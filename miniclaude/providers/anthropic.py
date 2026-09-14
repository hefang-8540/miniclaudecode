"""Anthropic Provider（显式缓存断点）。—— M3+ 可选实现

与 DeepSeek 自动前缀缓存的关键差异（面试对比素材，写进 DESIGN_NOTES.md）：
1. Anthropic 要显式 cache_control 断点：在 system 最后一个 content block 和
   tools 最后一项上打 {"type": "ephemeral"}，断点之前的内容才进缓存
2. usage 字段：cache_read_input_tokens（命中）/ cache_creation_input_tokens（写入）
3. 消息格式不同：tool 结果是 user 消息里的 tool_result block，需转换层
4. 同样需要稳定前缀 —— 断点位置固定，system 内容不变，否则缓存写入白费
"""
from __future__ import annotations

from .base import ModelResponse, Provider


class AnthropicProvider(Provider):
    def stream(self, system: str, messages: list[dict], tools: list[dict]) -> ModelResponse:
        raise NotImplementedError("M3+ 可选: 见本文件 docstring")
