from __future__ import annotations

import logging
from typing import Optional

import psycopg2
from psycopg2 import OperationalError

from app.config import WorkerConfig
from app.dispatch import TaskCoordinatorDispatch
from core.life_cycle.lifecycle import register_graceful_shutdown, shutdown_event
from core.logger.logger import setup_logging
from infra.repo.duckdb.factory import from_env as duckdb_config_from_env
from infra.repo.duckdb_manager import DuckDBManager
from infra.repo.object_storage import ObjectStorageConfig, create_parquet_merger
from infra.repo.pg_dao import DatabaseRepository
from service.consumer.gcp_consumer import GCPMessageConsumer, PubSubConsumerConfig
from service.task.task_factory import (
    TaskCoordinatorFactory,
    build_default_task_handler_registry,
)
from service.taskevent.helper import TaskEventHelper

logger = logging.getLogger(__name__)


class Application:
    """應用組裝點：管理 worker 所需模組的生命週期與優雅關閉。"""

    def __init__(self, config: Optional[WorkerConfig] = None) -> None:
        self.config = config or WorkerConfig.from_env()
        self._pg_conn: Optional[psycopg2.extensions.connection] = None
        self._consumer: Optional[GCPMessageConsumer] = None
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

        setup_logging()
        register_graceful_shutdown()

        storage_config = ObjectStorageConfig.from_env(self.config.storage_backend)
        duckdb_config = duckdb_config_from_env(self.config.storage_backend)
        DuckDBManager.initialize(duckdb_config, pool_size=self.config.duckdb_pool_size)

        try:
            self._pg_conn = psycopg2.connect(**self.config.db_config_dict)
        except OperationalError as exc:
            raise RuntimeError(f"PostgreSQL 連線失敗: {exc}") from exc

        db_repo = DatabaseRepository(self._pg_conn)
        task_event_helper = TaskEventHelper(db_repo)
        parquet_merger = create_parquet_merger(
            self.config.object_storage_bucket_base_path,
            storage_config,
        )

        registry = build_default_task_handler_registry(
            self._pg_conn,
            DuckDBManager.get_conn(),
            parquet_merger,
        )
        coordinator_factory = TaskCoordinatorFactory(task_event_helper, registry)
        task_coordinator = TaskCoordinatorDispatch(coordinator_factory)

        pubsub_config = PubSubConsumerConfig(
            project_id=self.config.gcp_project_id,
            subscription_id=self.config.gcp_subscription_id,
            batch_size=self.config.pubsub_batch_size,
            visibility_timeout=self.config.pubsub_visibility_timeout,
            pull_timeout=self.config.pubsub_pull_timeout,
        )
        self._consumer = GCPMessageConsumer(
            config=pubsub_config,
            task_cooridinaor=task_coordinator,
            task_event_helper=task_event_helper,
            db_dao=db_repo,
        )

        self._bootstrapped = True
        logger.info("[Application] 組裝完成，準備啟動 consumer")

    def _teardown(self) -> None:
        logger.info("[Application] 開始釋放資源")

        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None

        DuckDBManager.close_all()

        if self._pg_conn is not None:
            try:
                self._pg_conn.close()
            except Exception as exc:
                logger.error("[Application] 關閉 PostgreSQL 連線失敗: %s", exc)
            self._pg_conn = None

        self._bootstrapped = False
        logger.info("[Application] 資源釋放完成")
