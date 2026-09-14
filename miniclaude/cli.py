"""入口：chat / replay / status 三个子命令。M1 填 chat 的装配，其余已可用。"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def cmd_status(args) -> int:
    from rich.table import Table
    from .trajectory import aggregate

    stats = aggregate(Path(args.trajectory))
    t = Table(title=f"session stats: {args.trajectory}")
    t.add_column("metric"); t.add_column("value")
    t.add_row("model requests", str(stats["requests"]))
    t.add_row("prompt tokens", str(stats["prompt_tokens"]))
    t.add_row("cached tokens", str(stats["cached_tokens"]))
    t.add_row("cache hit rate", "-" if stats["hit_rate"] is None else f"{stats['hit_rate']:.2%}")
    t.add_row("tool calls", str(stats["tool_calls"]))
    t.add_row("permission decisions", str(stats["permission_decisions"]))
    t.add_row("compactions", str(stats["compactions"]))
    t.add_row("distinct system prefixes", str(stats["system_prefixes"]))
    from rich.console import Console
    Console().print(t)
    if stats["system_prefixes"] > 2:
        print("⚠️ 前缀指纹多于 2 种（模式切换最多贡献 2 种）——稳定前缀可能被破坏", file=sys.stderr)
    return 0


def cmd_chat(args) -> int:
    from .config import load_settings
    settings = load_settings(provider_name=args.provider, model=args.model,
                             workspace=args.workspace, fake=args.fake)
    if not args.fake and not settings.provider.api_key():
        raise SystemExit(f"缺少 API key：设置环境变量 {settings.provider.api_key_env}，或用 --fake")

    from .providers import FakeProvider
    if args.fake:
        provider = FakeProvider(settings.provider)
    elif settings.provider.name in ("deepseek", "openai"):
        from .providers.openai_compat import OpenAICompatProvider
        provider = OpenAICompatProvider(settings.provider)
    else:
        from .providers.anthropic import AnthropicProvider
        provider = AnthropicProvider(settings.provider)

    from .agent import Agent
    from .trajectory import TrajectoryRecorder
    sessions = Path(args.sessions)
    recorder = TrajectoryRecorder(sessions / f"{time.strftime('%Y%m%d-%H%M%S')}.jsonl")
    recorder.record("session_start", {"provider": settings.provider.name,
                                      "model": settings.provider.model,
                                      "workspace": str(settings.workspace)})
    agent = Agent(settings, provider, recorder)  # M1: Agent.run_chat() 落地后即可用
    try:
        agent.run_chat()
    finally:
        recorder.close()
        print(f"trajectory: {recorder.path}")
    return 0


def cmd_replay(args) -> int:
    raise NotImplementedError("M7: 调 replay.replay + write_report，drift → 返回 1")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="miniclaude", description="MiniClaudeCode — lightweight coding agent CLI")
    sub = ap.add_subparsers(dest="command", required=True)

    c = sub.add_parser("chat", help="交互会话")
    c.add_argument("--fake", action="store_true", help="离线 FakeProvider，无需 API key")
    c.add_argument("--provider", default=None, help="deepseek|openai|anthropic（默认 deepseek）")
    c.add_argument("--model", default=None)
    c.add_argument("--workspace", default=None, help="默认当前目录")
    c.add_argument("--sessions", default="sessions")
    c.set_defaults(fn=cmd_chat)

    s = sub.add_parser("status", help="聚合一条会话轨迹的遥测（缓存命中率等）")
    s.add_argument("trajectory")
    s.set_defaults(fn=cmd_status)

    r = sub.add_parser("replay", help="离线回放轨迹做回归 diff（M7）")
    r.add_argument("trajectory")
    r.add_argument("--json", action="store_true")
    r.set_defaults(fn=cmd_replay)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
