from __future__ import annotations

from dataclasses import dataclass

from app.env import env_int, env_str


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
        storage_backend = env_str("STORAGE_BACKEND", "gcs").lower()
        if storage_backend != "gcs":
            raise ValueError(
                "CLOUD_PROVIDER=gcp 時 STORAGE_BACKEND 必須為 gcs，"
                f"目前為: {storage_backend}"
            )

        return cls(
            project_id=env_str("GCP_PROJECT_ID"),
            subscription_id=env_str("GCP_TASK_SUBSCRIPTION_ID"),
            object_storage_bucket_base_path=env_str("OBJECT_STORAGE_BUCKET_BASE_PATH"),
            pubsub_batch_size=env_int("PUBSUB_BATCH_SIZE", 10),
            pubsub_visibility_timeout=env_int("PUBSUB_VISIBILITY_TIMEOUT", 30),
            pubsub_pull_timeout=float(env_str("PUBSUB_PULL_TIMEOUT", "5.0")),
        )
