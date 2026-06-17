from core.error.task_error import PermanentError
import duckdb
import psycopg2
from models.task_event import EventStage, TaskEvent
from service.pipline.pandas_trade_price_pipline import get_pandas_pre_process_pipline
from infra.repo.data_meger.blob_parquet_meger import BlobParquetMerger
from models.pipline_model.pipline_params import SinkParams
from service.task.handler import TaskHandler

class PreProcessPandasTaskProcessor(TaskHandler):
    """預處理任務處理器
        Args:
            pg_conn: postgres connection
            duckdb_conn: duckdb connection
            config: 配置管理器

        Warns:
            此Process內部使用S3ParquetMerger合併檔案，該模組有ConcurrencyRisk
            最安全起見，請確保同一個code + candle 同時只有一個實例在跑
    
    """
    def __init__(self, pg_conn: psycopg2.extensions.connection, duckdb_conn: duckdb.DuckDBPyConnection, parquet_meger: BlobParquetMerger):
        super().__init__(EventStage.PRE_STAGE)
        self.pg_conn = pg_conn
        self.duckdb_conn = duckdb_conn
        self.parquet_meger = parquet_meger

    def process(self, task_event: TaskEvent):
        """處理預處理任務
        
        Args:
            task_event: 要處理的任務事件
            
        Raises:
            ValueError: 當配置無效時拋出
            Exception: 當處理失敗時拋出
        """
        # 獲取存儲配置
        sink_params = self._get_sink_params(task_event)
        
        pipline = get_pandas_pre_process_pipline(
            self.pg_conn,
            sink_params,
            task_event.source_meta_data.as_dict(),
            self.duckdb_conn,
            parquet_merger=self.parquet_meger,
        )
        
        _, err = pipline.run()
        if err is not None:
            raise PermanentError(err)

    
    def _get_sink_params(self, task_event: TaskEvent) -> SinkParams:
        """創建存儲參數
        
        Args:
            sink_config: 存儲配置
            
        Returns:
            SinkParams: 存儲參數
        """
        if task_event.sink_params is None:
            raise PermanentError("sink params is not provided")
        return task_event.sink_params
