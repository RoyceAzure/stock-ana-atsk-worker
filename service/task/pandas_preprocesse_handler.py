import gc
import logging

import pandas as pd
import psycopg2

from core.error.task_error import PermanentError
from infra.repo.data_meger.blob_parquet_meger import BlobParquetMerger
from infra.repo.pipline_model.data_sink import IDataSink
from models.task_event import EventStage, TaskEvent
from service.pipline.pandas_trade_price_pipline import get_pandas_pre_process_pipline
from service.task.handler import TaskHandler
from util.memory_log import log_mem

logger = logging.getLogger(__name__)


class PreProcessPandasTaskProcessor(TaskHandler):
    """預處理任務處理器

    Args:
        pg_conn: postgres connection
        data_sink: 由 app 組裝階段注入的儲存實作
        parquet_meger: parquet 合併器

    Warns:
        此 Process 內部使用 S3ParquetMerger 合併檔案，該模組有 ConcurrencyRisk
        最安全起見，請確保同一個 code + candle 同時只有一個實例在跑
    """

    def __init__(
        self,
        pg_conn: psycopg2.extensions.connection,
        data_sink: IDataSink[pd.DataFrame],
        parquet_meger: BlobParquetMerger,
    ):
        super().__init__(EventStage.PRE_STAGE)
        self.pg_conn = pg_conn
        self.data_sink = data_sink
        self.parquet_meger = parquet_meger

    def process(self, task_event: TaskEvent):
        """處理預處理任務

        Args:
            task_event: 要處理的任務事件

        Raises:
            ValueError: 當配置無效時拋出
            Exception: 當處理失敗時拋出
        """
        meta = task_event.source_meta_data.as_dict()
        task_id = getattr(task_event, "task_id", None)
        log_mem(
            logger,
            "task_start",
            task_id=task_id,
            code=meta.get("code"),
            candle=meta.get("candle"),
        )

        pipline = None
        df = None
        err = None
        try:
            pipline = get_pandas_pre_process_pipline(
                self.pg_conn,
                self.data_sink,
                meta,
                parquet_merger=self.parquet_meger,
            )
            df, err = pipline.run()
            log_mem(
                logger,
                "task_end",
                df,
                task_id=task_id,
                code=meta.get("code"),
                candle=meta.get("candle"),
                err=err,
            )
        finally:
            if df is not None:
                log_mem(
                    logger,
                    "task_release_df",
                    df,
                    task_id=task_id,
                    code=meta.get("code"),
                    candle=meta.get("candle"),
                )
            df = None
            pipline = None
            gc.collect()
            log_mem(
                logger,
                "task_end_after_gc",
                task_id=task_id,
                code=meta.get("code"),
                candle=meta.get("candle"),
                err=err,
            )

        if err is not None:
            raise PermanentError(err)
