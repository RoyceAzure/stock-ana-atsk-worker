import duckdb

from infra.repo.duckdb.config import strip_uri_scheme
from infra.repo.object_storage import ObjectStorageConfig, StorageBackend
from infra.repo.pipline_model.pandas_trade_price_datasink import (
    PandasTradePriceObjectStorageParquetSink,
)
from models.pipline_model.pipline_params import SinkLocationType, SinkParams


def _storage_backend_to_sink_location(backend: StorageBackend) -> SinkLocationType:
    mapping = {
        StorageBackend.GCS: SinkLocationType.GCS,
        StorageBackend.S3: SinkLocationType.S3,
        StorageBackend.MINIO: SinkLocationType.MINIO,
    }
    try:
        return mapping[backend]
    except KeyError as exc:
        raise ValueError(f"Unsupported storage backend for trade price sink: {backend}") from exc


def create_trade_price_parquet_sink(
    bucket_base_path: str,
    storage_config: ObjectStorageConfig,
    duckdb_conn: duckdb.DuckDBPyConnection,
) -> PandasTradePriceObjectStorageParquetSink:
    """於 app 組裝階段建立 trade_price parquet sink。"""
    sink_params = SinkParams(
        location=_storage_backend_to_sink_location(storage_config.backend),
        path=strip_uri_scheme(bucket_base_path),
        storage_config=storage_config,
    )
    return PandasTradePriceObjectStorageParquetSink(
        sink_params, duckdb_conn=duckdb_conn
    )
