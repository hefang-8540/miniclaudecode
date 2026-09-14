"""主循环 —— 唯一的编排点，其他模块互不调用。分里程碑填充（标注 M1/M2/M5/M6）。

run_turn 的骨架步骤就是面试讲 Agent Loop 的答案，编号与 BUILD_ORDER 对应。
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

from .config import Settings
from .context import Compactor, build_system_prompt, estimate_tokens
from .instructions import load_instructions, render_section
from .permissions import Decision, PermissionPolicy, SessionMode
from .providers.base import ModelResponse, Provider
from .tools.registry import ToolContext, ToolResult, find_tool, serialize_tools, visible_tools
from .trajectory import TrajectoryRecorder


class Agent:
    def __init__(self, settings: Settings, provider: Provider, recorder: TrajectoryRecorder):
        self.settings = settings
        self.provider = provider
        self.recorder = recorder
        self.policy = PermissionPolicy(settings=settings)
        self.compactor = Compactor()
        self.messages: list[dict] = []
        self.mode = SessionMode.ACT
        self.extended_unlocked = not settings.lazy_activation
        self.turn_count = 0
        self.last_request_ts = time.time()
        self._instructions = render_section(
            load_instructions(Path.home(), settings.workspace))

    # ---------- REPL ----------

    def run_chat(self) -> None:
        """M1: input() 循环 → /命令 或 run_turn；Ctrl-C/Ctrl-D 干净退出并 close 轨迹。"""
        raise NotImplementedError("M1")

    def handle_command(self, line: str) -> bool:
        """/plan /act /status /compact /tools /quit —— M1 做 status/tools/quit，
        M5 加 plan/act（/act 需审批 + record mode_switch），M6 接 /compact。
        返回 False 表示退出 REPL。"""
        raise NotImplementedError("M1")

    # ---------- 单轮：构前缀 → 流式 → 工具 → 追加 ----------

    def run_turn(self, user_text: str) -> None:
        self.messages.append({"role": "user", "content": user_text})
        while True:
            system = build_system_prompt(self._instructions, self.mode)
            tools = serialize_tools(visible_tools(self.mode, self.extended_unlocked))
            # 前缀指纹入轨迹（稳定性审计：同 mode 下指纹必须恒定）
            self.recorder.record("model_request", {
                "system_sha256": hashlib.sha256(system.encode()).hexdigest()[:16],
                "tools_sha256": hashlib.sha256(str([t["function"]["name"] for t in tools]).encode()).hexdigest()[:16],
                "n_messages": len(self.messages), "mode": self.mode.value})

            resp: ModelResponse = self.provider.stream(system, self.messages, tools)  # M1
            self.last_request_ts = time.time()
            self.recorder.record("cache_stats", resp.usage.to_dict())                 # M1
            # M1: 打印 resp.content；assistant 消息（含 tool_calls）append 进 messages

            if not resp.tool_calls:
                self.turn_count += 1
                self._maybe_unlock_extended()                                         # M6
                break
            for tc in resp.tool_calls:
                self._dispatch_tool(tc)                                               # M2
            if self.turn_count >= self.settings.max_turns:
                break
        self._maybe_compact()                                                         # M6

    # ---------- 工具分派：判定 → 审批 → 执行（全程入轨迹）----------

    def _dispatch_tool(self, tc) -> None:
        """M2 实现。步骤（每步入轨迹，铁律 4）：
        1. find_tool(tc.name)；未注册 → 合成错误 tool_result（不崩溃，LLM 可自纠）
        2. tc.name == "exit_plan_mode" → 特殊路径：展示 plan → input 审批 →
           批准则 switch_mode(ACT)（M5）
        3. policy.decide(tool, args, mode) → record("permission_decision", {...})
        4. ASK → input("[y/n/always] ")；always → policy.grant_always；
           DENY/拒绝 → 合成 ToolResult(False, "denied by user/permission")
        5. ALLOW → try: handler(args, ctx) except Exception as e: ToolResult(False, repr(e))
           —— 异常安全：单工具失败绝不杀死会话
        6. record tool_call / tool_result（output 截 4KB）；结果 append 为
           {"role":"tool","tool_call_id":...,"content":...}
        """
        raise NotImplementedError("M2")

    # ---------- 延迟激活 / 压缩 ----------

    def _maybe_unlock_extended(self) -> None:
        """M6: turn_count >= warmup_turns 且未解锁 → 解锁（一次性，铁律 3）。
        解锁时 record 一条 mode 外的说明事件可并入 compaction 类日志或 stderr 提示。"""
        raise NotImplementedError("M6")

    def _maybe_compact(self) -> None:
        """M6: estimate_tokens → compactor.should_compact(…, cache_ttl_s=provider.cfg.cache_ttl_s)
        → True 则 compact() 并 record("compaction", meta)。"""
        raise NotImplementedError("M6")

    def switch_mode(self, target: SessionMode, approved_by: str = "user") -> None:
        """M5: PLAN→ACT 必须已获审批；切换后重建 instructions 不变、仅模式段变。
        record("mode_switch", {from, to, approved_by})。"""
        raise NotImplementedError("M5")
