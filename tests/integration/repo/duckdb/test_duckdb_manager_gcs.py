import duckdb
import pytest

from infra.repo.duckdb_manager import DuckDBManager
from infra.repo.object_storage import object_uri
from tests.integration.repo.duckdb.conftest import gcs_test_bucket, track_gcs_path

pytestmark = [pytest.mark.integration, pytest.mark.integration_gcs]


class TestDuckDBManagerGcs:
    def test_copy_to_gcs_and_read_parquet(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_storage_config,
        gcs_test_path: str,
        gcs_created_paths: list[str],
        gcs_fs,
    ):
        rel_path = f"{gcs_test_path}/sample.parquet"
        track_gcs_path(gcs_created_paths, rel_path)
        uri = object_uri(gcs_storage_config, gcs_test_bucket(), rel_path)

        duckdb_conn.execute(
            f"""
            COPY (
                SELECT 1 AS id, '2330' AS code, 580.0::DOUBLE AS close
            ) TO '{uri}' (FORMAT PARQUET, CODEC 'SNAPPY')
            """
        )

        assert gcs_fs.exists(uri)
        rows = duckdb_conn.execute(
            f"SELECT id, code, close FROM read_parquet('{uri}') ORDER BY id"
        ).fetchall()
        assert rows == [(1, "2330", 580.0)]

    def test_read_parquet_limit_zero_returns_schema(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_storage_config,
        gcs_test_path: str,
        gcs_created_paths: list[str],
    ):
        rel_path = f"{gcs_test_path}/schema.parquet"
        track_gcs_path(gcs_created_paths, rel_path)
        uri = object_uri(gcs_storage_config, gcs_test_bucket(), rel_path)

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

    def test_return_conn_reuses_pool_connection(self, duckdb_manager_gcs):
        conn = DuckDBManager.get_conn()
        DuckDBManager.return_conn(conn)

        reused = DuckDBManager.get_conn()
        try:
            assert reused is conn
        finally:
            DuckDBManager.return_conn(reused)

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
