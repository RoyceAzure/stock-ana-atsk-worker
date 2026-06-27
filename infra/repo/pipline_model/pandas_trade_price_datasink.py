import logging
from typing import Optional, Tuple

import duckdb
import pandas as pd

from core.file_lock.file_lock_manager import FileLocker
from infra.repo.object_storage import to_duckdb_httpfs_uri
from models.pipline_model.pandas_trade_price_schema import validate_pandas_trade_price_output
from models.pipline_model.pipline_params import SinkParams
from infra.repo.pipline_model.data_sink import IDataSink

logger = logging.getLogger(__name__)


def _format_date(val) -> str:
    """將 date/datetime 轉為 YYYY-MM-DD 字串"""
    if val is None or (hasattr(val, "__iter__") and not isinstance(val, str) and pd.isna(val)):
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]


class PandasTradePriceObjectStorageParquetSink(IDataSink[pd.DataFrame]):
    """pandas 版本：將 trade price 依 code/candle/start_date/end_date 分組寫入物件儲存 parquet。"""

    def __init__(
        self,
        args: SinkParams,
        expected_schema=None,
        duckdb_conn: duckdb.DuckDBPyConnection = None,
    ):
        super().__init__(args=args)
        self.expected_schema = expected_schema
        self.duckdb_conn = duckdb_conn

    def _save(self) -> Optional[str]:
        if self.parms is None or self.parms.path is None:
            return "Missing saved path"

        storage_config = self.parms.resolved_storage_config()
        df = self._df_selelct
        required_cols = ["code", "candle", "start_date", "end_date"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return f"Missing columns for grouping: {missing}"

        bucket = self.parms.path
        groups = df[required_cols].drop_duplicates()
        with self.duckdb_conn.cursor() as con:
            try:
                for _, row in groups.iterrows():
                    code, candle, start_date, end_date = (
                        row["code"],
                        row["candle"],
                        row["start_date"],
                        row["end_date"],
                    )
                    start_str = _format_date(start_date)
                    end_str = _format_date(end_date)
                    folder_name = f"{code}_{candle}_{start_str}_{end_str}.parquet"
                    parquet_key = f"{folder_name}/part-00000.snappy.parquet"
                    duckdb_parquet_path = to_duckdb_httpfs_uri(
                        storage_config, bucket, parquet_key
                    )
                    success_key = f"{folder_name}/_SUCCESS"
                    lock_key = to_duckdb_httpfs_uri(storage_config, bucket, folder_name)

                    df_filtered = df[(df["code"] == code) & (df["candle"] == candle)]
                    logger.info(
                        f"save data to {storage_config.backend.value}: "
                        f"{code}, {candle}, {start_date}, {end_date}"
                    )
                    with FileLocker.get_lock(lock_key):
                        con.register("_sink_df", df_filtered)
                        con.execute(
                            f"COPY (SELECT * FROM _sink_df) TO '{duckdb_parquet_path}' "
                            f"(FORMAT PARQUET, CODEC 'SNAPPY')"
                        )
                        con.unregister("_sink_df")
                        success_path = to_duckdb_httpfs_uri(
                            storage_config, bucket, success_key
                        )
                        con.execute(
                            f"COPY (SELECT 1) TO '{success_path}' "
                            f"(FORMAT CSV, HEADER false)"
                        )
                    logger.info(
                        f"save data to {storage_config.backend.value} success: "
                        f"{code}, {candle}, {start_date}, {end_date}"
                    )
            except Exception as e:
                error_type = type(e).__name__
                error_msg = f"儲存 parquet 失敗: [{error_type}] {str(e)}"
                logger.error(
                    f"save data failed: {code}, {candle}, {start_date}, {end_date}, {error_msg}"
                )
                return error_msg
            finally:
                logger.info("duck db shrink memory start")
                try:
                    con.execute("PRAGMA shrink_memory();")
                except Exception:
                    pass
                logger.info("duck db shrink memory end")
        return None

    def _validate(self, df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            validate_pandas_trade_price_output(df)
            return df, None
        except Exception as e:
            return None, str(e)

