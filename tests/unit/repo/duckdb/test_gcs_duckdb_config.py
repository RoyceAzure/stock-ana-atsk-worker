import pytest

from infra.repo.duckdb.gcs_config import GcsDuckDBConfig


class TestGcsDuckDBConfig:
    def test_build_secret_sql_uses_hmac_type_gcs(self):
        config = GcsDuckDBConfig(
            hmac_access_key="test-access",
            hmac_secret_key="test-secret",
        )
        sql = config.build_secret_sql()

        assert "TYPE gcs" in sql
        assert "KEY_ID 'test-access'" in sql
        assert "SECRET 'test-secret'" in sql
        assert "credential_chain" not in sql

    def test_object_uri_uses_gs_scheme(self):
        config = GcsDuckDBConfig(
            hmac_access_key="ak",
            hmac_secret_key="sk",
        )
        assert config.object_uri("my-bucket", "path/file.parquet") == (
            "gs://my-bucket/path/file.parquet"
        )

    def test_requires_hmac_keys(self):
        with pytest.raises(ValueError, match="HMAC"):
            GcsDuckDBConfig(hmac_access_key="", hmac_secret_key="sk")

    def test_sql_literal_escapes_single_quotes(self):
        config = GcsDuckDBConfig(
            hmac_access_key="key'with'quote",
            hmac_secret_key="secret",
        )
        sql = config.build_secret_sql()
        assert "key''with''quote" in sql
