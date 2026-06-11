from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Tuple

from core.config.config import Config


class StorageBackend(str, Enum):
    S3 = "s3"
    MINIO = "minio"
    GCS = "gcs"


_URI_PREFIXES: Tuple[str, ...] = ("s3://", "gs://", "gcs://")


def object_uri(config: ObjectStorageConfig, bucket: str, key: str = "") -> str:
    scheme = config.effective_uri_scheme
    base = f"{scheme}://{bucket.strip('/')}"
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
    return f"{config.effective_uri_scheme}://{normalized}"


to_fs_uri = to_duckdb_uri


def split_object_path(full_path: str) -> Tuple[str, str]:
    normalized = strip_uri_scheme(full_path)
    parts = normalized.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid object path, expected 'bucket/key': {full_path}")
    return parts[0], parts[1]


@dataclass
class ObjectStorageConfig:
    backend: StorageBackend = StorageBackend.S3
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    region: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    use_adc: bool = False

    @property
    def effective_uri_scheme(self) -> str:
        if self.backend is StorageBackend.GCS and self.use_adc:
            return "gs"
        return "s3"

    @property
    def uses_gcs_s3_interop(self) -> bool:
        return (
            self.backend is StorageBackend.GCS
            and not self.use_adc
            and bool(self.access_key)
            and bool(self.secret_key)
        )

    @classmethod
    def from_env(cls, backend: StorageBackend) -> "ObjectStorageConfig":
        config = Config()
        if backend is StorageBackend.MINIO:
            return cls(
                backend=backend,
                access_key=_config_value(config, "MINIO_ROOT_USER"),
                secret_key=_config_value(config, "MINIO_ROOT_PASSWORD"),
                region=_config_value(config, "AWS_REGION", "us-east-1"),
                host=_config_value(config, "MINIO_HOST"),
                port=int(_config_value(config, "MINIO_PORT", "9000")),
            )
        if backend is StorageBackend.S3:
            return cls(
                backend=backend,
                access_key=_config_value(config, "AWS_ACCESS_KEY_ID"),
                secret_key=_config_value(config, "AWS_SECRET_ACCESS_KEY"),
                region=_config_value(config, "AWS_REGION", "us-east-1"),
            )
        if backend is StorageBackend.GCS:
            return cls(
                backend=backend,
                access_key=_config_value(config, "GCS_HMAC_ACCESS_KEY"),
                secret_key=_config_value(config, "GCS_HMAC_SECRET_KEY"),
                use_adc=_truthy(_config_value(config, "GCS_USE_ADC", "false")),
            )
        raise ValueError(f"Unsupported storage backend: {backend}")

    def object_uri(self, bucket: str, key: str = "") -> str:
        return object_uri(self, bucket, key)


def _config_value(config: Config, key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        value = getattr(config, key)
    except AttributeError:
        return default
    if value is None or value == "":
        return default
    return str(value)


def _truthy(value: Optional[str]) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def create_filesystem(config: ObjectStorageConfig) -> Any:
    if config.backend is StorageBackend.GCS and config.use_adc:
        import gcsfs

        return gcsfs.GCSFileSystem()

    import s3fs

    client_kwargs: dict[str, Any] = {}
    if config.region:
        client_kwargs["region_name"] = config.region

    if config.uses_gcs_s3_interop:
        client_kwargs["endpoint_url"] = "https://storage.googleapis.com"
        return s3fs.S3FileSystem(
            key=config.access_key,
            secret=config.secret_key,
            client_kwargs=client_kwargs,
        )

    if config.backend is StorageBackend.MINIO:
        use_ssl = _truthy(_config_value(Config(), "MINIO_SECURE", "true"))
        scheme = "https" if use_ssl else "http"
        client_kwargs["endpoint_url"] = f"{scheme}://{config.host}:{config.port}"
        return s3fs.S3FileSystem(
            key=config.access_key,
            secret=config.secret_key,
            client_kwargs=client_kwargs,
            use_ssl=use_ssl,
        )

    return s3fs.S3FileSystem(
        key=config.access_key,
        secret=config.secret_key,
        client_kwargs=client_kwargs or None,
    )


def create_parquet_merger(bucket_base_path: str, storage_config: ObjectStorageConfig):
    from infra.repo.data_meger.s3_parquet_meger import S3ParquetMerger

    return S3ParquetMerger(
        create_filesystem(storage_config),
        bucket_base_path,
        storage_config,
    )


def location_to_backend(location: str) -> StorageBackend:
    mapping = {
        "minio": StorageBackend.MINIO,
        "s3": StorageBackend.S3,
        "gcs": StorageBackend.GCS,
    }
    try:
        return mapping[location.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported object storage location: {location}") from exc
