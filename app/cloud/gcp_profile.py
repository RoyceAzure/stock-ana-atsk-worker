from __future__ import annotations

import os
from dataclasses import dataclass

from core.config.config import Config


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
class GcpWorkerProfile:
    """GCP worker 專用設定：Pub/Sub 收任務、GCS 寫入。"""

    project_id: str
    subscription_id: str
    object_storage_bucket_base_path: str
    pubsub_batch_size: int = 10
    pubsub_visibility_timeout: int = 30
    pubsub_pull_timeout: float = 5.0

    @classmethod
    def from_env(cls) -> GcpWorkerProfile:
        os.environ.setdefault("DBDRIVERFILE", "")
        Config()

        storage_backend = _env_str("STORAGE_BACKEND", "gcs").lower()
        if storage_backend != "gcs":
            raise ValueError(
                "CLOUD_PROVIDER=gcp 時 STORAGE_BACKEND 必須為 gcs，"
                f"目前為: {storage_backend}"
            )

        return cls(
            project_id=_env_str("GCP_PROJECT_ID"),
            subscription_id=_env_str("GCP_SUBSCRIPTION_ID"),
            object_storage_bucket_base_path=_env_str("OBJECT_STORAGE_BUCKET_BASE_PATH"),
            pubsub_batch_size=_env_int("PUBSUB_BATCH_SIZE", 10),
            pubsub_visibility_timeout=_env_int("PUBSUB_VISIBILITY_TIMEOUT", 30),
            pubsub_pull_timeout=float(_env_str("PUBSUB_PULL_TIMEOUT", "5.0")),
        )
