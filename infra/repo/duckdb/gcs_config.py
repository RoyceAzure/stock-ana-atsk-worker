from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import duckdb

from core.config.config import Config
from infra.repo.duckdb.config import DuckDBStorageConfig

_DEFAULT_SECRET_NAME = "object_storage_config"
_DEFAULT_URI_SCHEME = "gs"


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _config_value(config: Config, key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        value = getattr(config, key)
    except AttributeError:
        return default
    if value is None or value == "":
        return default
    return str(value)


@dataclass
class GcsDuckDBConfig(DuckDBStorageConfig):
    """GCS 連線：httpfs TYPE gcs + HMAC 金鑰（方案 A）。"""

    hmac_access_key: str
    hmac_secret_key: str
    secret_name: str = _DEFAULT_SECRET_NAME
    uri_scheme: str = _DEFAULT_URI_SCHEME

    def __post_init__(self) -> None:
        if not self.hmac_access_key or not self.hmac_secret_key:
            raise ValueError(
                "GcsDuckDBConfig 需設定 GCS HMAC access key 與 secret key"
            )

    @classmethod
    def from_env(cls) -> "GcsDuckDBConfig":
        config = Config()
        access_key = _config_value(config, "GCS_HMAC_ACCESS_KEY")
        secret_key = _config_value(config, "GCS_HMAC_SECRET_KEY")
        if not access_key or not secret_key:
            raise ValueError(
                "GCS DuckDB 連線需設定環境變數 GCS_HMAC_ACCESS_KEY 與 GCS_HMAC_SECRET_KEY"
            )
        return cls(hmac_access_key=access_key, hmac_secret_key=secret_key)

    def setup_connection(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(self.build_secret_sql())

    def build_secret_sql(self) -> str:
        key_id = _sql_literal(self.hmac_access_key)
        secret = _sql_literal(self.hmac_secret_key)
        return f"""
            CREATE OR REPLACE SECRET {self.secret_name} (
                TYPE gcs,
                KEY_ID '{key_id}',
                SECRET '{secret}'
            );
        """

    def object_uri(self, bucket: str, key: str = "") -> str:
        base = f"{self.uri_scheme}://{bucket.strip('/')}"
        if not key:
            return base
        return f"{base}/{key.lstrip('/')}"
