import psycopg2
import pandas as pd
from typing import Optional

from infra.repo.data_loaders.sql_loader import SQLLoader
from infra.repo.data_meger.blob_parquet_meger import BlobParquetMerger
from infra.repo.pipline_model.data_sink import IDataSink
from service.pipline.pandas_trade_price_dataset import PandasTradePriceDataSet
from service.pipline.post_actions import make_batch_merge_action
from service.pipline.pipline_service import PipelineStage, Pipline
from technicals import pattern


def get_pandas_pre_process_pipline(
    pg_conn: psycopg2.extensions.connection,
    data_sink: IDataSink[pd.DataFrame],
    query_params: dict,
    parquet_merger: Optional[BlobParquetMerger] = None,
) -> Pipline:
    """
    建立 trade_price 預處理 pipeline；儲存目的地由外部注入的 data_sink 決定。
    """
    dataLoader = SQLLoader(pg_conn)

    source_data_set = PandasTradePriceDataSet(dataLoader, **query_params)

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
    trade_price_pipline.set_data_sink(data_sink)

    if parquet_merger is not None:
        trade_price_pipline.add_post_sink_action(
            make_batch_merge_action(parquet_merger)
        )

    return trade_price_pipline
