"""离线开发/测试用 Provider：按脚本返回响应，无网络、无 key、确定性。

M1 实现要点：
- script 为 [(content, tool_calls)] 列表，按调用次序弹出；耗尽后返回兜底文本
- usage 伪造固定值（prompt_tokens 按 messages 长度估算，cached_tokens=0），
  保证 status/aggregate 全链路可测
- 回放模式（M7）由 replay.TapeProvider 承担，不是本类
"""
from __future__ import annotations

from typing import Any

from .base import ModelResponse, Provider, ToolCall


class FakeProvider(Provider):
    def __init__(self, cfg, script: list[tuple[str, list[dict[str, Any]]]] | None = None):
        super().__init__(cfg)
        self.script = list(script or [])
        self.calls: list[dict] = []   # 记录每次请求，测试断言用

    def stream(self, system: str, messages: list[dict], tools: list[dict]) -> ModelResponse:
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        if self.script:
            content, tcs = self.script.pop(0)
        else:
            content, tcs = f"[fake] 收到 {len(messages)} 条消息，无脚本响应。", []
        from ..trajectory import CacheUsage
        usage = CacheUsage(prompt_tokens=sum(len(str(m)) for m in messages) // 4,
                           cached_tokens=0, completion_tokens=len(content) // 4)
        return ModelResponse(content=content,
                             tool_calls=[ToolCall(**tc) for tc in tcs],
                             usage=usage, finish_reason="stop")
