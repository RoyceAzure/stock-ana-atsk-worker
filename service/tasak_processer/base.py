from abc import ABC, abstractmethod
from models.task_event import TaskEvent
from models.task_result import TaskResult

class TaskProcessor(ABC):
    """任務處理器基類
    
    定義了任務處理的基本接口
    """
    
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