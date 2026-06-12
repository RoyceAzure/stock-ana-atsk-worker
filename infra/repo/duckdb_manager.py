import logging
import threading
from queue import Empty, Queue
from typing import Optional
import duckdb
from infra.repo.object_storage import ObjectStorageConfig, StorageBackend


class DuckDBManager:
    _pool = Queue()
    _lock = threading.Lock()
    _config: Optional[ObjectStorageConfig] = None
    _all_connections = []

    @classmethod
    def initialize(cls, config: ObjectStorageConfig, pool_size: int = 10):
        """初始化全域設定與預建連線池。"""
        cls._config = config
        duckdb.execute("SET memory_limit = '256MB'")
        for _ in range(pool_size):
            cls._pool.put(cls._create_new_connection())

    @classmethod
    def _ensure_config(cls) -> ObjectStorageConfig:
        if cls._config is None:
            raise RuntimeError("DuckDBManager 尚未初始化，請先呼叫 DuckDBManager.initialize()")
        return cls._config

    @classmethod
    def _create_new_connection(cls):
        """建立並配置全新的 DuckDB 連線。"""
        config = cls._ensure_config()
        con = duckdb.connect(":memory:")
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(cls._build_secret_sql(config))

        with cls._lock:
            cls._all_connections.append(con)
        return con

    @classmethod
    def _build_secret_sql(cls, config: ObjectStorageConfig) -> str:
        secret_name = "object_storage_config"
        if config.backend is StorageBackend.GCS:
            if config.use_adc:
                return f"""
                    CREATE OR REPLACE SECRET {secret_name} (
                        TYPE gcs,
                        PROVIDER credential_chain
                    );
                """
            if config.uses_gcs_s3_interop:
                return f"""
                    CREATE OR REPLACE SECRET {secret_name} (
                        TYPE S3,
                        KEY_ID '{config.access_key}',
                        SECRET '{config.secret_key}',
                        REGION 'auto',
                        ENDPOINT 'storage.googleapis.com',
                        URL_STYLE 'path',
                        USE_SSL 'true'
                    );
                """
            return f"""
                CREATE OR REPLACE SECRET {secret_name} (
                    TYPE gcs,
                    KEY_ID '{config.access_key}',
                    SECRET '{config.secret_key}'
                );
            """

        url_style = "path" if config.backend is StorageBackend.MINIO else "vhost"
        use_ssl = "false" if config.backend is StorageBackend.MINIO else "true"
        endpoint_str = (
            f"ENDPOINT '{config.host}:{config.port}',"
            if config.backend is StorageBackend.MINIO and config.host and config.port
            else ""
        )
        region = config.region or "us-east-1"
        return f"""
            CREATE OR REPLACE SECRET {secret_name} (
                TYPE S3,
                KEY_ID '{config.access_key}',
                SECRET '{config.secret_key}',
                REGION '{region}',
                {endpoint_str}
                URL_STYLE '{url_style}',
                USE_SSL '{use_ssl}'
            );
        """

    @classmethod
    def get_conn(cls) -> duckdb.DuckDBPyConnection:
        """獲取連線，若池中無連線則動態建立。"""
        try:
            return cls._pool.get_nowait()
        except Empty:
            return cls._create_new_connection()

    @classmethod
    def return_conn(cls, con: duckdb.DuckDBPyConnection):
        """歸還健康的連線至池中。"""
        if con:
            cls._pool.put(con)

    @classmethod
    def return_and_delete(cls, con: duckdb.DuckDBPyConnection):
        """徹底棄用有問題的連線。"""
        if con:
            with cls._lock:
                if con in cls._all_connections:
                    cls._all_connections.remove(con)
            try:
                con.close()
            except Exception:
                pass

    @classmethod
    def close_all(cls):
        """關閉所有由 Manager 管理的連線。"""
        with cls._lock:
            logging.info("正在關閉所有 DuckDB 連線...")
            while not cls._pool.empty():
                try:
                    cls._pool.get_nowait()
                except Empty:
                    break

            for con in cls._all_connections:
                try:
                    con.close()
                except Exception as e:
                    logging.error(f"關閉連線時出錯: {e}")

            cls._all_connections.clear()
