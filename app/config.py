from __future__ import annotations

from dataclasses import dataclass

from app.cloud.gcp_profile import GcpWorkerProfile
from app.cloud.provider import CloudProvider
from app.env import ensure_env_loaded, env_int, env_str
from app.task.profile import TaskWorkerProfile
from infra.repo.pg_dao import DBConfig


@dataclass(frozen=True)
class WorkerConfig:
    """Worker 共用設定；雲端專用欄位由對應 profile 承載。"""

    cloud_provider: CloudProvider
    pg_host: str
    pg_database: str
    pg_user: str
    pg_password: str
    pg_port: int
    duckdb_pool_size: int = 10
    pg_pool_min_conn: int = 1
    pg_pool_max_conn: int = 10
    shutdown_drain_timeout: float = 30.0
    gcp: GcpWorkerProfile | None = None
    task: TaskWorkerProfile | None = None

    @classmethod
    def from_env(cls) -> WorkerConfig:
        ensure_env_loaded()

        provider_raw = env_str("CLOUD_PROVIDER", CloudProvider.GCP.value).lower()
        try:
            cloud_provider = CloudProvider(provider_raw)
        except ValueError as exc:
            supported = ", ".join(p.value for p in CloudProvider)
            raise ValueError(
                f"不支援的 CLOUD_PROVIDER: {provider_raw}（支援: {supported}）"
            ) from exc

        gcp: GcpWorkerProfile | None = None
        if cloud_provider is CloudProvider.GCP:
            gcp = GcpWorkerProfile.from_env()
        elif cloud_provider is CloudProvider.AWS:
            raise NotImplementedError(
                "AWS worker（SQS + S3）尚未實作，請設定 CLOUD_PROVIDER=gcp"
            )

        task = TaskWorkerProfile.from_env()

        return cls(
            cloud_provider=cloud_provider,
            pg_host=env_str("PG_HOST", "localhost"),
            pg_database=env_str("PG_DATABASE", "sexy_stock"),
            pg_user=env_str("PG_USER", "postgres"),
            pg_password=env_str("PG_PASSWORD", "password"),
            pg_port=env_int("PG_PORT", 5432),
            duckdb_pool_size=env_int("DUCKDB_POOL_SIZE", 10),
            pg_pool_min_conn=env_int("PG_POOL_MIN_CONN", 1),
            pg_pool_max_conn=env_int("PG_POOL_MAX_CONN", 10),
            shutdown_drain_timeout=float(env_str("SHUTDOWN_DRAIN_TIMEOUT", "30.0")),
            gcp=gcp,
            task=task,
        )

    @property
    def db_config(self) -> DBConfig:
        return DBConfig(
            host=self.pg_host,
            database=self.pg_database,
            user=self.pg_user,
            password=self.pg_password,
            port=self.pg_port,
        )

    @property
    def db_config_dict(self) -> dict:
        return self.db_config.as_dict()
