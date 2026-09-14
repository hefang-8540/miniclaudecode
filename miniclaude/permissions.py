"""权限治理：SessionMode + 三道防线判定。

三道防线（纵深防御，任何单点失效仍有兜底）：
  L1 模式层：PLAN 模式下副作用工具在 tools/list 中物理不可见（registry 过滤）；
     即使 LLM 幻觉调用，decide() 仍返回 DENY —— 可见性之外再兜一层
  L2 静态层：read_only → ALLOW；高危工具（ALWAYS_ASK）→ 永远 ASK；
     settings.auto_approve 命中 → ALLOW；其余 rw → ASK
  L3 交互层：ASK → 用户 y/n/always；always 写入会话级授权集（本会话内升级为 ALLOW）

铁律 4：每次判定（含 ALLOW）都由调用方（agent）record 到 trajectory。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Settings
    from .tools.registry import ToolDef


class SessionMode(Enum):
    PLAN = "plan"   # 只读环境：只可见/可执行 read_only 工具
    ACT = "act"     # 正常执行


class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


# 高危工具：即使被 auto_approve / always 授权过，进入新会话仍需重新 ASK
ALWAYS_ASK = frozenset({"bash", "delete_file", "git_commit"})


@dataclass
class PermissionPolicy:
    settings: "Settings"
    session_grants: set[str] = field(default_factory=set)  # L3 "always" 授权集

    def decide(self, tool: "ToolDef", args: dict, mode: SessionMode) -> tuple[Decision, str]:
        """返回 (决定, 原因)。原因字符串入轨迹 —— 回放 diff 的可比字段。"""
        if mode is SessionMode.PLAN and not tool.read_only:
            return Decision.DENY, f"plan mode: {tool.name} 非只读工具"
        if tool.read_only:
            return Decision.ALLOW, "read_only"
        if tool.name in self.session_grants and tool.name not in ALWAYS_ASK:
            return Decision.ALLOW, "session grant (always)"
        if tool.name in self.settings.auto_approve and tool.name not in ALWAYS_ASK:
            return Decision.ALLOW, "settings.auto_approve"
        return Decision.ASK, ("高危工具" if tool.name in ALWAYS_ASK else "写操作默认询问")

    def grant_always(self, tool_name: str) -> None:
        if tool_name not in ALWAYS_ASK:
            self.session_grants.add(tool_name)
