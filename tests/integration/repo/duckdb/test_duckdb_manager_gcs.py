"""DuckDBManager 連線池整合測試（使用 GCS 設定初始化）。"""

import duckdb
import pytest

from infra.repo.duckdb_manager import DuckDBManager

pytestmark = [pytest.mark.integration, pytest.mark.integration_gcs]


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
