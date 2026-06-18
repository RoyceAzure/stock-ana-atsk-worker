from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Protocol

import duckdb

from infra.repo.data_meger.blob_parquet_meger import BlobParquetMerger
from infra.repo.pg_dao import DatabasePool
from models.task_event import EventName, TaskEvent
from service.task.handler import TaskHandler
from service.task.pandas_preprocesse_handler import PreProcessPandasTaskProcessor
from service.task.task_coordinator import TaskCoordinator
from service.taskevent.helper import TaskEventHelper


class TaskHandlerFactory(Protocol):
    def __call__(self) -> TaskHandler:
        ...


@dataclass(frozen=True)
class TaskHandlerDeps:
    pg_pool: DatabasePool
    duckdb_conn: duckdb.DuckDBPyConnection
    parquet_merger: BlobParquetMerger


def _event_name_key(event_name: EventName | str) -> str:
    if isinstance(event_name, EventName):
        return event_name.value
    return str(event_name)


class TaskHandlerRegistry:
    """任務處理器註冊表：由 event_name 映射至 handler factory。"""

    def __init__(self) -> None:
        self._factories: Dict[str, TaskHandlerFactory] = {}

    def register(self, event_name: EventName | str, factory: TaskHandlerFactory) -> None:
        self._factories[_event_name_key(event_name)] = factory

    def create(self, event_name: EventName | str) -> TaskHandler:
        key = _event_name_key(event_name)
        if key not in self._factories:
            raise ValueError(f"No task handler registered for event_name={key}")
        return self._factories[key]()

    def supports(self, event_name: EventName | str) -> bool:
        return _event_name_key(event_name) in self._factories


HandlerRegistrar = Callable[[TaskHandlerRegistry, TaskHandlerDeps], None]


def _register_preprocess(registry: TaskHandlerRegistry, deps: TaskHandlerDeps) -> None:
    registry.register(
        EventName.PREPROCESS,
        lambda: PreProcessPandasTaskProcessor(
            deps.pg_pool.get_connection(),
            deps.duckdb_conn,
            deps.parquet_merger,
        ),
    )


_HANDLER_REGISTRARS: Dict[EventName, HandlerRegistrar] = {
    EventName.PREPROCESS: _register_preprocess,
}


def build_task_handler_registry(
    enabled_event_names: Iterable[EventName],
    deps: TaskHandlerDeps,
) -> TaskHandlerRegistry:
    """依啟用的 event_name 建立 handler registry。"""

    enabled = frozenset(enabled_event_names)
    if not enabled:
        raise ValueError("至少需要啟用一種 WORKER_TASK_TYPES")

    registry = TaskHandlerRegistry()
    for event_name in sorted(enabled, key=lambda item: item.value):
        registrar = _HANDLER_REGISTRARS.get(event_name)
        if registrar is None:
            raise ValueError(f"event_name={event_name.value} 尚未實作 handler")
        registrar(registry, deps)

    return registry


def build_default_task_handler_registry(
    pg_pool: DatabasePool,
    duckdb_conn: duckdb.DuckDBPyConnection,
    parquet_meger: BlobParquetMerger,
) -> TaskHandlerRegistry:
    """建立預設 registry（僅 preprocessing，供測試與向後相容）。"""

    deps = TaskHandlerDeps(
        pg_pool=pg_pool,
        duckdb_conn=duckdb_conn,
        parquet_merger=parquet_meger,
    )
    return build_task_handler_registry([EventName.PREPROCESS], deps)


class TaskCoordinatorFactory:
    """依 TaskEvent.event_name 動態建立對應 handler 的 TaskCoordinator。"""

    def __init__(self, task_event_helper: TaskEventHelper, registry: TaskHandlerRegistry):
        self.task_event_helper = task_event_helper
        self.registry = registry

    def create(self, task_event: TaskEvent) -> TaskCoordinator:
        handler = self.registry.create(task_event.event_name)
        return TaskCoordinator(self.task_event_helper, handler)


def create_coordinator_for_task(
    task_event: TaskEvent,
    task_event_helper: TaskEventHelper,
    pg_pool: DatabasePool,
    duckdb_conn: duckdb.DuckDBPyConnection,
    parquet_meger: BlobParquetMerger,
    registry: Optional[TaskHandlerRegistry] = None,
) -> TaskCoordinator:
    """
    便利方法：依 task_event 建立 coordinator。
    若未傳入 registry，使用預設 registry（僅含 preprocessing）。
    """

    resolved_registry = registry or build_default_task_handler_registry(
        pg_pool, duckdb_conn, parquet_meger
    )
    factory = TaskCoordinatorFactory(task_event_helper, resolved_registry)
    return factory.create(task_event)
