from __future__ import annotations

from infra.repo.duckdb.config import DuckDBStorageConfig
from infra.repo.duckdb.gcs_config import GcsDuckDBConfig
from infra.repo.object_storage import StorageBackend


def from_env(backend: StorageBackend) -> DuckDBStorageConfig:
    if backend is StorageBackend.GCS:
        return GcsDuckDBConfig.from_env()
    raise NotImplementedError(f"DuckDB 後端尚未實作: {backend.value}")
