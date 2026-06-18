from __future__ import annotations

from dataclasses import dataclass

from app.dispatch import TaskCoordinatorDispatch
from app.task.profile import TaskWorkerProfile
from service.task.task_factory import (
    TaskCoordinatorFactory,
    TaskHandlerDeps,
    TaskHandlerRegistry,
    build_task_handler_registry,
)
from service.taskevent.helper import TaskEventHelper


@dataclass(frozen=True)
class TaskWorkerAssembly:
    """第二層組裝結果：任務 handler registry 與 dispatch 管線。"""

    registry: TaskHandlerRegistry
    coordinator_factory: TaskCoordinatorFactory
    dispatch: TaskCoordinatorDispatch


def build_task_worker_assembly(
    profile: TaskWorkerProfile,
    task_event_helper: TaskEventHelper,
    deps: TaskHandlerDeps,
) -> TaskWorkerAssembly:
    registry = build_task_handler_registry(profile.enabled_event_names, deps)
    coordinator_factory = TaskCoordinatorFactory(task_event_helper, registry)
    dispatch = TaskCoordinatorDispatch(coordinator_factory)
    return TaskWorkerAssembly(
        registry=registry,
        coordinator_factory=coordinator_factory,
        dispatch=dispatch,
    )
