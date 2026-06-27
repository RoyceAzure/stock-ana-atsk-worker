from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import duckdb

from infra.repo.duckdb.config import DuckDBStorageConfig
from infra.repo.gcp.gcp_auth import (
    GcpAuthMode,
    gcp_auth_mode_from_env,
    gcp_service_account_key_file_from_env,
    refresh_gcp_access_token,
)

logger = logging.getLogger(__name__)

_DEFAULT_SECRET_NAME = "object_storage_config"
_DEFAULT_URI_SCHEME = "gs"


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


@dataclass
class GcsDuckDBConfig(DuckDBStorageConfig):
    """GCS 連線：httpfs TYPE gcs + ADC / SA JSON bearer token。"""

    auth_mode: GcpAuthMode = GcpAuthMode.ADC
    service_account_key_file: Optional[str] = None
    secret_name: str = _DEFAULT_SECRET_NAME
    uri_scheme: str = _DEFAULT_URI_SCHEME

    @classmethod
    def from_env(cls) -> "GcsDuckDBConfig":
        return cls(
            auth_mode=gcp_auth_mode_from_env(),
            service_account_key_file=gcp_service_account_key_file_from_env(),
        )

    def setup_connection(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(self.build_secret_sql())
        if self.auth_mode is GcpAuthMode.ADC:
            logger.info("[DuckDB GCS] 憑證模式: ADC（Workload Identity / 預設應用程式憑證）")
        else:
            logger.info(
                "[DuckDB GCS] 憑證模式: service_account_json (%s)",
                self.service_account_key_file,
            )

    def build_secret_sql(self) -> str:
        token = _sql_literal(
            refresh_gcp_access_token(
                auth_mode=self.auth_mode,
                service_account_key_file=self.service_account_key_file,
            )
        )
        return f"""
            CREATE OR REPLACE SECRET {self.secret_name} (
                TYPE GCS,
                BEARER_TOKEN '{token}'
            );
        """

    def object_uri(self, bucket: str, key: str = "") -> str:
        base = f"{self.uri_scheme}://{bucket.strip('/')}"
        if not key:
            return base
        return f"{base}/{key.lstrip('/')}"
