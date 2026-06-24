"""pandas trade_price pipeline 整合測試：mock SQLLoader，實際寫入 GCS parquet。

前置條件（.env 或環境變數）：
- GCS_HMAC_ACCESS_KEY / GCS_HMAC_SECRET_KEY
- GCS_TEST_BUCKET（可選，預設見 tests/integration/repo/duckdb/conftest.py）
"""

import duckdb
import pytest

from infra.repo.pipline_model.trade_price_sink_factory import (
    create_trade_price_parquet_sink,
)
from service.pipline.pandas_trade_price_pipline import get_pandas_pre_process_pipline
from tests.integration.repo.duckdb.conftest import gcs_test_bucket, track_gcs_path
from tests.integration.service.pipline.trade_price_factory import (
    TEST_CANDLE_DAILY,
    TEST_CANDLE_WEEKLY,
    TEST_CODE_A,
    TEST_CODE_B,
    TEST_MERGE_CODE,
    expected_merged_parquet_rows,
    seed_stale_parquet_partition,
)

pytestmark = [pytest.mark.integration, pytest.mark.integration_gcs]


def _cleanup_dataset_glob(gcs_fs, bucket: str, glob_pattern: str) -> None:
    seen = set()
    for path in gcs_fs.glob(f"{bucket}/{glob_pattern}"):
        folder = path.split("/part-")[0] if "/part-" in path else path
        rel = folder[len(f"{bucket}/") :] if folder.startswith(f"{bucket}/") else folder
        rel = rel.rstrip("/")
        if rel in seen:
            continue
        seen.add(rel)
        try:
            gcs_fs.rm(f"{bucket}/{rel}", recursive=True)
        except Exception:
            pass


def _track_pipeline_outputs(gcs_fs, gcs_created_paths: list[str], bucket: str) -> None:
    for path in gcs_fs.glob(f"{bucket}/T2*"):
        rel = path[len(f"{bucket}/") :] if path.startswith(f"{bucket}/") else path
        track_gcs_path(gcs_created_paths, rel)


def _track_merge_test_outputs(gcs_fs, gcs_created_paths: list[str], bucket: str) -> None:
    for path in gcs_fs.glob(f"{bucket}/{TEST_MERGE_CODE}*"):
        rel = path[len(f"{bucket}/") :] if path.startswith(f"{bucket}/") else path
        track_gcs_path(gcs_created_paths, rel)


def _unique_dataset_folders(gcs_fs, bucket: str, glob_pattern: str) -> set[str]:
    folders: set[str] = set()
    for path in gcs_fs.glob(f"{bucket}/{glob_pattern}"):
        if "/part-" in path:
            path = path.split("/part-")[0]
        rel = path[len(f"{bucket}/") :] if path.startswith(f"{bucket}/") else path
        folders.add(rel.rstrip("/"))
    return folders


class TestPandasTradePricePipelineGcs:
    def test_pipeline_writes_parquet_to_gcs(
        self,
        mock_sql_loader,
        mocker,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_duckdb_config,
        gcs_storage_config,
        gcs_fs,
        gcs_created_paths: list[str],
    ):
        bucket = gcs_test_bucket()
        data_sink = create_trade_price_parquet_sink(
            bucket, gcs_storage_config, duckdb_conn
        )

        pipeline = get_pandas_pre_process_pipline(
            pg_conn=mocker.Mock(),
            data_sink=data_sink,
            query_params={"code": TEST_CODE_A},
        )

        df, err = pipeline.run()
        assert err is None, err
        assert df is not None
        assert not df.empty

        _track_pipeline_outputs(gcs_fs, gcs_created_paths, bucket)

        for code, candle in (
            (TEST_CODE_A, TEST_CANDLE_DAILY),
            (TEST_CODE_B, TEST_CANDLE_WEEKLY),
        ):
            matches = gcs_fs.glob(f"{bucket}/{code}_{candle}_*")
            assert matches, f"找不到輸出目錄: {code}_{candle}_*"

            parquet_matches = gcs_fs.glob(
                f"{bucket}/{code}_{candle}_*/part-*.parquet"
            )
            assert parquet_matches, f"找不到 parquet: {code}_{candle}_*/part-*.parquet"

            success_matches = gcs_fs.glob(f"{bucket}/{code}_{candle}_*/_SUCCESS")
            assert success_matches, f"找不到 _SUCCESS: {code}_{candle}_*/_SUCCESS"

            parquet_key = parquet_matches[0][len(f"{bucket}/") :]
            duck_uri = gcs_duckdb_config.object_uri(bucket, parquet_key)
            rows = duckdb_conn.execute(
                f"""
                SELECT code, candle, direction
                FROM read_parquet('{duck_uri}')
                ORDER BY trade_time
                """
            ).fetchall()
            assert rows
            assert all(row[0] == code and row[1] == candle for row in rows)
            assert all(row[2] in (1, -1) for row in rows)

    def test_pipeline_merges_parquet_after_sink(
        self,
        mock_sql_loader_merge_only,
        mocker,
        duckdb_conn: duckdb.DuckDBPyConnection,
        gcs_duckdb_config,
        gcs_storage_config,
        gcs_fs,
        gcs_created_paths: list[str],
        parquet_merger,
    ):
        bucket = gcs_test_bucket()
        _cleanup_dataset_glob(
            gcs_fs, bucket, f"{TEST_MERGE_CODE}_{TEST_CANDLE_DAILY}_*"
        )
        seed_stale_parquet_partition(
            duckdb_conn, gcs_duckdb_config, bucket, gcs_created_paths
        )
        assert _unique_dataset_folders(
            gcs_fs, bucket, f"{TEST_MERGE_CODE}_{TEST_CANDLE_DAILY}_*"
        ) == {f"{TEST_MERGE_CODE}_{TEST_CANDLE_DAILY}_2024-01-01_2024-01-01.parquet"}

        data_sink = create_trade_price_parquet_sink(
            bucket, gcs_storage_config, duckdb_conn
        )

        pipeline = get_pandas_pre_process_pipline(
            pg_conn=mocker.Mock(),
            data_sink=data_sink,
            query_params={"code": TEST_MERGE_CODE},
            parquet_merger=parquet_merger,
        )

        df, err = pipeline.run()
        assert err is None, err
        assert df is not None

        _track_merge_test_outputs(gcs_fs, gcs_created_paths, bucket)

        merged_folders = _unique_dataset_folders(
            gcs_fs, bucket, f"{TEST_MERGE_CODE}_{TEST_CANDLE_DAILY}_*"
        )
        expected_folder = (
            f"{TEST_MERGE_CODE}_{TEST_CANDLE_DAILY}_2024-01-01_2024-01-03.parquet"
        )
        stale_folder = (
            f"{TEST_MERGE_CODE}_{TEST_CANDLE_DAILY}_2024-01-01_2024-01-01.parquet"
        )
        sink_folder = (
            f"{TEST_MERGE_CODE}_{TEST_CANDLE_DAILY}_2024-01-02_2024-01-03.parquet"
        )
        assert merged_folders == {expected_folder}
        assert stale_folder not in merged_folders
        assert sink_folder not in merged_folders

        merged_key = f"{next(iter(merged_folders))}/part-00000.snappy.parquet"
        duck_uri = gcs_duckdb_config.object_uri(bucket, merged_key)
        merged_rows = duckdb_conn.execute(
            f"""
            SELECT id, code, candle, trade_time::DATE, trade_time_date::DATE
            FROM read_parquet('{duck_uri}')
            ORDER BY trade_time
            """
        ).fetchall()
        assert len(merged_rows) == 3
        assert [(row[0], row[3]) for row in merged_rows] == expected_merged_parquet_rows()
        assert all(row[1] == TEST_MERGE_CODE and row[2] == TEST_CANDLE_DAILY for row in merged_rows)

        min_date, max_date = duckdb_conn.execute(
            f"""
            SELECT MIN(trade_time_date)::DATE, MAX(trade_time_date)::DATE
            FROM read_parquet('{duck_uri}')
            """
        ).fetchone()
        assert min_date == expected_merged_parquet_rows()[0][1]
        assert max_date == expected_merged_parquet_rows()[-1][1]
