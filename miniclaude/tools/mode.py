"""模式门工具（1 个）。—— M5 由 agent 特殊处理。

exit_plan_mode 不是普通工具：handler 不产生副作用，只把 plan 文本透传回去；
真正的模式切换由 agent 层执行 —— 展示 plan → 用户批准（L3 交互）→ switch_mode(ACT)
→ record("mode_switch")。用户拒绝则留在 PLAN，agent 继续完善计划。
read_only=True 使它在 PLAN 模式可见（否则连退出计划模式的工具都没有）。
"""
from __future__ import annotations

from .registry import ToolDef, ToolResult, register


def _exit_plan_mode(args: dict, ctx) -> ToolResult:
    # 真实现仅是透传；审批与切换在 agent.run_turn 的工具分派处特判
    return ToolResult(True, args.get("plan", ""))


register(ToolDef(
    name="exit_plan_mode",
    description="PLAN 模式下完成规划后调用：提交完整实现计划供用户审批。批准后切换到执行模式；拒绝则留在计划模式继续修改。这是 PLAN→ACT 的唯一通道。",
    input_schema={"type": "object", "properties": {"plan": {"type": "string", "description": "完整实现计划文本"}}, "required": ["plan"]},
    handler=_exit_plan_mode, read_only=True, tier="core"))
