from __future__ import annotations

from dataclasses import dataclass

from app.cloud.gcp_profile import GcpWorkerProfile
from app.cloud.provider import CloudProvider
from app.config import WorkerConfig
from infra.repo.duckdb.config import DuckDBStorageConfig
from infra.repo.duckdb.factory import from_env as duckdb_config_from_env
from infra.repo.object_storage import ObjectStorageConfig, StorageBackend
from service.consumer.gcp_consumer import PubSubConsumerConfig


@dataclass(frozen=True)
class CloudWorkerAssembly:
    """第一層組裝結果：雲端 queue + 物件儲存相關模組設定。"""

    storage_config: ObjectStorageConfig
    duckdb_config: DuckDBStorageConfig
    object_storage_bucket_base_path: str
    pubsub_config: PubSubConsumerConfig


def build_cloud_worker_assembly(config: WorkerConfig) -> CloudWorkerAssembly:
    """依雲端廠商組裝 consumer 與儲存層所需設定。"""

    if config.cloud_provider is not CloudProvider.GCP:
        raise ValueError(
            f"目前僅支援 CLOUD_PROVIDER=gcp，收到: {config.cloud_provider.value}"
        )

    return _build_gcp_assembly(config)


def _build_gcp_assembly(config: WorkerConfig) -> CloudWorkerAssembly:
    if config.gcp is None:
        raise ValueError("CLOUD_PROVIDER=gcp 時必須提供 GcpWorkerProfile")

    gcp: GcpWorkerProfile = config.gcp
    storage_backend = StorageBackend.GCS
    storage_config = ObjectStorageConfig.from_env(storage_backend)
    duckdb_config = duckdb_config_from_env(storage_backend)

    pubsub_config = PubSubConsumerConfig(
        project_id=gcp.project_id,
        subscription_id=gcp.subscription_id,
        batch_size=gcp.pubsub_batch_size,
        visibility_timeout=gcp.pubsub_visibility_timeout,
        pull_timeout=gcp.pubsub_pull_timeout,
        shutdown_drain_timeout=config.shutdown_drain_timeout,
        auth_mode=gcp.pubsub_auth_mode,
        service_account_key_file=gcp.pubsub_service_account_key_file,
    )

    return CloudWorkerAssembly(
        storage_config=storage_config,
        duckdb_config=duckdb_config,
        object_storage_bucket_base_path=gcp.object_storage_bucket_base_path,
        pubsub_config=pubsub_config,
    )
