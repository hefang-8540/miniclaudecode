"""扁平工具注册表 + read_only 注解 + 分层可见性。与 design_mcp registry 同款模式。

铁律 3：visible_tools 输出按 (tier≠core, name) 排序 —— core 恒在前、extended
warmup 后一次性追加到尾部，列表前缀永不抖动（缓存友好）。
铁律 1：serialize_tools 用 json.dumps(sort_keys=True) 规范化 schema。

13 个工具（7 core + 6 extended）：
  core:     read_file list_dir glob_files grep_search write_file edit_file exit_plan_mode
  extended: bash run_tests delete_file git_diff git_commit fetch_url
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from ..permissions import SessionMode

Tier = Literal["core", "extended"]


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str          # 选型引导写在这里：何时用/何时不用/替代工具（ab-r1 同款实践）
    input_schema: dict
    handler: Callable[[dict, "ToolContext"], "ToolResult"]
    read_only: bool
    tier: Tier = "core"


@dataclass
class ToolResult:
    ok: bool
    output: str


@dataclass
class ToolContext:
    cwd: Path                          # workspace 根，文件类工具的边界基准
    record: Callable[[str, dict], int] # trajectory 写回调（铁律 4 由 agent 统一执行，工具内一般不用）


ALL_TOOLS: list[ToolDef] = []
_BY_NAME: dict[str, ToolDef] = {}


def register(tool: ToolDef) -> ToolDef:
    assert tool.name not in _BY_NAME, f"重复注册: {tool.name}"
    ALL_TOOLS.append(tool)
    _BY_NAME[tool.name] = tool
    return tool


def find_tool(name: str) -> ToolDef | None:
    return _BY_NAME.get(name)


def visible_tools(mode: SessionMode, extended_unlocked: bool) -> list[ToolDef]:
    """L1 防线（可见性过滤）+ 延迟激活，输出顺序稳定。"""
    tools = [t for t in ALL_TOOLS
             if (mode is SessionMode.ACT or t.read_only)
             and (extended_unlocked or t.tier == "core")]
    return sorted(tools, key=lambda t: (t.tier != "core", t.name))


def serialize_tools(tools: list[ToolDef]) -> list[dict]:
    """OpenAI tools 参数格式；schema 确定性序列化（铁律 1）。"""
    return [{"type": "function",
             "function": json.loads(json.dumps(
                 {"name": t.name, "description": t.description,
                  "parameters": t.input_schema}, sort_keys=True, ensure_ascii=False))}
            for t in tools]


# 触发内置工具注册（import 副作用，勿删）
from . import fs, shell, vcs, web, mode  # noqa: E402,F401
