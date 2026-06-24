from __future__ import annotations

import logging
from typing import Optional

from psycopg2 import OperationalError

from app.cloud.assembly import build_cloud_worker_assembly
from app.config import WorkerConfig
from app.task.assembly import build_task_worker_assembly
from core.life_cycle.lifecycle import register_graceful_shutdown, shutdown_event
from core.logger.logger import setup_logging
from infra.repo.duckdb_manager import DuckDBManager
from infra.repo.object_storage import create_parquet_merger
from infra.repo.pg_dao import DBPoolConfig, DatabasePool, DatabaseRepository
from infra.repo.pipline_model.trade_price_sink_factory import (
    create_trade_price_parquet_sink,
)
from service.consumer.gcp_consumer import GCPMessageConsumer, IMessageConsumer
from service.task.task_factory import TaskHandlerDeps
from service.taskevent.helper import TaskEventHelper

logger = logging.getLogger(__name__)


class Application:
    """應用組裝點：管理 worker 所需模組的生命週期與優雅關閉。"""

    def __init__(self, config: Optional[WorkerConfig] = None) -> None:
        self.config = config or WorkerConfig.from_env()
        self._pg_pool: Optional[DatabasePool] = None
        self._consumer: Optional[IMessageConsumer] = None
        self._bootstrapped = False

    def run(self) -> None:
        """啟動 worker 並阻塞，直到收到關閉訊號。"""
        self._bootstrap()
        try:
            assert self._consumer is not None
            self._consumer.start()
        finally:
            self._teardown()

    def request_shutdown(self) -> None:
        """手動觸發優雅關閉。"""
        if not shutdown_event.is_set():
            logger.warning("[Application] 收到手動關閉請求")
            shutdown_event.set()

    def _bootstrap(self) -> None:
        if self._bootstrapped:
            return

        setup_logging(self.config.app, level=self.config.log_level)
        register_graceful_shutdown()

        cloud_assembly = build_cloud_worker_assembly(self.config)
        DuckDBManager.initialize(
            cloud_assembly.duckdb_config,
            pool_size=self.config.duckdb_pool_size,
        )

        pool_config = DBPoolConfig(
            min_conn=self.config.pg_pool_min_conn,
            max_conn=self.config.pg_pool_max_conn,
        )
        try:
            self._pg_pool = DatabasePool(pool_config, self.config.db_config)
        except OperationalError as exc:
            raise RuntimeError(f"PostgreSQL 連線池建立失敗: {exc}") from exc

        pg_conn = self._pg_pool.get_connection()
        db_repo = DatabaseRepository(pg_conn)
        task_event_helper = TaskEventHelper(db_repo)
        parquet_merger = create_parquet_merger(
            cloud_assembly.object_storage_bucket_base_path,
            cloud_assembly.storage_config,
        )
        trade_price_data_sink = create_trade_price_parquet_sink(
            cloud_assembly.object_storage_bucket_base_path,
            cloud_assembly.storage_config,
            DuckDBManager.get_conn(),
        )

        assert self.config.task is not None
        task_assembly = build_task_worker_assembly(
            self.config.task,
            task_event_helper,
            TaskHandlerDeps(
                pg_pool=self._pg_pool,
                trade_price_data_sink=trade_price_data_sink,
                parquet_merger=parquet_merger,
            ),
        )

        self._consumer = GCPMessageConsumer(
            config=cloud_assembly.pubsub_config,
            task_cooridinaor=task_assembly.dispatch,
            task_event_helper=task_event_helper,
            db_dao=db_repo,
        )

        self._bootstrapped = True
        logger.info(
            "[Application] 組裝完成，任務類型: %s",
            ", ".join(self.config.task.enabled_values),
        )

    def _teardown(self) -> None:
        logger.info("[Application] 開始釋放資源")

        if self._consumer is not None:
            self._consumer.close(timeout=self.config.shutdown_drain_timeout)
            self._consumer = None

        DuckDBManager.close_all()

        if self._pg_pool is not None:
            try:
                self._pg_pool.return_connection()
                self._pg_pool.close()
            except Exception as exc:
                logger.error("[Application] 關閉 PostgreSQL 連線池失敗: %s", exc)
            self._pg_pool = None

        self._bootstrapped = False
        logger.info("[Application] 資源釋放完成")
