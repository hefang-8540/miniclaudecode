"""Git 工具（2 个）。—— M2。只读 git_diff（extended 因为输出可能大），git_commit 高危审批。"""
from __future__ import annotations

from .registry import ToolDef, register

_STUB = "M2: subprocess git 实现，同 shell.py 纪律"

register(ToolDef(
    name="git_diff",
    description="查看工作区 git diff（可指定路径/HEAD 对比）。提交前必须先 diff 检查改动范围。",
    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "staged": {"type": "boolean", "description": "true 看暂存区"}}, "required": []},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=True, tier="extended"))

register(ToolDef(
    name="git_commit",
    description="git add 指定文件并 commit。高危：永远审批。message 用 conventional commits 格式。禁止 push（push 是用户的事）。",
    input_schema={"type": "object", "properties": {"paths": {"type": "array", "items": {"type": "string"}}, "message": {"type": "string"}}, "required": ["paths", "message"]},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=False, tier="extended"))
