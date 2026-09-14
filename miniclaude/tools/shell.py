"""Shell 工具（2 个）。—— M2

实现纪律（ab-r1 生产事故换来的两条）：
1. subprocess 的 stderr 合并进 stdout（stderr=STDOUT）或写文件，**禁止 PIPE 分离**
   —— 64KB 管道缓冲区写满会死锁（ab-r1 r13 事故根因）
2. 必须传 timeout（默认 120s），超时杀进程树（start_new_session=True + killpg）
"""
from __future__ import annotations

from .registry import ToolDef, register

_STUB = "M2: subprocess 实现，stderr 合并 stdout，timeout + 杀进程树"

register(ToolDef(
    name="bash",
    description="在 workspace 执行 shell 命令，返回 stdout+stderr 与退出码。高危：默认逐次审批。长任务（>2min）应建议用户后台运行。",
    input_schema={"type": "object", "properties": {"command": {"type": "string"}, "timeout_s": {"type": "integer", "description": "默认 120"}}, "required": ["command"]},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=False, tier="extended"))

register(ToolDef(
    name="run_tests",
    description="运行项目测试（自动探测 pytest / npm test / go test），返回摘要 + 失败用例详情。改完代码应主动调用验证。",
    input_schema={"type": "object", "properties": {"path": {"type": "string", "description": "可选：测试路径过滤"}}, "required": []},
    handler=lambda a, c: (_ for _ in ()).throw(NotImplementedError(_STUB)),
    read_only=False, tier="extended"))
