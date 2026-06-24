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


class TestDuckDBGcsMergerPathInterop:
    """驗證 BlobParquetMerger 路徑行為：DuckDB gs:// 寫入後 s3fs 能否存取、move。"""

    def test_duckdb_write_visible_to_s3fs_plain_path(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_duckdb_config,
        gcs_test_path: str,
        gcs_created_paths: list[str],
        gcs_fs,
    ):
        """DuckDB httpfs 與 s3fs 可見性一致；exists / glob 可找到 part 與 _SUCCESS。"""
        bucket = gcs_test_bucket()
        base_path = f"{bucket}/{gcs_test_path}"
        track_gcs_path(gcs_created_paths, gcs_test_path)

        temp_path = f"{base_path}/TEMP_7610_d1_2025-01-01_2025-01-31.parquet"
        parquet_key = f"{temp_path}/part-00000.snappy.parquet"
        success_key = f"{temp_path}/_SUCCESS"

        parquet_uri = gcs_duckdb_config.to_uri(parquet_key)
        success_uri = gcs_duckdb_config.to_uri(success_key)

        duckdb_conn.execute(
            f"""
            COPY (
                SELECT 1 AS id, '7610' AS code, 100.0::DOUBLE AS close
            ) TO '{parquet_uri}' (FORMAT PARQUET, CODEC 'SNAPPY')
            """
        )
        duckdb_conn.execute(
            f"COPY (SELECT 1) TO '{success_uri}' (FORMAT CSV, HEADER false)"
        )

        assert gcs_fs.exists(parquet_key)
        assert gcs_fs.exists(success_key)
        assert gcs_fs.isdir(temp_path)
        globbed = gcs_fs.glob(f"{temp_path}/*")
        assert parquet_key in globbed

    def test_s3fs_recursive_move_fails_on_parquet_dataset_folder(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_duckdb_config,
        gcs_test_path: str,
        gcs_created_paths: list[str],
        gcs_fs,
    ):
        """重現 merger 的 move 失敗：虛擬資料夾名稱以 .parquet 結尾時 s3fs move 會 NoSuchKey。"""
        bucket = gcs_test_bucket()
        base_path = f"{bucket}/{gcs_test_path}"
        track_gcs_path(gcs_created_paths, gcs_test_path)

        temp_path = f"{base_path}/TEMP_7610_d1_2025-01-01_2025-01-31.parquet"
        final_path = f"{base_path}/7610_d1_2025-01-01_2025-01-31.parquet"
        parquet_uri = gcs_duckdb_config.to_uri(
            f"{temp_path}/part-00000.snappy.parquet"
        )

        duckdb_conn.execute(
            f"""
            COPY (
                SELECT 1 AS id, '7610' AS code, 100.0::DOUBLE AS close
            ) TO '{parquet_uri}' (FORMAT PARQUET, CODEC 'SNAPPY')
            """
        )

        with pytest.raises((FileNotFoundError, OSError)):
            gcs_fs.move(temp_path, final_path, recursive=True)

    def test_s3fs_cp_per_file_workaround_for_dataset_folder(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_duckdb_config,
        gcs_test_path: str,
        gcs_created_paths: list[str],
        gcs_fs,
    ):
        """逐檔 cp + rm 可替代 move，作為 merger 修復方向驗證。"""
        bucket = gcs_test_bucket()
        base_path = f"{bucket}/{gcs_test_path}"
        track_gcs_path(gcs_created_paths, gcs_test_path)

        temp_path = f"{base_path}/TEMP_7610_d1_2025-01-01_2025-01-31.parquet"
        final_path = f"{base_path}/7610_d1_2025-01-01_2025-01-31.parquet"
        parquet_uri = gcs_duckdb_config.to_uri(
            f"{temp_path}/part-00000.snappy.parquet"
        )
        success_uri = gcs_duckdb_config.to_uri(f"{temp_path}/_SUCCESS")

        duckdb_conn.execute(
            f"""
            COPY (
                SELECT 1 AS id, '7610' AS code, 100.0::DOUBLE AS close
            ) TO '{parquet_uri}' (FORMAT PARQUET, CODEC 'SNAPPY')
            """
        )
        duckdb_conn.execute(
            f"COPY (SELECT 1) TO '{success_uri}' (FORMAT CSV, HEADER false)"
        )

        for src in gcs_fs.glob(f"{temp_path}/*"):
            name = src.rsplit("/", 1)[-1]
            gcs_fs.cp(src, f"{final_path}/{name}")

        gcs_fs.rm(temp_path, recursive=True)

        assert gcs_fs.exists(f"{final_path}/part-00000.snappy.parquet")
        assert gcs_fs.exists(f"{final_path}/_SUCCESS")
        assert not gcs_fs.exists(f"{temp_path}/part-00000.snappy.parquet")
