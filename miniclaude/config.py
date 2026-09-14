"""配置层：纯声明，无业务逻辑。

铁律 1 相关约束：api_key 等易变/敏感内容只进环境变量与运行时对象，
**绝不进入 system prompt 或任何被序列化成前缀的内容**。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ProviderConfig:
    name: str                       # "deepseek" | "openai" | "anthropic" | "fake"
    base_url: str | None            # OpenAI 兼容端点；None → SDK 默认
    model: str
    api_key_env: str                # 从此环境变量读 key（fake 可为空）
    cache_telemetry_field: str | None  # usage 里的缓存命中字段名；None = 无遥测
    cache_ttl_s: int = 300          # 前缀缓存 TTL，压缩时机协同用（DeepSeek 约 5min）

    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


PROVIDERS: dict[str, ProviderConfig] = {
    "deepseek": ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4",          # TODO: 换成账号实际可用的 v4 系列模型 id
        api_key_env="DEEPSEEK_API_KEY",
        cache_telemetry_field="prompt_cache_hit_tokens",
        cache_ttl_s=300,
    ),
    "openai": ProviderConfig(
        name="openai",
        base_url=None,
        model="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
        cache_telemetry_field=None,   # OpenAI 自动前缀缓存，usage 字段接入时再定
        cache_ttl_s=300,
    ),
    "anthropic": ProviderConfig(
        name="anthropic",
        base_url=None,
        model="claude-sonnet-4-5",
        api_key_env="ANTHROPIC_API_KEY",
        cache_telemetry_field="cache_read_input_tokens",  # 显式 cache_control 断点
        cache_ttl_s=300,
    ),
    "fake": ProviderConfig(
        name="fake", base_url=None, model="fake-1", api_key_env="",
        cache_telemetry_field=None, cache_ttl_s=300,
    ),
}


@dataclass(frozen=True)
class Settings:
    provider: ProviderConfig
    workspace: Path = field(default_factory=Path.cwd)
    sessions_dir: Path = field(default_factory=lambda: Path("sessions"))
    max_turns: int = 50                 # 单次 run_turn 内工具循环上限（防失控）
    warmup_turns: int = 5               # 延迟激活：前 N 轮只挂 core 工具
    compaction_threshold: int = 60_000  # 估算 token 超过此值才考虑压缩
    keep_recent_turns: int = 6          # 压缩时保留最近 N 轮原文
    lazy_activation: bool = True
    auto_approve: frozenset[str] = frozenset()  # 会话内预授权的工具名（bash 等仍可被 ASK 规则覆盖）


def load_settings(provider_name: str | None = None, model: str | None = None,
                  workspace: str | None = None, fake: bool = False) -> Settings:
    """CLI 参数 > 环境变量 MINICLAUDE_PROVIDER/MODEL > 默认 deepseek。"""
    name = "fake" if fake else (provider_name or os.environ.get("MINICLAUDE_PROVIDER", "deepseek"))
    if name not in PROVIDERS:
        raise SystemExit(f"unknown provider: {name} (可选: {', '.join(PROVIDERS)})")
    cfg = PROVIDERS[name]
    if model:
        cfg = ProviderConfig(**{**cfg.__dict__, "model": model})
    return Settings(provider=cfg,
                    workspace=Path(workspace).resolve() if workspace else Path.cwd())
