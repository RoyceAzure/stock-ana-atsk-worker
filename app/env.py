from __future__ import annotations

import os

from core.config.config import Config
from core.logger.logger import parse_log_level


def ensure_env_loaded() -> Config:
    """載入 .env 並合併環境變數（環境變數優先）。可重複呼叫，僅初始化一次。"""
    os.environ.setdefault("DBDRIVERFILE", "")
    return Config()


def env_str(key: str, default: str | None = None) -> str:
    ensure_env_loaded()
    value = os.getenv(key)
    if value is None or value == "":
        if default is None:
            raise ValueError(f"缺少必要環境變數: {key}")
        return default
    return value


def env_int(key: str, default: int) -> int:
    ensure_env_loaded()
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    return int(raw)


def env_log_level(default: str = "info") -> int:
    """讀取 LOG_LEVEL（info / debug），預設 info。"""
    return parse_log_level(env_str("LOG_LEVEL", default))
