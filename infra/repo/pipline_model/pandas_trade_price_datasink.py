import logging
from infra.repo.pipline_model.data_sink import IDataSink, SinkParams
from typing import Tuple, Optional
import pandas as pd
import duckdb
import s3fs
from core.file_lock.file_lock_manager import FileLocker
from models.pipline_model.pandas_trade_price_schema import validate_pandas_trade_price_output
from models.pipline_model.pipline_params import SinkParams


def _create_s3fs(minio_config) -> s3fs.S3FileSystem:
    """從 MinioConfig 建立 s3fs，用於寫入 _SUCCESS 等檔案"""
    return s3fs.S3FileSystem(
        key=minio_config.access_key,
        secret=minio_config.secret_key,
        client_kwargs={"region_name": minio_config.region},
    )

def _format_date(val) -> str:
    """將 date/datetime 轉為 YYYY-MM-DD 字串"""
    if val is None or (hasattr(val, "__iter__") and not isinstance(val, str) and pd.isna(val)):
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]

class PandasTradePriceMinioParquetSink(IDataSink[pd.DataFrame]):
    """pandas 版本：將 trade price 依 code/candle/start_date/end_date 分組寫入 S3/MinIO parquet。
    """
    def __init__(self, args: SinkParams, expected_schema=None, duckdb_conn: duckdb.DuckDBPyConnection = None):
        super().__init__(args=args, expected_schema=expected_schema)
        self.duckdb_conn = duckdb_conn
        self.logger = logging.getLogger(__name__)

    def _save(self) -> Optional[str]:
        if self.parms is None or self.parms.path is None:
            return "Missing saved path"
        if self.parms.minio_config is None:
            return "Missing minio_config"

        df = self._df_selelct
        required_cols = ["code", "candle", "start_date", "end_date"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return f"Missing columns for grouping: {missing}"

        bucket = self.parms.path
        groups = df[required_cols].drop_duplicates()
        fs = _create_s3fs(self.parms.minio_config)
        with self.duckdb_conn.cursor() as con:
            try:
                    for _, row in groups.iterrows():
                        code, candle, start_date, end_date = (
                            row["code"], row["candle"], row["start_date"], row["end_date"]
                        )
                        start_str = _format_date(start_date)
                        end_str = _format_date(end_date)
                        folder_name = f"{code}_{candle}_{start_str}_{end_str}.parquet"
                        parquet_path = f"s3://{bucket}/{folder_name}/part-00000.snappy.parquet"
                        success_path = f"s3://{bucket}/{folder_name}/_SUCCESS"
                        lock_key = f"s3://{bucket}/{folder_name}"

                        df_filtered = df[(df["code"] == code) & (df["candle"] == candle)]
                        self.logger.info(f"save data to minio: {code}, {candle}, {start_date}, {end_date}")
                        with FileLocker.get_lock(lock_key):
                            con.register("_sink_df", df_filtered)
                            con.execute(
                                f"COPY (SELECT * FROM _sink_df) TO '{parquet_path}' "
                                f"(FORMAT PARQUET, CODEC 'SNAPPY')"
                            )
                            con.unregister("_sink_df")
                            with fs.open(success_path, "wb") as f:
                                pass
                        self.logger.info(f"save data to minio success: {code}, {candle}, {start_date}, {end_date}")
            except Exception as e:
                error_type = type(e).__name__ 
                error_msg = f"儲存 minio parquet 失敗: [{error_type}] {str(e)}"
                self.logger.error(f"save data to minio failed: {code}, {candle}, {start_date}, {end_date}, {error_msg}")
                return error_msg
            finally:
                self.logger.info("duck db shrink memory start")
                try:
                    con.execute("PRAGMA shrink_memory();")
                except:
                    pass
                self.logger.info("duck db shrink memory end")
        return None

    def _validate(self, df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            validate_pandas_trade_price_output(df)
            return df, None
        except Exception as e:
            return None, str(e)