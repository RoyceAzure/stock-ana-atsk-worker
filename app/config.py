from __future__ import annotations

import os
from dataclasses import dataclass

from core.config.config import Config
from infra.repo.object_storage import StorageBackend


def _env_str(key: str, default: str | None = None) -> str:
    value = os.getenv(key)
    if value is None or value == "":
        if default is None:
            raise ValueError(f"缺少必要環境變數: {key}")
        return default
    return value


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class WorkerConfig:
    pg_host: str
    pg_database: str
    pg_user: str
    pg_password: str
    pg_port: int
    storage_backend: StorageBackend
    object_storage_bucket_base_path: str
    gcp_project_id: str
    gcp_subscription_id: str
    duckdb_pool_size: int = 10
    pubsub_batch_size: int = 10
    pubsub_visibility_timeout: int = 30
    pubsub_pull_timeout: float = 5.0

    @classmethod
    def from_env(cls) -> WorkerConfig:
        # Config 單例會讀取 DBDRIVERFILE；worker 流程未使用 DRIVER_PATH，給空值避免初始化失敗。
        os.environ.setdefault("DBDRIVERFILE", "")
        Config()

        backend_raw = _env_str("STORAGE_BACKEND", "gcs").lower()
        backend = StorageBackend(backend_raw)

        return cls(
            pg_host=_env_str("PG_HOST", "localhost"),
            pg_database=_env_str("PG_DATABASE", "sexy_stock"),
            pg_user=_env_str("PG_USER", "postgres"),
            pg_password=_env_str("PG_PASSWORD", "password"),
            pg_port=_env_int("PG_PORT", 5432),
            storage_backend=backend,
            object_storage_bucket_base_path=_env_str("OBJECT_STORAGE_BUCKET_BASE_PATH"),
            gcp_project_id=_env_str("GCP_PROJECT_ID"),
            gcp_subscription_id=_env_str("GCP_SUBSCRIPTION_ID"),
            duckdb_pool_size=_env_int("DUCKDB_POOL_SIZE", 10),
            pubsub_batch_size=_env_int("PUBSUB_BATCH_SIZE", 10),
            pubsub_visibility_timeout=_env_int("PUBSUB_VISIBILITY_TIMEOUT", 30),
            pubsub_pull_timeout=float(_env_str("PUBSUB_PULL_TIMEOUT", "5.0")),
        )

    @property
    def db_config_dict(self) -> dict:
        return {
            "host": self.pg_host,
            "database": self.pg_database,
            "user": self.pg_user,
            "password": self.pg_password,
            "port": self.pg_port,
        }
