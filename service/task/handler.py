from abc import ABC, abstractmethod
from models.task_event import EventStage, TaskEvent
from models.task_result import TaskResult

class TaskHandler(ABC):
    """任務處理器基類
    
    定義了任務處理的基本接口
    """

    def __init__(self, stage : EventStage) -> None:
        self.event_stage = stage

    @abstractmethod
    def process(self, task_event: TaskEvent) -> TaskResult:
        """處理任務
        
        Args:
            task_event: 要處理的任務事件
            
        Returns:
            TaskResult: 任務處理結果
            
        Raises:
            TaskResultException: 當處理失敗時拋出
        """
        pass

    @property
    def get_stage(self) -> EventStage:
        """
        取得當前任務執行階段
        """
        return self.event_stage

    def set_stage(self, stage:EventStage) -> None:
        """
        設置當前任務執行階段
        """
        self.event_stage = stage
        