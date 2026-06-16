"""DuckDB GCS CRUD 整合測試（httpfs TYPE gcs + HMAC）。

前置條件（.env 或環境變數）：
- GCS_HMAC_ACCESS_KEY / GCS_HMAC_SECRET_KEY
- GCS_TEST_BUCKET（可選，預設見 conftest）
"""

import duckdb
import pytest

from infra.repo.object_storage import object_uri
from tests.integration.repo.duckdb.conftest import gcs_test_bucket, track_gcs_path

pytestmark = [pytest.mark.integration, pytest.mark.integration_gcs]


class TestDuckDBGcsCrud:
    """DuckDB 透過 gs:// 對 GCS parquet 做簡單 CRUD。"""

    def test_gcs_parquet_crud(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_duckdb_config,
        gcs_storage_config,
        gcs_test_path: str,
        gcs_created_paths: list[str],
        gcs_fs,
    ):
        rel_path = f"{gcs_test_path}/crud.parquet"
        track_gcs_path(gcs_created_paths, rel_path)
        duck_uri = gcs_duckdb_config.object_uri(gcs_test_bucket(), rel_path)
        fs_uri = object_uri(gcs_storage_config, gcs_test_bucket(), rel_path)

        # Create
        duckdb_conn.execute(
            f"""
            COPY (
                SELECT 1 AS id, '2330' AS code, 580.0::DOUBLE AS close
            ) TO '{duck_uri}' (FORMAT PARQUET, CODEC 'SNAPPY')
            """
        )
        assert gcs_fs.exists(fs_uri)

        # Read
        rows = duckdb_conn.execute(
            f"SELECT id, code, close FROM read_parquet('{duck_uri}') ORDER BY id"
        ).fetchall()
        assert rows == [(1, "2330", 580.0)]

        # Update（覆寫同一路徑）
        duckdb_conn.execute(
            f"""
            COPY (
                SELECT 1 AS id, '2330' AS code, 600.0::DOUBLE AS close
            ) TO '{duck_uri}' (FORMAT PARQUET, CODEC 'SNAPPY')
            """
        )
        updated = duckdb_conn.execute(
            f"SELECT close FROM read_parquet('{duck_uri}')"
        ).fetchone()
        assert updated == (600.0,)

        # Delete（DuckDB 無刪除 API，透過 fsspec 刪除後應無法再讀）
        gcs_fs.rm(fs_uri)
        assert not gcs_fs.exists(fs_uri)
        with pytest.raises(duckdb.Error):
            duckdb_conn.execute(f"SELECT 1 FROM read_parquet('{duck_uri}')").fetchall()
