"""DuckDB + GCS 整合測試（httpfs TYPE gcs + HMAC）。

前置條件：
- GCS_TEST_BUCKET：測試用 bucket（預設 conftest 常數，可用環境變數覆蓋）
- GCS_HMAC_ACCESS_KEY / GCS_HMAC_SECRET_KEY：GCS HMAC 金鑰（寫入 .env 或環境變數）
"""

import duckdb
import pytest

from infra.repo.duckdb.gcs_config import GcsDuckDBConfig
from infra.repo.duckdb_manager import DuckDBManager
from infra.repo.object_storage import object_uri
from tests.integration.repo.duckdb.conftest import gcs_test_bucket, track_gcs_path

pytestmark = [pytest.mark.integration, pytest.mark.integration_gcs]


class TestDuckDBGcsIntegration:
    """驗證 DuckDB 透過 GcsDuckDBConfig（HMAC + gs://）讀寫 GCS。"""

    def test_gs_uri_scheme(
        self,
        gcs_duckdb_config: GcsDuckDBConfig,
    ):
        uri = gcs_duckdb_config.object_uri(gcs_test_bucket(), "path/file.parquet")
        assert uri.startswith("gs://")
        assert uri == f"gs://{gcs_test_bucket()}/path/file.parquet"

    def test_copy_to_gcs_and_read_parquet(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_duckdb_config: GcsDuckDBConfig,
        gcs_storage_config,
        gcs_test_path: str,
        gcs_created_paths: list[str],
        gcs_fs,
    ):
        rel_path = f"{gcs_test_path}/sample.parquet"
        track_gcs_path(gcs_created_paths, rel_path)
        duck_uri = gcs_duckdb_config.object_uri(gcs_test_bucket(), rel_path)
        fs_uri = object_uri(gcs_storage_config, gcs_test_bucket(), rel_path)

        assert duck_uri.startswith("gs://")
        assert fs_uri.startswith("s3://")

        duckdb_conn.execute(
            f"""
            COPY (
                SELECT 1 AS id, '2330' AS code, 580.0::DOUBLE AS close
            ) TO '{duck_uri}' (FORMAT PARQUET, CODEC 'SNAPPY')
            """
        )

        assert gcs_fs.exists(fs_uri)
        rows = duckdb_conn.execute(
            f"SELECT id, code, close FROM read_parquet('{duck_uri}') ORDER BY id"
        ).fetchall()
        assert rows == [(1, "2330", 580.0)]

    def test_read_parquet_limit_zero_returns_schema(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_duckdb_config: GcsDuckDBConfig,
        gcs_test_path: str,
        gcs_created_paths: list[str],
    ):
        rel_path = f"{gcs_test_path}/schema.parquet"
        track_gcs_path(gcs_created_paths, rel_path)
        uri = gcs_duckdb_config.object_uri(gcs_test_bucket(), rel_path)

        duckdb_conn.execute(
            f"""
            COPY (
                SELECT '2330' AS code, 580.0::DOUBLE AS close
            ) TO '{uri}' (FORMAT PARQUET, CODEC 'SNAPPY')
            """
        )

        schema_df = duckdb_conn.execute(
            f"SELECT * FROM read_parquet('{uri}') LIMIT 0"
        ).df()
        assert set(schema_df.columns) == {"code", "close"}


class TestDuckDBManagerPool:
    """DuckDBManager 連線池行為（使用已初始化的 GCS 設定）。"""

    def test_return_conn_reuses_pool_connection(self, duckdb_manager_gcs):
        # initialize(pool_size=2) 會預放多條連線；Queue 為 FIFO，
        # 歸還後再 get 可能拿到池中「另一條」連線，而非剛歸還的那條。
        parked = []
        while not DuckDBManager._pool.empty():
            parked.append(DuckDBManager._pool.get_nowait())

        conn = DuckDBManager.get_conn()
        DuckDBManager.return_conn(conn)

        reused = DuckDBManager.get_conn()
        try:
            assert reused is conn
        finally:
            DuckDBManager.return_conn(reused)
            for parked_conn in parked:
                DuckDBManager.return_conn(parked_conn)

    def test_get_conn_creates_connection_when_pool_empty(self, duckdb_manager_gcs):
        connections = [DuckDBManager.get_conn() for _ in range(3)]
        try:
            for con in connections:
                assert con is not None
                result = con.execute("SELECT 1").fetchone()
                assert result == (1,)
        finally:
            for con in connections:
                DuckDBManager.return_conn(con)

    def test_return_and_delete_removes_bad_connection(self, duckdb_manager_gcs):
        conn = DuckDBManager.get_conn()
        conn.close()

        DuckDBManager.return_and_delete(conn)

        replacement = DuckDBManager.get_conn()
        try:
            assert replacement is not conn
            assert replacement.execute("SELECT 1").fetchone() == (1,)
        finally:
            DuckDBManager.return_conn(replacement)
