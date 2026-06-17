import logging
from typing import Protocol
from models.task_event import TaskEvent, TaskEventStatus
from service.task.handler import TaskHandler
from service.taskevent.helper import TaskEventHelper
from core.life_cycle.lifecycle import shutdown_event
from core.error.task_error import  TransientError, PermanentError

logger = logging.getLogger(__name__)

class ITaskCoordinator(Protocol):
    """任務協調器
    
    整合任務執行與事件更新
    處理任務重試機制，以及錯誤處理
    """
    def execute(self, task_event: TaskEvent) -> None:
        ...


class TaskCoordinator(ITaskCoordinator):
    """任務協調器
    
    整合任務執行與事件更新
    處理任務重試機制，以及錯誤處理
    重試通通由TaskCoordinator處理，不經由外部infra 如消息對列requeue等
    
    Args:
        task_event_helper: 任務事件助手
        task_handler: 任務處理器
    """
    def __init__(self, task_event_helper: TaskEventHelper, task_handler: TaskHandler):
        self.task_event_helper = task_event_helper
        self.task_handler = task_handler

    def execute(self, task_event: TaskEvent) -> None:
        """執行任務
        
        Args:
            task_event: 任務事件
        """
        final_stage = TaskEventStatus.TaskStatusCompleted
        event_stage = self.task_handler.get_stage
        err_msg = ""
        try:
            self._excute_with_retry(task_event)
        except Exception as e:
            err_msg = f"發生錯誤 [{type(e).__name__}]: {str(e)}"
            final_stage = TaskEventStatus.TaskStatusFailed
            raise
        finally:
            self.task_event_helper.update_task_event(task_event.id, final_stage, event_stage, err_msg)


    def _excute_with_retry(self, task_event: TaskEvent) -> None:
        max_retries = 3
        base_backoff = 5  # 秒

        for attempt in range(max_retries):
            try:
                # 呼叫純商業邏輯的 Processor
                self.task_handler.process(task_event)
                return

            except TransientError as e:
                # 發生可重試的錯誤
                if attempt < max_retries - 1:
                    sleep_time = base_backoff * (2 ** attempt) # 指數退避

                    print(f"遇到瞬態錯誤 {e}，等待 {sleep_time} 秒後重試...")

                    if shutdown_event.wait(timeout=sleep_time):
                        logging.error("Shutdown interrupted retry")
                else:
                    # 重試達上限，將拋出例外讓外層收尾
                    logging.error("Max retries reached for transient")
                    raise PermanentError(e)
