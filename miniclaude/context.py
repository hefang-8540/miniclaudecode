"""稳定前缀构造 + 缓存感知压缩 —— Token 经济学的心脏。

铁律 1：build_system_prompt 的输出对同一 (instructions, mode) 字节级稳定 ——
  无时间戳、无 uuid、无随机序。测试：tests/test_stable_prefix.py 两次构造断言相等。
铁律 2：历史消息 append-only；compact() 是唯一改写入口，且优先在缓存冷时执行。

模式段是唯一随 mode 变化的内容 → 模式切换 = 已知的前缀失效点，可接受
（切换是低频显式动作）。除此之外前缀在会话内必须恒定。
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from .permissions import SessionMode

IDENTITY = (
    "你是 MiniClaudeCode，一个运行在本地终端的编码 Agent。"
    "你在用户的 workspace 内通过工具读写文件、执行命令，完成编码任务。"
)

RULES = (
    "# 行为规则\n"
    "- 修改文件前先 read_file 确认现状；部分修改用 edit_file，不要整文件重写\n"
    "- 每次改动后主动 run_tests 验证\n"
    "- 不确定需求时先提问，不要猜\n"
    "- PLAN 模式：只调研与规划，产出实现计划后调用 exit_plan_mode 提交审批"
)

MODE_SECTION = {
    SessionMode.PLAN: "# 当前模式：PLAN（只读）\n副作用工具不可用。调研代码库后给出完整实现计划。",
    SessionMode.ACT: "# 当前模式：ACT\n可正常读写与执行。",
}


def build_system_prompt(instruction_section: str, mode: SessionMode) -> str:
    """拼装顺序固定：身份 → 规则 → 指令文件 → 模式段。返回文本对同输入字节级稳定。"""
    parts = [IDENTITY, RULES]
    if instruction_section:
        parts.append(instruction_section)
    parts.append(MODE_SECTION[mode])
    return "\n\n".join(parts)


def estimate_tokens(system: str, messages: list[dict], tools: list[dict]) -> int:
    """chars/4 启发式即可（压缩阈值判断不需要精确 tokenizer，注明是估算）。"""
    import json
    total = len(system) + sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)
    total += sum(len(json.dumps(t, ensure_ascii=False)) for t in tools)
    return total // 4


@dataclass
class Compactor:
    """M6 实现。缓存协同是灵魂：压缩必破坏前缀缓存，所以只在缓存已冷时做。"""

    def should_compact(self, tokens: int, threshold: int, last_request_ts: float,
                       cache_ttl_s: int, force: bool = False) -> tuple[bool, str]:
        """返回 (是否压缩, 原因)。规则：
        tokens <= threshold → (False, "below threshold")
        force → (True, "user forced")
        空闲(now - last_request_ts) > cache_ttl_s → (True, "cache cold, free compaction")
        否则 → (False, "cache hot, defer")   ← 宁可靠近阈值多跑几轮，也不白扔缓存
        """
        raise NotImplementedError("M6")

    def compact(self, messages: list[dict], keep_recent_turns: int,
                summarize_fn) -> tuple[list[dict], dict]:
        """将最旧消息压成单条 summary（role=system 或首条 user 前的 note，
        summarize_fn 由 agent 传入 = 调一次 provider 生成摘要；M6 前期可先用
        截断占位）。返回 (新 messages, 压缩元数据)。
        元数据 record 进 trajectory：{before_tokens, after_tokens, reason, cache_cold}
        不变量：压缩后最近 keep_recent_turns 轮的消息对象原样保留（内容不改写）。"""
        raise NotImplementedError("M6")
