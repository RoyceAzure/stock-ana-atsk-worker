from models.task_event import TaskEvent
from service.task.task_coordinator import ITaskCoordinator
from service.task.task_factory import TaskCoordinatorFactory


class TaskCoordinatorDispatch(ITaskCoordinator):
    """依 event_name 動態建立 TaskCoordinator 並執行。"""

    def __init__(self, coordinator_factory: TaskCoordinatorFactory) -> None:
        self._coordinator_factory = coordinator_factory

    def execute(self, task_event: TaskEvent) -> None:
        self._coordinator_factory.create(task_event).execute(task_event)
