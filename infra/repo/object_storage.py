from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Tuple

from infra.repo.gcp.gcp_auth import (
    GcpAuthMode,
    create_gcs_filesystem,
    gcp_auth_mode_from_env,
    gcp_service_account_key_file_from_env,
)


class StorageBackend(str, Enum):
    GCS = "gcs"


_URI_PREFIXES: Tuple[str, ...] = ("gs://", "gcs://", "s3://")


def object_uri(config: ObjectStorageConfig, bucket: str, key: str = "") -> str:
    base = f"gs://{bucket.strip('/')}"
    if not key:
        return base
    return f"{base}/{key.lstrip('/')}"


def strip_uri_scheme(path: str) -> str:
    for prefix in _URI_PREFIXES:
        if path.startswith(prefix):
            return path[len(prefix) :].rstrip("/")
    return path.rstrip("/")


def to_duckdb_uri(config: ObjectStorageConfig, path: str) -> str:
    normalized = strip_uri_scheme(path)
    return f"gs://{normalized}"


def to_duckdb_httpfs_uri(config: ObjectStorageConfig, bucket: str, key: str = "") -> str:
    """DuckDB httpfs COPY/READ 用的 URI（gs:// + TYPE gcs HMAC secret）。"""
    from infra.repo.duckdb.gcs_config import GcsDuckDBConfig

    return GcsDuckDBConfig.from_env().object_uri(bucket, key)


to_fs_uri = to_duckdb_uri


def split_object_path(full_path: str) -> Tuple[str, str]:
    normalized = strip_uri_scheme(full_path)
    parts = normalized.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid object path, expected 'bucket/key': {full_path}")
    return parts[0], parts[1]


@dataclass
class ObjectStorageConfig:
    backend: StorageBackend = StorageBackend.GCS
    auth_mode: GcpAuthMode = GcpAuthMode.ADC
    service_account_key_file: Optional[str] = None

    @property
    def effective_uri_scheme(self) -> str:
        return "gs"

    @classmethod
    def from_env(cls, backend: StorageBackend = StorageBackend.GCS) -> ObjectStorageConfig:
        if backend is not StorageBackend.GCS:
            raise ValueError(f"目前僅支援 GCS 物件儲存，收到: {backend.value}")
        return cls(
            backend=StorageBackend.GCS,
            auth_mode=gcp_auth_mode_from_env(),
            service_account_key_file=gcp_service_account_key_file_from_env(),
        )

    def object_uri(self, bucket: str, key: str = "") -> str:
        return object_uri(self, bucket, key)


def create_filesystem(config: ObjectStorageConfig) -> Any:
    if config.backend is not StorageBackend.GCS:
        raise ValueError(f"目前僅支援 GCS 物件儲存，收到: {config.backend.value}")
    return create_gcs_filesystem(
        auth_mode=config.auth_mode,
        service_account_key_file=config.service_account_key_file,
    )


def create_parquet_merger(bucket_base_path: str, storage_config: ObjectStorageConfig):
    from infra.repo.data_meger.blob_parquet_meger import BlobParquetMerger
    from infra.repo.duckdb.factory import from_env

    return BlobParquetMerger(
        create_filesystem(storage_config),
        bucket_base_path,
        from_env(storage_config.backend),
    )


def create_parquet_helper(bucket_base_path: str, storage_config: ObjectStorageConfig):
    from infra.repo.data_helper.blob_parquet_helper import BlobParquetDataHelper
    from infra.repo.duckdb.factory import from_env

    return BlobParquetDataHelper(
        create_filesystem(storage_config),
        bucket_base_path,
        from_env(storage_config.backend),
    )


def location_to_backend(location: str) -> StorageBackend:
    if location.lower() != StorageBackend.GCS.value:
        raise ValueError(
            f"目前僅支援 GCS 物件儲存，收到 location: {location!r}"
        )
    return StorageBackend.GCS
