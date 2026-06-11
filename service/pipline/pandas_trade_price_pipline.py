import duckdb
import psycopg2
import pandas as pd

from infra.repo.data_loaders.sql_loader import SQLLoader
from infra.repo.pipline_model.pandas_trade_price_datasink import (
    PandasTradePriceObjectStorageParquetSink,
)
from models.pipline_model.data_sink import SinkLocationType, SinkParams
from models.pipline_model.pandas_trade_price_dataset import PandasTradePriceDataSet
from service.pipline.pipline_service import PipelineStage, Pipline
from technicals import pattern


_OBJECT_STORAGE_LOCATIONS = {
    SinkLocationType.MINIO,
    SinkLocationType.S3,
    SinkLocationType.GCS,
}


def get_pandas_pre_process_pipline(
    pg_conn: psycopg2.extensions.connection,
    sink_parms: SinkParams,
    query_params: dict,
    duckdb_conn: duckdb.DuckDBPyConnection,
) -> Pipline:
    """
        get default pre process pipline of trade_price table
        Args:
            query for trade price data set
            duckdb_conn: duckdb connection
    """
    dataLoader = SQLLoader(pg_conn)

    source_data_set = PandasTradePriceDataSet(dataLoader, None, **query_params)

    trade_price_pipline = Pipline[pd.DataFrame]()
    remove_columns_stage = PipelineStage[pd.DataFrame](pattern.remove_columns)
    apply_candle_stage = PipelineStage[pd.DataFrame](pattern.apply_candle_props)
    clean_data_stage = PipelineStage[pd.DataFrame](pattern.clean_data)
    post_process_stage = PipelineStage[pd.DataFrame](pattern.trade_price_post_process)

    trade_price_pipline.set_data_set(source_data_set)
    trade_price_pipline.add_stage(remove_columns_stage)
    trade_price_pipline.add_stage(apply_candle_stage)
    trade_price_pipline.add_stage(clean_data_stage)
    trade_price_pipline.add_stage(post_process_stage)

    if sink_parms.location in _OBJECT_STORAGE_LOCATIONS:
        data_sink = PandasTradePriceObjectStorageParquetSink(
            sink_parms, duckdb_conn=duckdb_conn
        )
    else:
        raise ValueError("pipline data sink 沒有設定")

    trade_price_pipline.set_data_sink(data_sink)

    return trade_price_pipline
