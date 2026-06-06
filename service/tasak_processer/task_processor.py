import duckdb
import psycopg2
from models.task_event import TaskEvent
from models.task_processer import TaskProcessor
from models.task_result import TaskResult, TaskResultException
from config.consumer_config import ConsumerConfig, SinkConfig
from internal.pipline.pandas_trade_price_pipline import get_pandas_pre_process_pipline
from internal.repository.data_meger.s3_parquet_meger import S3ParquetMerger
from domain.model.pipline_model.data_sink import SinkParams
from internal.pkg.util import util
from pkg.rabbitmq.base import ConsumerResult

class PreProcessPandasTaskProcessor(TaskProcessor):
    """預處理任務處理器
        Args:
            pg_conn: postgres connection
            duckdb_conn: duckdb connection
            config: 配置管理器

        Warns:
            此Process內部使用S3ParquetMerger合併檔案，該模組有ConcurrencyRisk
            最安全起見，請確保同一個code + candle 同時只有一個實例在跑
    
    """
    def __init__(self, pg_conn: psycopg2.extensions.connection, duckdb_conn: duckdb.DuckDBPyConnection, config: ConsumerConfig, parquet_meger: S3ParquetMerger):
        self.pg_conn = pg_conn
        self.duckdb_conn = duckdb_conn
        self.config = config
        self.parquet_meger = parquet_meger

    def process(self, task_event: TaskEvent, taskId: str = "default") -> TaskResult:
        """處理預處理任務
        
        Args:
            task_event: 要處理的任務事件
            
        Raises:
            ValueError: 當配置無效時拋出
            Exception: 當處理失敗時拋出
        """
        # 獲取存儲配置
        sink_config = self._get_sink_config(task_event)
        sink_params = self._create_sink_params(sink_config)
        
        #判斷code是否為user code 群組
        #若code為":" 則表示處理當日所有新資料
        isProcessNewData = ":" in task_event.source_meta_data.code

        temp_map = {}
        if isProcessNewData:
            #特殊的propress處理流程
            #撈取當天所有新增資料
            start_time, end_time = util.get_utc_day_range()
            start_time = start_time.strftime('%Y-%m-%d')
            end_time = end_time.strftime('%Y-%m-%d')
            task_event.source_meta_data.code = "*"
            task_event.source_meta_data.start_time = start_time
            task_event.source_meta_data.end_time = end_time
            temp_map["filter_time_col"] = "created_at"
        else:
            temp_map["filter_time_col"] = "trade_time"

        filter_map = task_event.source_meta_data.as_dict() | temp_map
        
        pipline = get_pandas_pre_process_pipline(
            self.pg_conn,
            sink_params,
            filter_map,
            self.duckdb_conn
        )
        
        _, err = pipline.run()
        if err is not None:
            raise TaskResultException(TaskResult(
                id=task_event.id,
                is_successed=ConsumerResult.FAILED,
                message=err,
                extras=None
            ))

        #warning: 此處使用S3ParquetMerger合併檔案，該模組有ConcurrencyRisk
        self.parquet_meger.merge_all_available_data()

        return TaskResult(
            id=task_event.id,
            is_successed=ConsumerResult.SUCCESSED,
            message="",
            extras=None
        )
                
    def _get_sink_config(self, task_event: TaskEvent) -> SinkConfig:
        """獲取存儲配置
        
        Args:
            task_event: 任務事件
            
        Returns:
            SinkConfig: 存儲配置
            
        Raises:
            ValueError: 當存儲位置無效時拋出
        """
        location = task_event.saver_params.saver_name
        if not location:
            raise ValueError("sink location not provided")
        return self.config.get_sink_config(location)
    
    def _create_sink_params(self, sink_config: SinkConfig) -> SinkParams:
        """創建存儲參數
        
        Args:
            sink_config: 存儲配置
            
        Returns:
            SinkParams: 存儲參數
        """
        return SinkParams(
            location=sink_config.location,
            path=sink_config.path,
            minio_config=sink_config.minio_config
        )
