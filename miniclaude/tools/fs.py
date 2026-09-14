"""文件系统工具（7 个）。read_file 是参考实现，其余照它的模式补 —— M2。

通用边界规则（每个文件类 handler 必须执行）：
- 相对路径基于 ctx.cwd 解析；解析后必须落在 ctx.cwd 内（ab-r1 数据访问边界同款纪律），
  越界返回 ToolResult(False, "path escapes workspace: ...")
- 输出截断：单文件 > 2000 行截断并注明；tool_result 入轨迹时 output 截 4KB
"""
from __future__ import annotations

from pathlib import Path

from .registry import ToolContext, ToolDef, ToolResult, register


def _resolve_in_workspace(ctx: ToolContext, raw: str) -> Path | ToolResult:
    """公共边界检查：成功返回绝对路径，失败返回 ToolResult（调用方直接 return）。"""
    p = Path(raw)
    p = p.resolve() if p.is_absolute() else (ctx.cwd / p).resolve()
    if p != ctx.cwd and ctx.cwd not in p.parents:
        return ToolResult(False, f"path escapes workspace: {p}")
    return p


def _read_file(args: dict, ctx: ToolContext) -> ToolResult:
    p = _resolve_in_workspace(ctx, args["path"])
    if isinstance(p, ToolResult):
        return p
    if not p.is_file():
        return ToolResult(False, f"file not found: {p}")
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    truncated = len(lines) > 2000
    body = "\n".join(f"{i + 1}\t{ln}" for i, ln in enumerate(lines[:2000]))
    if truncated:
        body += f"\n... [截断：共 {len(lines)} 行，仅显示前 2000]"
    return ToolResult(True, body)


register(ToolDef(
    name="read_file",
    description="读取工作区内文本文件，返回带行号内容（>2000 行截断）。查看目录用 list_dir，按名找文件用 glob_files，按内容找用 grep_search。",
    input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    handler=_read_file, read_only=True, tier="core"))

# ---- M2 待实现（契约见各自 description，实现照 _read_file 模式）----

_STUB = "M2: 照 _read_file 模式实现（含 _resolve_in_workspace 边界检查）"

register(ToolDef(
    name="list_dir",
    description="列出目录一层内容，标注 文件/目录 与大小。递归查找用 glob_files。",
    input_schema={"type": "object", "properties": {"path": {"type": "string", "description": "默认 ."}}, "required": []},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=True, tier="core"))

register(ToolDef(
    name="glob_files",
    description="按 glob 模式（如 **/*.py）在工作区内找文件，返回按修改时间排序的路径列表。",
    input_schema={"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=True, tier="core"))

register(ToolDef(
    name="grep_search",
    description="工作区内正则搜索文件内容，返回 文件:行号:内容。只搜文本文件，跳过 .git/__pycache__/二进制。",
    input_schema={"type": "object", "properties": {"pattern": {"type": "string"}, "glob": {"type": "string", "description": "可选文件过滤，如 *.py"}}, "required": ["pattern"]},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=True, tier="core"))

register(ToolDef(
    name="write_file",
    description="整文件写入（覆盖）。仅部分修改优先用 edit_file；覆盖前应先 read_file 确认。",
    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=False, tier="core"))

register(ToolDef(
    name="edit_file",
    description="精确字符串替换：old_string 必须在文件中唯一，否则报错（附出现次数）。new_string 与 old_string 不得相同。",
    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"]},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=False, tier="core"))

register(ToolDef(
    name="delete_file",
    description="删除单个文件。高危：永远触发审批（ALWAYS_ASK）。禁止实现为递归删除目录。",
    input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=False, tier="extended"))
