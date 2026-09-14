"""AGENTS.md 分层指令注入（Memory 静态层）。—— M4 接入 agent

铁律 1：注入内容只随文件变化；渲染顺序固定（用户级在前、项目级在后），
文件不存在则整段跳过 —— 输出对同一磁盘状态字节级稳定。

与 ab-r1 的动态记忆（wiki 知识库）分工：指令文件 = 不变的约定（编码规范、
禁改目录）；wiki = 随实验演化的经验。静态层放约定，动态层放事实。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

USER_LEVEL_DIR = ".miniclaude"   # ~/.miniclaude/AGENTS.md
PROJECT_FILE = "AGENTS.md"       # <workspace>/AGENTS.md


@dataclass(frozen=True)
class InstructionFile:
    scope: str        # "user" | "project"
    path: Path
    content: str


def load_instructions(home: Path, workspace: Path) -> list[InstructionFile]:
    """用户级 → 项目级顺序返回；不存在的跳过。项目级优先级更高（渲染时声明）。"""
    out: list[InstructionFile] = []
    for scope, p in (("user", home / USER_LEVEL_DIR / PROJECT_FILE),
                     ("project", workspace / PROJECT_FILE)):
        if p.is_file():
            out.append(InstructionFile(scope, p,
                                       p.read_text(encoding="utf-8", errors="replace")))
    return out


def render_section(files: list[InstructionFile]) -> str:
    """渲染进 system prompt 的稳定文本段。无文件时返回空串。"""
    if not files:
        return ""
    parts = ["# 指令文件（冲突时 project 级覆盖 user 级）"]
    for f in files:
        parts.append(f"## [{f.scope}] {f.path.name}\n{f.content.rstrip()}")
    return "\n\n".join(parts)
