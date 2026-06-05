import logging
import duckdb
import threading
from queue import Queue, Empty

class DuckDBManager:
    _pool = Queue()
    _lock = threading.Lock()
    _config = None
    _is_minio = False
    _all_connections = [] # 追蹤所有建立過的連線，方便一次關閉
    @classmethod
    def initialize(cls, config, is_minio=False, pool_size=10):
        """初始化全域設定與預建連線池"""
        cls._config = config
        cls._is_minio = is_minio
        duckdb.execute("SET memory_limit = '256MB'")
        for _ in range(pool_size):
            cls._pool.put(cls._create_new_connection())

    @classmethod
    def _create_new_connection(cls):
        """建立並配置全新的 DuckDB 連線"""
        # 使用 :memory: 確保每個連線擁有獨立的 Engine State
        con = duckdb.connect(':memory:')
        
        # 你的配置邏輯
        con.execute("INSTALL aws; LOAD aws;")
        secret_name = "s3_config"
        url_style = "path" if cls._is_minio else "vhost"
        use_ssl = "false" if cls._is_minio else "true"
        endpoint_str = f"ENDPOINT '{cls._config.host}:{cls._config.port}'," if cls._is_minio else ""

        create_secret_sql = f"""
            CREATE OR REPLACE SECRET {secret_name} (
                TYPE S3,
                KEY_ID '{cls._config.access_key}',
                SECRET '{cls._config.secret_key}',
                REGION '{cls._config.region}',
                {endpoint_str}
                URL_STYLE '{url_style}',
                USE_SSL '{use_ssl}'
            );
        """
        con.execute(create_secret_sql)
        with cls._lock:
            cls._all_connections.append(con) # 記錄連線
        return con

    @classmethod
    def get_conn(cls) -> duckdb.DuckDBPyConnection:
        """獲取連線，若池中無連線則動態建立"""
        try:
            return cls._pool.get_nowait()
        except Empty:
            return cls._create_new_connection()

    @classmethod
    def return_conn(cls, con: duckdb.DuckDBPyConnection):
        """歸還健康的連線至池中"""
        if con:
            cls._pool.put(con)

    @classmethod
    def return_and_delete(cls, con: duckdb.DuckDBPyConnection):
        """徹底棄用有問題的連線"""
        if con:
            with cls._lock:
                if con in cls._all_connections:
                    cls._all_connections.remove(con)
            try:
                con.close()
            except:
                pass

    @classmethod
    def close_all(cls):
        """關閉所有由 Manager 管理的連線"""
        with cls._lock:
            logging.info("正在關閉所有 DuckDB 連線...")
            # 1. 清空 Queue，防止新的 get_conn 拿到已關閉的連線
            while not cls._pool.empty():
                try:
                    cls._pool.get_nowait()
                except Empty:
                    break
            
            # 2. 逐一關閉所有追蹤中的連線
            for con in cls._all_connections:
                try:
                    con.close()
                except Exception as e:
                    logging.error(f"關閉連線時出錯: {e}")
            
            cls._all_connections.clear()