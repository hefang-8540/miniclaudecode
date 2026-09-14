"""网络工具（1 个）。—— M2。只读但出网，仍归 extended（上下文成本 + 数据外泄面）。"""
from __future__ import annotations

from .registry import ToolDef, register


def _stub_fetch(a, c):
    raise NotImplementedError("M2: urllib 实现，超时 15s，HTML 转纯文本（html.parser 即可），截 8KB")


register(ToolDef(
    name="fetch_url",
    description="GET 一个 URL 返回纯文本（HTML 剥标签），截断 8KB。只支持 http/https。发送内容到外部 = 发布，请求体不含敏感信息。",
    input_schema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    handler=_stub_fetch, read_only=True, tier="extended"))
