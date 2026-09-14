# MiniClaudeCode

轻量级本地编码 Agent CLI：不依赖 LangChain/LangGraph，从零实现 Agent Loop、工具注册表、
分层权限、缓存感知上下文管理与轨迹回放。

> **机制出处**：plan mode（模式级只读环境）、AGENTS.md 分层指令注入、工具只读注解等机制
> 设计参考 grok-build 的生产实现，本项目为独立重实现（非代码复制），并按轻量单机场景
> 做了裁剪。各机制的"原版设计 → 本实现取舍"对比见 `DESIGN_NOTES.md`。

## 架构

```
cli ──► agent (主循环，唯一编排点)
          ├── context        稳定前缀构造 + 缓存感知压缩
          ├── providers      流式 + 指数退避重试 + usage/缓存遥测
          ├── tools          扁平注册表，13 个工具，read_only 注解 + core/extended 分层
          ├── permissions    三道防线：工具白名单 → 模式只读 → 交互审批
          ├── instructions   AGENTS.md 分层注入（用户级/项目级）
          └── trajectory     全量 JSONL 录制 ──► replay 离线回归（VCR 模式）
```

## 设计铁律（改任何模块前先读）

1. **稳定前缀**：system prompt 与 tools 序列化不含时间戳/uuid/随机序；JSON 一律
   `sort_keys=True` 确定性序列化。前缀每变一个字节，DeepSeek 自动前缀缓存全部失效。
2. **Append-only**：历史消息永不原地修改；唯一例外是显式 `compact()`，且优先在
   缓存 TTL 已冷（空闲 > cache_ttl_s）时执行，让压缩的缓存损失为零。
3. **稳定序一次激活**：工具按 `(tier, name)` 排序，core 恒在前；extended 工具在
   warmup 轮次后**一次性**追加（无抖动），追加只动列表尾部。
4. **权限判定必录**：每次 ALLOW/DENY/ASK 都写 trajectory（铁律 4 = 回放的可比性来源）。
5. **完成 = 产物存在**：回放/报告以文件存在与内容 diff 为准，不以进程退出码为准。

## 模块地图

| 文件 | 职责 | 施工阶段 |
|---|---|---|
| `cli.py` / `__main__.py` | 入口：chat / replay / status 三个子命令 | M1 |
| `config.py` | Provider/Settings 声明式配置 | M1（已完成） |
| `trajectory.py` | JSONL 录制 + usage 聚合（命中率数据源） | M1（已完成） |
| `providers/` | fake（离线开发）/ openai_compat（DeepSeek）/ anthropic | M1/M3 |
| `agent.py` | 主循环：构前缀→流式→工具调用→权限→追加→压缩 | M1 起逐步填 |
| `tools/registry.py` | ToolDef + 可见性过滤 + 稳定序列化 | M2（骨架已完成） |
| `tools/fs,shell,vcs,web,mode.py` | 13 个内置工具 | M2 |
| `permissions.py` | SessionMode + 三道防线判定 | M2/M5 |
| `instructions.py` | AGENTS.md 分层加载与渲染 | M4 |
| `context.py` | build_system_prompt + Compactor（TTL 协同） | M4/M6 |
| `replay.py` | TapeProvider + diff 报告 | M7 |

## 测量（简历数字的唯一出处，禁止估算）

- **延迟激活 A→B token**：同一会话脚本分别在 `warmup_turns=0`（全量工具）与
  `warmup_turns=99`（仅 core）下跑首请求，对比请求体中 tools 序列化字节 → token 估算。
- **缓存命中率 X%→Y%**：`usage.prompt_cache_hit_tokens / usage.prompt_tokens`，
  逐请求写入 trajectory，`miniclaude status <session.jsonl>` 聚合输出。
  baseline = 未做稳定前缀改造前实测；优化后 = 改造后同场景复测。

## Quickstart

```bash
pip install -e .
export DEEPSEEK_API_KEY=sk-...
miniclaude chat                 # 真实会话（默认 deepseek provider）
miniclaude chat --fake          # 离线开发，无需 API key
miniclaude status sessions/xxx.jsonl
miniclaude replay sessions/xxx.jsonl
```

## 会话内命令

`/plan` `/act`（切换模式，进 act 需审批）、`/status`（命中率/token/工具统计）、
`/compact`（手动压缩）、`/tools`（当前可见工具）、`/quit`
