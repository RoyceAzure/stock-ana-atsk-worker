from typing import Protocol, Tuple
from models.task_event import EventStage, TaskEvent, TaskEventStatus
from service.task.processer import TaskProcesser
from service.taskevent.helper import TaskEventHelper
from core.life_cycle.lifecycle import shutdown_event
from core.error.task_error import TaskAlreadyClaimedError, TaskAlreadyCompletedError, TransientError, PermanentError

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
        task_processer: 任務處理器
    """
    def __init__(self, task_event_helper: TaskEventHelper, task_processer: TaskProcesser):
        self._current_stage = EventStage.PRE_STAGE # 標示為哪種任務階段.
        self.task_event_helper = task_event_helper
        self.task_processer = task_processer


    def execute(self, task_event: TaskEvent) -> None:
        """執行任務
        
        Args:
            task_event: 任務事件
        """
        success, reason = self.excute_with_retry(task_event)
        if not success:
            self.task_event_helper.update_task_event(task_event.id, TaskEventStatus.TaskStatusFailed, reason)
        else:
            self.task_event_helper.update_task_event(task_event.id, TaskEventStatus.TaskStatusCompleted)

    def excute_with_retry(self, task_event: TaskEvent) -> Tuple[Boolean, str]:
        max_retries = 3
        base_backoff = 5  # 秒

        for attempt in range(max_retries):
            try:
                # 呼叫純商業邏輯的 Processor
                self.task_processer.process(task_event)

                # 成功執行，跳出迴圈，準備回傳 ACK
                return True, "Success"

            except (TaskAlreadyClaimedError, TaskAlreadyCompletedError) as e:
                # 被別人做掉了，當作成功，直接 ACK
                return True, f"Ignored: {str(e)}"

            except TransientError as e:
                # 發生可重試的錯誤
                if attempt < max_retries - 1:
                    sleep_time = base_backoff * (2 ** attempt) # 指數退避
                    print(f"遇到瞬態錯誤 {e}，等待 {sleep_time} 秒後重試...")

                    if shutdown_event.wait(timeout=sleep_time):
                        return False, "Shutdown interrupted retry"
                else:
                    # 重試達上限，將拋出例外讓外層收尾
                    return False, f"Max retries reached for transient error: {e}"

            except PermanentError as e:
                # 遇到永久錯誤，絕對不重試
                return False, f"Fatal error, aborting: {e}"

            except Exception as e:
                # 捕捉未知的系統錯誤 (例如 KeyError, AttributeError 等 Bug)
                # 未知錯誤通常視為永久錯誤，避免無限重試卡死系統
                return False, f"Unknown unexpected error: {e}"
