import duckdb

from infra.repo.duckdb.config import strip_uri_scheme
from infra.repo.object_storage import ObjectStorageConfig, StorageBackend
from infra.repo.pipline_model.pandas_trade_price_datasink import (
    PandasTradePriceObjectStorageParquetSink,
)
from models.pipline_model.pipline_params import SinkLocationType, SinkParams


def create_trade_price_parquet_sink(
    bucket_base_path: str,
    storage_config: ObjectStorageConfig,
    duckdb_conn: duckdb.DuckDBPyConnection,
) -> PandasTradePriceObjectStorageParquetSink:
    """於 app 組裝階段建立 trade_price parquet sink。"""
    if storage_config.backend is not StorageBackend.GCS:
        raise ValueError(f"trade price sink 目前僅支援 GCS，收到: {storage_config.backend}")

    sink_params = SinkParams(
        location=SinkLocationType.GCS,
        path=strip_uri_scheme(bucket_base_path),
        storage_config=storage_config,
    )
    return PandasTradePriceObjectStorageParquetSink(
        sink_params, duckdb_conn=duckdb_conn
    )
