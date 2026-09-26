"""Central configuration. Secrets only from environment, never hardcoded."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    github_token: str = field(default_factory=lambda: _get("GITHUB_TOKEN"))
    github_webhook_secret: str = field(default_factory=lambda: _get("GITHUB_WEBHOOK_SECRET"))
    llm_api_key: str = field(default_factory=lambda: _get("LLM_API_KEY"))
    llm_base_url: str = field(default_factory=lambda: _get("LLM_BASE_URL"))
    llm_model: str = field(default_factory=lambda: _get("LLM_MODEL"))
    bob_api_key: str = field(default_factory=lambda: _get("BOB_API_KEY"))
    bob_base_url: str = field(default_factory=lambda: _get("BOB_BASE_URL"))
    report_dir: str = field(default_factory=lambda: _get("REPORT_DIR", "./reports"))
    database_url: str = field(default_factory=lambda: _get("DATABASE_URL", ""))
    # Laya AI
    laya_model_path: str = field(default_factory=lambda: _get("LAYA_MODEL_PATH", ""))
    # MutaCI
    mutation_runner: str = field(default_factory=lambda: _get("MUTATION_RUNNER", "stub"))
    # CausalTrace
    sentry_dsn: str = field(default_factory=lambda: _get("SENTRY_DSN", ""))
    datadog_api_key: str = field(default_factory=lambda: _get("DATADOG_API_KEY", ""))
    datadog_app_key: str = field(default_factory=lambda: _get("DATADOG_APP_KEY", ""))
    jaeger_url: str = field(default_factory=lambda: _get("JAEGER_URL", "http://localhost:16686"))
    # BugPort
    bugport_store: str = field(default_factory=lambda: _get("BUGPORT_STORE", "./reports/bugport-snapshots"))

    @property
    def bob_enabled(self) -> bool:
        return bool(self.bob_api_key and self.bob_base_url and "REPLACE_ME" not in self.bob_api_key)

    def redacted(self) -> dict:
        """Safe to log: never include secret values."""

        def _redact(v: str) -> str:
            return "set" if v and "REPLACE_ME" not in v else "unset"

        return {
            "github_token": _redact(self.github_token),
            "llm_api_key": _redact(self.llm_api_key),
            "bob": "enabled" if self.bob_enabled else "disabled-local-fallback",
            "report_dir": self.report_dir,
        }


SECRET_KEYS = ("token", "api_key", "authorization", "secret", "password")


def redact_dict(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if any(s in k.lower() for s in SECRET_KEYS):
            out[k] = "***REDACTED***"
        elif isinstance(v, dict):
            out[k] = redact_dict(v)
        elif isinstance(v, str) and v.startswith("ghp_"):
            out[k] = "ghp_***REDACTED***"
        else:
            out[k] = v
    return out
