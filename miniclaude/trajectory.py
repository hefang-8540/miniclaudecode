"""轨迹录制与遥测聚合 —— M1 优先落地的模块（简历数字与回放的地基）。

铁律 2/4：JSONL append-only，永不重写；每次权限判定必须 record。
事件类型固定枚举，payload 自由 dict —— 回放的可比性依赖 type + 关键字段的稳定性。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

EVENT_TYPES = (
    "session_start",        # {provider, model, workspace, settings 快照}
    "model_request",        # {system_sha256, tools_sha256, n_messages, mode}  ← 前缀指纹，稳定性审计用
    "model_response",       # {content, tool_calls, finish_reason, usage}
    "tool_call",            # {id, name, arguments}
    "tool_result",          # {id, ok, output_truncated}
    "permission_decision",  # {tool, decision, mode, reason}   ← 铁律 4
    "compaction",           # {before_tokens, after_tokens, reason, cache_cold}
    "mode_switch",          # {from, to, approved_by}
    "cache_stats",          # CacheUsage 原样
)


@dataclass
class CacheUsage:
    prompt_tokens: int = 0
    cached_tokens: int = 0
    completion_tokens: int = 0

    @property
    def hit_rate(self) -> float:
        return self.cached_tokens / self.prompt_tokens if self.prompt_tokens else 0.0

    def to_dict(self) -> dict[str, int]:
        return {"prompt_tokens": self.prompt_tokens,
                "cached_tokens": self.cached_tokens,
                "completion_tokens": self.completion_tokens}


class TrajectoryRecorder:
    """一个会话一个 JSONL 文件。record() 立写立 flush（进程被杀不丢轨迹）。"""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8")
        self._seq = 0

    def record(self, event_type: str, payload: dict[str, Any]) -> int:
        assert event_type in EVENT_TYPES, f"未注册事件类型: {event_type}"
        self._seq += 1
        row = {"ts": round(time.time(), 3), "seq": self._seq,
               "type": event_type, "payload": payload}
        self._fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        self._fh.flush()
        return self._seq

    def close(self) -> None:
        self._fh.close()


def read_trajectory(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def aggregate(path: Path) -> dict[str, Any]:
    """/status 与简历数字的数据源。返回：
    requests, tool_calls(按工具名计数), permission_decisions(按决定计数),
    prompt_tokens, cached_tokens, hit_rate, compactions, system_prefixes(去重指纹数)
    —— system_prefixes > 1 且非模式切换所致 = 前缀稳定性被破坏，应报警。
    """
    stats: dict[str, Any] = {
        "requests": 0, "tool_calls": {}, "permission_decisions": {},
        "prompt_tokens": 0, "cached_tokens": 0, "completion_tokens": 0,
        "compactions": 0, "system_prefixes": set(),
    }
    for ev in read_trajectory(path):
        t, p = ev["type"], ev["payload"]
        if t == "model_request":
            stats["requests"] += 1
            stats["system_prefixes"].add(p.get("system_sha256", "?"))
        elif t == "cache_stats":
            for k in ("prompt_tokens", "cached_tokens", "completion_tokens"):
                stats[k] += p.get(k, 0)
        elif t == "tool_call":
            stats["tool_calls"][p["name"]] = stats["tool_calls"].get(p["name"], 0) + 1
        elif t == "permission_decision":
            d = p["decision"]
            stats["permission_decisions"][d] = stats["permission_decisions"].get(d, 0) + 1
        elif t == "compaction":
            stats["compactions"] += 1
    pt = stats["prompt_tokens"]
    stats["hit_rate"] = round(stats["cached_tokens"] / pt, 4) if pt else None
    stats["system_prefixes"] = len(stats["system_prefixes"])
    return stats
