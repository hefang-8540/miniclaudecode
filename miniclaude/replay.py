"""VCR 离线回放 —— 回归测试：改 prompt/权限/压缩逻辑后重放旧会话，验证不漂移。—— M7

设计：
- TapeProvider 从轨迹的 model_response 事件按序弹出响应（替代真实 API）
- 工具结果同样从录像供数（tool_result 事件），handler 不真执行 ——
  但 harness 代码路径真跑：权限判定、可见性过滤、前缀构造、压缩触发
- 比对三项（漂移任一项 → 退出码 1 + diff 报告）：
    1. 工具调用序列（name + args 规范化 JSON）
    2. 权限判定序列（decision + reason）
    3. 压缩事件（次数与触发位置）
- 铁律 5：报告落盘为文件（replay_report_<ts>.txt），"完成 = 报告存在"，
  不以进程正常走完为准

用法：miniclaude replay sessions/xxx.jsonl [--json]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiffReport:
    tool_call_drift: list[str] = field(default_factory=list)
    permission_drift: list[str] = field(default_factory=list)
    compaction_drift: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.tool_call_drift or self.permission_drift or self.compaction_drift)


class TapeProvider:
    """M7: 实现 providers.base.Provider 接口，stream() 从录像弹出下一条
    model_response（content/tool_calls/usage 原样），耗尽则抛异常（轨迹不完整）。"""


def replay(trajectory_path: Path, settings) -> DiffReport:
    raise NotImplementedError("M7")


def write_report(report: DiffReport, out_dir: Path) -> Path:
    raise NotImplementedError("M7")
