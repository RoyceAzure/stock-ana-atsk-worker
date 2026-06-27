from unittest.mock import MagicMock

import pytest

from infra.repo.duckdb.gcs_config import GcsDuckDBConfig
from infra.repo.gcp.gcp_auth import GcpAuthMode


class TestGcsDuckDBConfig:
    def test_build_secret_sql_uses_bearer_token(self, mocker):
        mocker.patch(
            "infra.repo.duckdb.gcs_config.refresh_gcp_access_token",
            return_value="test-token",
        )
        config = GcsDuckDBConfig(auth_mode=GcpAuthMode.ADC)
        sql = config.build_secret_sql()

        assert "TYPE GCS" in sql
        assert "BEARER_TOKEN 'test-token'" in sql
        assert "KEY_ID" not in sql

    def test_build_secret_sql_service_account_json(self, mocker):
        refresh = mocker.patch(
            "infra.repo.duckdb.gcs_config.refresh_gcp_access_token",
            return_value="sa-token",
        )
        config = GcsDuckDBConfig(
            auth_mode=GcpAuthMode.SERVICE_ACCOUNT_JSON,
            service_account_key_file="/keys/sa.json",
        )
        sql = config.build_secret_sql()

        assert "BEARER_TOKEN 'sa-token'" in sql
        refresh.assert_called_once_with(
            auth_mode=GcpAuthMode.SERVICE_ACCOUNT_JSON,
            service_account_key_file="/keys/sa.json",
        )

    def test_object_uri_uses_gs_scheme(self):
        config = GcsDuckDBConfig()
        assert config.object_uri("my-bucket", "path/file.parquet") == (
            "gs://my-bucket/path/file.parquet"
        )

    def test_sql_literal_escapes_single_quotes(self, mocker):
        mocker.patch(
            "infra.repo.duckdb.gcs_config.refresh_gcp_access_token",
            return_value="tok'en",
        )
        config = GcsDuckDBConfig()
        sql = config.build_secret_sql()
        assert "tok''en" in sql

    def test_setup_connection_installs_httpfs_and_secret(self, mocker):
        mocker.patch(
            "infra.repo.duckdb.gcs_config.refresh_gcp_access_token",
            return_value="token",
        )
        config = GcsDuckDBConfig()
        con = MagicMock()
        config.setup_connection(con)
        assert con.execute.call_count == 2
