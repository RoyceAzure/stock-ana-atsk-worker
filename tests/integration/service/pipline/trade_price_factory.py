import pandas as pd
from datetime import date
from typing import List, Tuple

from models.pipline_model.pandas_trade_price_schema import PandasTradePriceInputSchema
from technicals import pattern

TEST_CODE_A = "T2330"
TEST_CODE_B = "T2317"
TEST_MERGE_CODE = "T2330M"
TEST_CANDLE_DAILY = "1d"
TEST_CANDLE_WEEKLY = "1w"


def _run_preprocess_stages(df: pd.DataFrame) -> pd.DataFrame:
    df = pattern.remove_columns(df)
    df = pattern.apply_candle_props(df)
    df = pattern.clean_data(df)
    return pattern.trade_price_post_process(df)


def build_trade_price_input_df() -> pd.DataFrame:
    """建立符合 PandasTradePriceInputSchema 的假資料。"""
    base_time = pd.Timestamp("2024-01-02 09:00:00")
    rows = [
        {
            "id": 1,
            "code": TEST_CODE_A,
            "open": 100.0,
            "close": 101.0,
            "high": 102.0,
            "low": 99.0,
            "trade_time": base_time,
            "candle": TEST_CANDLE_DAILY,
            "volume": 1000,
            "volume_weight": 1000,
            "updated_at": base_time,
            "created_at": base_time,
        },
        {
            "id": 2,
            "code": TEST_CODE_A,
            "open": 101.0,
            "close": 103.0,
            "high": 104.0,
            "low": 100.5,
            "trade_time": base_time + pd.Timedelta(days=1),
            "candle": TEST_CANDLE_DAILY,
            "volume": 1100,
            "volume_weight": 1100,
            "updated_at": base_time,
            "created_at": base_time,
        },
        {
            "id": 3,
            "code": TEST_CODE_B,
            "open": 50.0,
            "close": 51.0,
            "high": 52.0,
            "low": 49.0,
            "trade_time": base_time + pd.Timedelta(days=2),
            "candle": TEST_CANDLE_WEEKLY,
            "volume": 800,
            "volume_weight": 800,
            "updated_at": base_time,
            "created_at": base_time,
        },
    ]
    df = pd.DataFrame(rows)
    PandasTradePriceInputSchema.validate(df, lazy=True)
    return df


def build_trade_price_merge_input_df() -> pd.DataFrame:
    """僅含 TEST_MERGE_CODE 的假資料，供 merge 整合測試使用。"""
    base_time = pd.Timestamp("2024-01-02 09:00:00")
    rows = [
        {
            "id": 1,
            "code": TEST_MERGE_CODE,
            "open": 100.0,
            "close": 101.0,
            "high": 102.0,
            "low": 99.0,
            "trade_time": base_time,
            "candle": TEST_CANDLE_DAILY,
            "volume": 1000,
            "volume_weight": 1000,
            "updated_at": base_time,
            "created_at": base_time,
        },
        {
            "id": 2,
            "code": TEST_MERGE_CODE,
            "open": 101.0,
            "close": 103.0,
            "high": 104.0,
            "low": 100.5,
            "trade_time": base_time + pd.Timedelta(days=1),
            "candle": TEST_CANDLE_DAILY,
            "volume": 1100,
            "volume_weight": 1100,
            "updated_at": base_time,
            "created_at": base_time,
        },
    ]
    df = pd.DataFrame(rows)
    PandasTradePriceInputSchema.validate(df, lazy=True)
    return df


def seed_stale_parquet_partition(
    duckdb_conn,
    gcs_duckdb_config,
    bucket: str,
    gcs_created_paths: list[str],
) -> str:
    """
    寫入舊的 T2330/1d 分割區，供 merge 整合測試使用。
    回傳 dataset 資料夾名稱（不含 bucket）。
    """
    stale_time = pd.Timestamp("2024-01-01 09:00:00")
    row_df = build_trade_price_merge_input_df().iloc[[0]].copy()
    row_df["id"] = 99
    row_df["trade_time"] = stale_time
    processed = _run_preprocess_stages(row_df)

    folder_name = f"{TEST_MERGE_CODE}_{TEST_CANDLE_DAILY}_2024-01-01_2024-01-01.parquet"
    parquet_key = f"{folder_name}/part-00000.snappy.parquet"
    duck_uri = gcs_duckdb_config.object_uri(bucket, parquet_key)

    with duckdb_conn.cursor() as con:
        con.register("_seed_df", processed)
        con.execute(
            f"COPY (SELECT * FROM _seed_df) TO '{duck_uri}' "
            f"(FORMAT PARQUET, CODEC 'SNAPPY')"
        )
        con.unregister("_seed_df")

    gcs_created_paths.append(folder_name)
    return folder_name


def expected_merged_parquet_rows() -> List[Tuple[int, date]]:
    """
    合併後 parquet 預期內容（依 trade_time 排序）。
    id=99 來自 seed 舊分割，id=1/2 來自本次 pipeline sink。
    """
    return [
        (99, date(2024, 1, 1)),
        (1, date(2024, 1, 2)),
        (2, date(2024, 1, 3)),
    ]
