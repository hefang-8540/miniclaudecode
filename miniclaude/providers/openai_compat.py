"""OpenAI 兼容 Provider（DeepSeek 主用）。—— M3 实现

实现清单（照此填 stream()）：
1. openai.OpenAI(base_url=cfg.base_url, api_key=cfg.api_key())
2. chat.completions.create(model, messages=[{"role":"system","content":system}, *messages],
   tools=tools or None, stream=True, stream_options={"include_usage": True})
   ← 没有 stream_options 拿不到最终 usage，DeepSeek 缓存遥测全丢
3. 逐 chunk：delta.content 即时 print；delta.tool_calls 按 index 累积
   （流式 tool_calls 是分片的：id/name 首片给，arguments 逐片拼接）
4. 最终 chunk 的 usage：prompt_tokens / completion_tokens /
   prompt_cache_hit_tokens（字段名走 cfg.cache_telemetry_field，缺失按 0）→ CacheUsage
5. 重试装饰：429/5xx/APITimeoutError/APIConnectionError，指数退避 + 抖动，max 5；
   重试时原样重放请求（base.py 契约）
"""
from __future__ import annotations

from .base import ModelResponse, Provider


class OpenAICompatProvider(Provider):
    def stream(self, system: str, messages: list[dict], tools: list[dict]) -> ModelResponse:
        raise NotImplementedError("M3: 见本文件 docstring 实现清单")
