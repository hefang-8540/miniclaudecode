"""Provider 抽象：流式 + 指数退避重试 + usage/缓存遥测提取。

契约：stream() 内部逐 chunk 边打印边累积，结束后返回完整 ModelResponse。
重试范围：429 / 5xx / 网络错误；退避 1/2/4/8/16s + 抖动；max 5 次。
重试必须重放**完全相同**的请求体（铁律 1：请求体本身是确定性构造的，可安全重放）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..config import ProviderConfig
from ..trajectory import CacheUsage


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: CacheUsage = field(default_factory=CacheUsage)
    finish_reason: str = ""


class Provider(ABC):
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg

    @abstractmethod
    def stream(self, system: str, messages: list[dict], tools: list[dict]) -> ModelResponse:
        """system: 稳定前缀文本；messages: OpenAI 风格 role/content/tool_calls 列表；
        tools: registry.serialize_tools() 的确定性输出。"""
