from dataclasses import Field, asdict, dataclass
import datetime
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Tuple, Union
import threading
import uuid
import psycopg2
import psycopg2.extras
from psycopg2 import OperationalError
from psycopg2.extras import execute_values
from psycopg2.pool import ThreadedConnectionPool
import psycopg2.extensions
from pydantic import Field, Json
from models.basemodel import BaseModelWithConfig


@dataclass
class DBConfig:
    host : str
    database : str
    user : str
    password : str
    port : int
    sslmode: str = 'prefer'
    connect_timeout: int = 30
    
    def as_dict(self):
        return asdict(self)


def adapt_uuid(uuid):
    return psycopg2.extensions.adapt(str(uuid))

# 在模組層級註冊 UUID 適配器，確保無論如何創建連接都能使用 UUID 類型
psycopg2.extensions.register_adapter(uuid.UUID, adapt_uuid)

def conn_pg(db_config : DBConfig):
    """
    創建到 PostgreSQL 數據庫的連接。
    
    :param host: 數據庫服務器地址
    :param database: 數據庫名稱
    :param user: 用戶名
    :param password: 密碼
    :param port: 端口號，默認為 5432
    :return: 如果連接成功，返回連接對象；否則返回 None
    """
    psycopg2.extensions.register_adapter(uuid.UUID, adapt_uuid)
    try:
        conn = psycopg2.connect(
            host=db_config.host,
            database=db_config.database,
            user=db_config.user,
            password=db_config.pas,
            port=db_config.port
        )
    except OperationalError as e:
            print(f"連接PG失敗 {e}")
            return None

    return conn


@dataclass
class DBPoolConfig:
    min_conn : int
    max_conn : int

class DatabasePool:
    """PostgreSQL 線程安全數據庫連接池
    
    這個類提供了線程安全的 PostgreSQL 數據庫連接管理，確保每個線程使用獨立的數據庫連接。
    使用 ThreadedConnectionPool 實現連接池功能，並通過 threading.local() 確保線程安全。
    
    主要特點：
    - 線程安全的連接管理
    - 連接池功能減少資源消耗
    - 自動適配 UUID 類型
    - 支持連接的獲取和歸還
    
    技術細節：
    - 使用 psycopg2.extensions.register_adapter 註冊 UUID 類型適配器
    - 使用 ThreadedConnectionPool 管理數據庫連接池
    - 使用 threading.local() 確保每個線程使用獨立連接
    
    Attributes:
        pool (ThreadedConnectionPool): PostgreSQL 連接池
        _local (threading.local): 線程本地存儲，用於保存每個線程的連接
        
    Note:
        - 每個線程只能有一個活動連接
        - 必須確保使用完連接後正確歸還到連接池
        - 連接池大小由 pool_config 控制
    """
    def __init__(self, pool_config : DBPoolConfig, db_config : DBConfig):
        self.pool = None
        self._local = threading.local()
        self._lock = threading.Lock()
        psycopg2.extensions.register_adapter(uuid.UUID, adapt_uuid)
        
        self.pool = ThreadedConnectionPool(pool_config.min_conn, pool_config.max_conn, **db_config.as_dict())

        
    def get_connection(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = self.pool.getconn()
        return self._local.conn

    def return_connection(self):
        if hasattr(self._local, "conn"):
            self.pool.putconn(self._local.conn)
            del self._local.conn
            
    def close(self):
        """關閉連接池及其所有連接
        
        注意：
        - 這個方法應該在應用程序結束時調用
        - 調用後連接池將不能再使用
        - 確保所有連接都已歸還後再調用
        """
        if self.pool is not None:
            with self._lock:
                if self.pool:
                    self.pool.closeall()
                    self.pool = None

    def __del__(self):
        """析構時確保連接池被關閉"""
        self.close()
            
            
class BaseRepository:
    """資料庫操作基礎類
    
    此類提供基本的數據庫操作功能，包括查詢、執行和事務管理。
    注意：此類不負責連接的生命週期管理，連接應該由調用者管理。
    
    Attributes:
        _conn: 數據庫連接對象，由外部傳入
    """
    def __init__(self, conn: psycopg2.extensions.connection):
        self._conn = conn
        
    def commit(self):
        self._conn.commit() 

    def rollback(self):
        self._conn.rollback() 
        
    def fetch_one(self, sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """查詢單筆資料。

        Args:
            sql (str): SQL 語句
            params (tuple, optional): SQL 參數. Defaults to None.

        Returns:
            Optional[Dict[str, Any]]: 查詢結果字典，若無資料則返回 None

        Raises:
            psycopg2.Error: 資料庫操作錯誤
        """
        try:
            with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        except psycopg2.Error:
            raise

    def fetch_all(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """查詢多筆資料。

        Args:
            sql (str): SQL 語句
            params (tuple, optional): SQL 參數. Defaults to None.

        Returns:
            List[Dict[str, Any]]: 查詢結果列表，若無資料則返回空列表

        Raises:
            psycopg2.Error: 資料庫操作錯誤
        """
        try:
            with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        except psycopg2.Error:
            raise        

    def execute(self, sql: str, params) -> None:
        """執行單條 SQL"""
        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, params)
        except psycopg2.Error:
            raise 

    def execute_batch(self, sql: str, params_list: List[Union[Dict, Tuple]], page_size: int = 1000) -> int:
        """批量執行 SQL，支援 Dict 和 Tuple 格式"""
        try:
            if not params_list:
                return 0
                
            with self._conn.cursor() as cur:
                # 檢查第一個元素的類型
                first_param = params_list[0]
                if isinstance(first_param, dict):
                    values = [tuple(d.values()) for d in params_list]
                    execute_values(
                        cur,
                        sql,
                        values,
                        page_size=page_size
                    )
                else:
                    # Tuple 模式
                    execute_values(
                        cur,
                        sql,
                        params_list,
                        page_size=page_size
                    )
                    
            return len(params_list)
        except psycopg2.Error:
            raise

    def with_transaction(self):
        """事務上下文管理器"""
        class TransactionContext:
            def __init__(self, conn):
                self.conn = conn

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    self.conn.commit()
                else:
                    self.conn.rollback()

        return TransactionContext(self._conn)
        
    def __del__(self):
        if hasattr(self, '_cursor') and self._cursor:
            self._cursor.close()
            
class CandleIntervalEnum(Enum):
    D1 = "d1"

class SortOrderEnum(Enum):
    ASC ="asc"
    DESC    = "desc"

class GetTestResultsParamsSortEnum(Enum):
    NAME ="name"
    CODE = "code"
    PROFIT = "profit"
    START_TIME = "start_time"
    END_TIME = "end_time"

class GetTestResultsParams(BaseModelWithConfig):
    str_name: Optional[str]= Field(default="", description="策略名稱")
    code: Optional[str]= Field(default="", description="股票代碼")
    candle: Optional[CandleIntervalEnum]= Field(default="", description="標的時間間隔")
    sort_by: Optional[GetTestResultsParamsSortEnum]= Field(default=GetTestResultsParamsSortEnum.NAME, description="排序欄位")
    sort_order: Optional[SortOrderEnum]= Field(default=SortOrderEnum.ASC, description="排序方式")
    page : Optional[int] = Field(default=1, description="分頁頁數")
    page_size : Optional[int] = Field(default=20, description="分頁大小")


class TestResultEntity(BaseModelWithConfig):
    id: int = Field(..., description="自動遞增的主鍵，唯一識別回測結果")
    key_string: str = Field(..., description="原始的 Key 字串，用於快速查找特定回測結果")
    strategy_parms: Json[Dict[str, Any]] = Field(..., description="策略參數 JSON 區塊，包含策略的相關設定")
    tester_params: Json[Dict[str, Any]] = Field(..., description="測試器參數 JSON 區塊，包含回測測試器的相關設定")
    summary: Json[Dict[str, Any]] = Field(..., description="回測結果摘要 JSON 區塊，包含回測的總體績效指標")
    file: Json[Dict[str, Any]] = Field(..., description="檔案資訊 JSON 區塊，包含回測結果相關檔案的路徑")
    completed_at: datetime.datetime = Field(..., description="回測完成時間")
    created_at: datetime.datetime = Field(..., description="資料建立時間")
    updated_at: datetime.datetime = Field(..., description="資料最後更新時間")
    
    
class TestResultUpsertParams(BaseModelWithConfig):
    key_string: str = Field(..., description="原始的 Key 字串，用於快速查找特定回測結果")
    strategy_parms: Json[Dict[str, Any]] = Field(..., description="策略參數 JSON 區塊，包含策略的相關設定")
    tester_params: Json[Dict[str, Any]] = Field(..., description="測試器參數 JSON 區塊，包含回測測試器的相關設定")
    summary: Json[Dict[str, Any]] = Field(..., description="回測結果摘要 JSON 區塊，包含回測的總體績效指標")
    file: Json[Dict[str, Any]] = Field(..., description="檔案資訊 JSON 區塊，包含回測結果相關檔案的路徑")
    completed_at: datetime.datetime = Field(..., description="回測完成時間")
    updated_at: datetime.datetime = Field(..., description="資料最後更新時間")
    task_event_id: uuid.UUID = Field(..., description="執行此任務的task event id")


class UpdateTaskEventParams(BaseModelWithConfig):
    """
    for update task event
    """    
    id: uuid.UUID
    updated_at: Optional[datetime.datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    event_stage : Optional[str] = Field(default=None)
    error_message:  Optional[str] = Field(default=None)
    
    
    def as_dict(self):
        return self.model_dump()


            
class DatabaseRepository(BaseRepository):
    def __init__(self, conn: psycopg2.extensions.connection):
        super().__init__(conn) 
        
    def batch_insert_task_history_2_process_log(self, records: List[Dict[str, Any]], page_size: int = 1000) -> int:
        """批量插入任務歷史記錄到日誌
        
            Args:
                records (List[Dict[str, Any]]): 任務記錄列表，每個記錄包含以下字段：
                    - task_id: 任務ID
                    - action: 函數名稱
                    - module: 模組名稱
                    - args: 函數參數
                    - start_time: 開始時間
                    - end_time: 結束時間
                    - duration: 執行時長
                    - status: 執行狀態
                    - error: 錯誤信息
                    - result: 執行結果
                page_size (int, optional): 每批次插入的記錄數量. 默認值: 1000
            Returns:
                int: 成功插入的記錄數量

            Examples:
                >>> records = [{
                ...     'task_id': 'uuid',
                ...     'action': 'process_data',
                ...     'module': ''
                ...     'args': '{"data": "example"}',
                ...     'start_time': '2024-01-01 10:00:00',
                ...     'end_time': '2024-01-01 10:01:00',
                ...     'duration': '60',
                ...     'status': 'success',
                ...     'error': None,
                ...     'result': '{"status": "processed"}'
                ... }]
                >>> repo.batch_insert_task_history_2_log(records)
                1
        """
        
        try:
            sql = """
            INSERT INTO process_log (
                task_id, action, module, args, start_time,
                end_time, duration, status, error, result
            ) VALUES %s
            """
            res = self.execute_batch(sql, records, page_size)
            self.commit()
            return res
            
        except Exception as e:
            self.rollback()
            raise Exception(f"批量插入任務歷史記錄失敗: {str(e)}")
        
    def get_process_log(self, task_id : int) -> Optional[Dict[str, Any]]:
        """查詢任務歷史日誌
            Args:
                task_id (int, ai) : 任務id
            Returns:
                >>> {
                ...     'task_id': '123',
                ...     'function_name': 'process_data',
                ...     'args': '{"data": "example"}',
                ...     'start_time': '2024-01-01 10:00:00',
                ...     'end_time': '2024-01-01 10:01:00',
                ...     'duration': '60',
                ...     'status': 'success',
                ...     'error': None,
                ...     'result': '{"status": "processed"}'
                ... }
                >>> 
        """
    
        try:
            sql = "SELECT * FROM process_log WHERE task_id = %s"
            res = self.fetch_one(sql, (task_id,))
            return res
            
        except Exception as e:
            raise Exception(f"查詢任務歷史日誌失敗: {str(e)}")
        
    # Task Event
    def get_task_event(self, id: str) -> Optional[Dict[str, Any]]:
        """查詢任務歷史日誌
        
        Args:
            id (str): 任務ID uuid str
            
        Returns:
            Optional[Dict[str, Any]]: 回傳任務資訊字典,若查無資料則回傳 None
            
        Raises:
            Exception: 當資料庫查詢發生錯誤時拋出異常
        """
        try:
            sql = "SELECT * FROM task_event WHERE id = %s"
            res = self.fetch_one(sql, (id,))
            return res
            
        except Exception as e:
            raise Exception(f"查詢Task Event失敗: {str(e)}")



    def update_task_event(self, params : UpdateTaskEventParams) -> Optional[Dict[str, Any]]:
        """更新任務事件狀態
        
        Args:
            id (str): 任務ID uuid str
            task_status (TaskEventStatus): 任務狀態  
            updated_at (datetime.datetime, optional): 結束時間
            error_message (str, optional): 錯誤訊息
            
        Returns:
            Optional[Dict[str, Any]]: 回傳更新後的資料字典,若更新失敗則回傳 None
            
        Raises:
            Exception: 當資料庫更新操作發生錯誤時拋出異常
        """
        try:
            # 建立要更新的欄位和參數列表
            update_fields = []
            params_list = []
            
            # 檢查每個欄位是否有值,有值才加入更新
            if params.event_stage is not None:
                update_fields.append("event_stage = %s")
                params_list.append(params.event_stage)
                
            if params.status is not None:
                update_fields.append("status = %s") 
                params_list.append(params.status)
                
            if params.updated_at is not None:
                update_fields.append("updated_at = %s")
                params_list.append(params.updated_at)
                
            if params.error_message is not None:
                update_fields.append("error_message = %s")
                params_list.append(params.error_message)
                
            # 如果沒有要更新的欄位就直接返回
            if not update_fields:
                return None
                
            # 組合 SQL 語句
            sql = f"UPDATE task_event SET {', '.join(update_fields)} WHERE id = %s"
            
            # 加入 id 參數
            params_list.append(params.id)
            
            # 執行更新
            self.execute(sql, tuple(params_list))
            self.commit()
            
        except Exception as e:
            raise Exception(f"更新Task Event失敗: {str(e)}")

    def db_claim_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """原子性領取任務，將 status 從 pending 更新為 running 並回傳任務資料。

        Args:
            task_id (str): 任務 ID uuid str

        Returns:
            Optional[Dict[str, Any]]: task_event 整列字典，若已被領走或不存在則回傳 None

        Raises:
            Exception: 當資料庫操作發生錯誤時拋出異常
        """
        try:
            sql = """
            UPDATE task_event
            SET status = %s,
                updated_at = NOW()
            WHERE id = %s AND status = %s
            RETURNING *;
            """
            res = self.fetch_one(sql, ('running', task_id, 'pending'))
            self.commit()

            if res is None:
                return None
            return dict(res)

        except Exception as e:
            self.rollback()
            raise Exception(f"Claim Task失敗: {str(e)}")
        
        
        # Test Result
    def get_test_results(self, params: GetTestResultsParams) -> Optional[Dict[str, Any]]:
        """List all 回測結果
        """
        try:
            sql_parts = ["SELECT",
                        "*",
                        "FROM",
                        "test_result",
                        "WHERE",
                        "1 = 1"]  # 初始 WHERE 條件

            query_params_list = [] # 用於儲存參數化查詢的參數值

            # 動態增加 WHERE 條件
            if params.str_name != "":
                sql_parts.append("AND strategy_parms ->> 'name' = %s") # 使用 %s 作為佔位符
                query_params_list.append(params.str_name) # 將參數值加入列表

            if params.code!= "":
                sql_parts.append("AND strategy_parms -> 'data_model' ->> 'code' = %s")
                query_params_list.append(params.code)

            if params.candle != "":
                sql_parts.append("AND strategy_parms -> 'data_model' ->> 'candle' = %s")
                query_params_list.append(params.candle)

            # 動態設定 ORDER BY 欄位
            sort_by_column = "strategy_parms ->> 'name'" # 預設排序欄位
            sort_by = params.sort_by.value

            if sort_by == "code":
                sort_by_column = "strategy_parms -> 'data_model' ->> 'code'"
            elif sort_by == "profit":
                sort_by_column = "(summary ->> 'total_return')::numeric"
            elif sort_by == "profit_rate":
                sort_by_column = "(summary ->> 'total_return_rate')::numeric"
            elif sort_by == "start_time":
                sort_by_column = "strategy_parms -> 'data_model' ->> 'start_time'"
            elif sort_by == "end_time":
                sort_by_column = "strategy_parms -> 'data_model' ->> 'end_time'"

            sql_parts.append(f"ORDER BY {sort_by_column}") # 使用 f-string 組裝 ORDER BY 子句

            # 動態設定排序方式 (ASC/DESC)
            sort_order = params.sort_order.value
            if sort_order == "desc":
                sql_parts.append("DESC")

            # 加入 LIMIT 和 OFFSET 子句
            sql_parts.append("LIMIT %s") 
            query_params_list.append(params.page_size) 
            sql_parts.append("OFFSET %s") 
            query_params_list.append((params.page - 1) * params.page_size) 


            sql_query = " ".join(sql_parts)
            print(sql_query)
            
            return self.fetch_all(sql_query, tuple(query_params_list))
            
        except Exception as e:
            raise Exception(f"查詢Task Result失敗: {str(e)}")
        
    def upsert_test_result(self, params : TestResultUpsertParams):
        """
        執行 UPSERT 操作，當 key_string 重複時更新，否則插入新資料。

        Args:
            conn: psycopg2 資料庫連線物件
            data: 包含要 UPSERT 資料的字典，鍵值需對應 SQL 語句中的佔位符
        """
        sql = """
        INSERT INTO test_result (
            key_string,
            strategy_parms,
            tester_params,
            summary,
            file,
            completed_at,
            updated_at,
            task_event_id
        ) VALUES (
            %(key_string)s,
            %(strategy_parms)s,
            %(tester_params)s,
            %(summary)s,
            %(file)s,
            %(completed_at)s,
            %(updated_at)s,
            %(task_event_id)s
        )
        ON CONFLICT (key_string) DO UPDATE SET
            strategy_parms = EXCLUDED.strategy_parms,
            tester_params = EXCLUDED.tester_params,
            summary = EXCLUDED.summary,
            file = EXCLUDED.file,
            completed_at = EXCLUDED.completed_at,
            updated_at = EXCLUDED.updated_at,
            task_event_id = EXCLUDED.task_event_id;
        """

        try:
            params_dict = params.as_dict() # 將 Pydantic 模型轉換為字典

            # 顯式將 JSONB 欄位的值轉換為 JSON 字串
            params_dict['strategy_parms'] = json.dumps(params_dict['strategy_parms'])
            params_dict['tester_params'] = json.dumps(params_dict['tester_params'])
            params_dict['summary'] = json.dumps(params_dict['summary'])
            params_dict['file'] = json.dumps(params_dict['file'])

            self.execute(sql, params_dict)    # 傳遞字典給 execute 方法
            self.commit()

        except Exception as e:
            raise Exception(f"UpSert Task Result失敗: {str(e)}")
