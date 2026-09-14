# BUILD_ORDER — vibecoding 施工顺序

每个里程碑 = 一张任务卡。开工时把「给 coding agent 的任务」原文粘给 ZCode/编码 agent，
完成后跑「验收」命令，过了再进下一个。**严格按顺序**：M0 的遥测是后面所有数字的地基。

---

## M1 — 最小可聊（骨架跑通 + 遥测落地）

**给 coding agent 的任务**：
> 填充 `providers/fake.py`、`agent.py`、`cli.py` 中标注 M1 的 NotImplementedError。
> 目标：`miniclaude chat --fake` 能进行多轮对话；每次 model_request/model_response
> 写入 `sessions/<ts>.jsonl`（用 trajectory.TrajectoryRecorder）；`miniclaude status
> <jsonl>` 能打印事件统计。遵守 README 五条铁律，特别是 JSONL append-only。

**验收**：
```bash
miniclaude chat --fake   # 输入两轮话退出
miniclaude status sessions/<生成的文件>.jsonl   # 应显示 model_request/response 计数
```

## M2 — 工具系统 + 权限（真实可用的编码 agent）

**给 coding agent 的任务**：
> 实现 `tools/fs.py`（read_file 已给出参考实现，照它的模式补 list_dir/glob_files/
> grep_search/write_file/edit_file/delete_file）、`tools/shell.py`（bash/run_tests）、
> `tools/vcs.py`（git_diff/git_commit）、`tools/web.py`（fetch_url）、`tools/mode.py`
> （exit_plan_mode 门）。填 `agent.py` 中 M2 步骤：工具调用循环 + PermissionPolicy
> 判定 + ASK 交互（y/n/always）+ 异常安全（handler 抛异常转 ok=False，绝不让单个
> 工具失败杀死会话）。每次权限判定写 trajectory（铁律 4）。bash 命令执行用
> subprocess，stderr 合并进 stdout 返回，禁止 PIPE 分离（缓冲区死锁教训）。

**验收**：
```bash
miniclaude chat --fake   # FakeProvider 脚本一段带 read_file 工具调用的响应
# 1) read_file 正常返回带行号内容  2) delete_file 触发 ASK  3) 拒绝后返回合成错误不崩溃
grep permission_decision sessions/<文件>.jsonl   # 判定已入轨迹
```

## M3 — 真 Provider 接入 + 缓存 baseline（简历数字第一步）

**给 coding agent 的任务**：
> 实现 `providers/openai_compat.py`：openai SDK，base_url 走 ProviderConfig，
> stream=True 且 stream_options={"include_usage": True}，从最后 chunk 提取
> usage.prompt_tokens / prompt_cache_hit_tokens / completion_tokens 填入
> CacheUsage；指数退避重试 429/5xx/网络错（1/2/4/8/16s + 抖动，max 5）。
> agent.py 每次响应后 record("cache_stats", ...)。

**验收**：
```bash
export DEEPSEEK_API_KEY=...
miniclaude chat   # 真实多轮编码会话（让它读几个文件、改一个文件）
miniclaude status sessions/<文件>.jsonl   # 输出真实缓存命中率
```
**📌 记录 baseline 命中率到 `MEASUREMENTS.md`（新建）**：这是简历 X% 的出处。

## M4 — AGENTS.md 分层注入 + 稳定前缀审计

**给 coding agent 的任务**：
> 填充 `instructions.py` 接入 agent（system prompt 拼装见 context.build_system_prompt
> 的 M4 部分）；执行铁律 1 审计：system prompt 与 tools 序列化全链路无时间戳/随机序，
> JSON 一律 sort_keys。写一个测试：同输入构造两次 system prompt，断言字节级相等。

**验收**：
```bash
pytest tests/test_stable_prefix.py   # 字节级相等断言通过
# 手工：在项目目录放 AGENTS.md 写一条规则，chat 中问"项目规则是什么"应答对
```

## M5 — Plan mode（模式级只读环境）

**给 coding agent 的任务**：
> 填充 `permissions.py` 的 SessionMode 切换与 `agent.py` 的 M5 步骤：/plan 进入后
> visible_tools 只返回 read_only 工具（防御纵深：即使 LLM 幻觉调用 rw 工具，
> policy.decide 仍 DENY）；exit_plan_mode 工具展示计划文本 → 用户批准 → 切回 ACT。
> 模式切换本身写 trajectory。

**验收**：
```bash
miniclaude chat --fake   # FakeProvider 脚本：plan 模式下尝试调用 write_file
# 1) write_file 不在 tools 列表  2) 强行调用被 DENY  3) exit_plan_mode 走审批后 rw 工具恢复可见
```

## M6 — 延迟激活 + 缓存感知压缩（简历数字第二步）

**给 coding agent 的任务**：
> ① 延迟激活：turn_count >= warmup_turns 时一次性解锁 extended 工具（铁律 3：
> 只追加到列表尾部，解锁后不再变化）。② Compactor：should_compact 仅在
> tokens > threshold 且（空闲 > provider cache_ttl_s 或用户 /compact 强制）时为真；
> compact 将最旧消息摘要为单条 summary 消息（摘要用 LLM 生成），保留最近
> keep_recent_turns 轮原文；压缩事件 record("compaction", {before, after, reason})。
> ③ 复测：M3 同场景重跑，记录优化后命中率。

**验收**：
```bash
pytest tests/test_compactor.py    # TTL 冷/热两种情况下 should_compact 的行为
miniclaude status sessions/<新会话>.jsonl   # 命中率 Y%
```
**📌 记录到 MEASUREMENTS.md**：优化后命中率（简历 Y%）、延迟激活 tools 序列化
token 开/关对比（简历 A→B）。

## M7 — 轨迹回放 + 收尾

**给 coding agent 的任务**：
> 实现 `replay.py`：TapeProvider 从 trajectory 顺序回放 model_response；工具结果
> 也从录像供数（不真执行）；重跑 harness 代码路径（权限判定/上下文构造/压缩触发），
> 对比三项：工具调用序列（name+args）、权限判定、压缩事件；任何漂移 → diff 报告 +
> 退出码 1。然后：写 DESIGN_NOTES.md（每机制：grok-build 原版怎么做/我改了什么/
> 为什么）、MEASUREMENTS.md 定稿、README 补截图或 asciinema。

**验收**：
```bash
miniclaude replay sessions/<M6的会话>.jsonl   # 报告 zero drift，退出码 0
# 改一行 system prompt 模板再回放 → 应报 drift 且退出码 1（证明回归有效）
```

## 收尾（人工，不委托）

```bash
git init && git add -A && git commit -m "miniclaudecode: hand-rolled coding agent CLI"
# GitHub 建私有→公开仓库 miniclaudecode，push，简历填链接
```

**纪律重申**：MEASUREMENTS.md 里没有的数字，简历上不许出现。
