import base64
import datetime
import logging
from typing import Any, Dict, List, Optional, Protocol, Tuple
import uuid
from infra.repo.pg_dao import DatabaseRepository
from models.task_event import EventStage, TaskEvent, TaskEventStatus, UpdateTaskEventParams
from models.task_result import ConsumerResult, TaskResult
from core.logger.task_context import task_log_context

logger = logging.getLogger(__name__)


class TaskEventHelper(Protocol):
    def handle_success(self, result: TaskResult, stage: EventStage) -> None:
        """處理任務成功完成的情況
        
        根據任務結果更新任務狀態
        
        Args:
            result: 任務執行結果
        """
        ... 
    def handle_error(self, task_id: str, stage: EventStage, error: Exception) -> None:
        """處理任務執行過程中的錯誤
        
        統一的錯誤處理邏輯
        
        Args:
            task_id: 任務ID
            stage: 任務階段
            error: 捕獲到的異常
        """
        ...
    def update_task_event(self, 
                        task_id: str, 
                        status: TaskEventStatus,
                        stage: Optional[EventStage] = None,
                        error_message: str = "") -> None:
        """更新任務事件狀態
        Args:
            task_id: 任務ID
            status: 任務狀態
            stage: 任務階段（可選）
            error_message: 錯誤信息（可選）
        """
        ...

class TaskEventHelper:
    """處理Task event 領域相關邏輯 資料前處理，以及後續處理 for sqs consumer"""
    def __init__(self, db_dao: DatabaseRepository):
        self.db_dao = db_dao

    def handle_success(self, result: TaskResult, stage: EventStage) -> None:
        """處理任務成功完成的情況，包括任務成功和任務失敗
        
        根據任務結果更新任務狀態
        
        Args:
            result: 任務執行結果
        """
        try:
            with task_log_context(result.id):
                status = (TaskEventStatus.TaskStatusCompleted.value         
                        if result.is_successed.value == ConsumerResult.SUCCESSED.value                      
                        else TaskEventStatus.TaskStatusFailed.value)  
                
                self.update_task_event(
                    task_id=result.id,
                    status=status,
                    stage=stage,
                    error_message=result.message if result.is_successed.value == ConsumerResult.FAILED.value else ""
                )
                logger.info("任務狀態更新完成")
        except Exception as e:
            logger.error("任務成功，但是更新任務狀態失敗: %s", e)


    def handle_error(self, task_id: str, stage: EventStage, error: Exception) -> None:
        """處理任務執行過程中的錯誤
        
        統一的錯誤處理邏輯
        
        Args:
            error: 捕獲到的異常
        """
        try:
            with task_log_context(task_id):
                self.update_task_event(
                    task_id=task_id,
                    status=TaskEventStatus.TaskStatusFailed.value,
                    stage=stage,
                    error_message=str(error)
                )
                logger.error("%s 任務失敗: %s", self.__class__.__name__, error)
        except Exception as e:
            logger.error("任務失敗，且更新任務狀態失敗: %s", e)


    def _get_task_event(self, message: bytes) -> TaskEvent:
        """從消息中解析出 TaskEvent
        
        Args:
            message: 原始消息內容
            
        Returns:
            TaskEvent: 解析後的任務事件對象
            
        Raises:
            ValueError: 當解析失敗時拋出
        """
        raw_bytes = base64.b64decode(message) # 解碼成原始bytes aws sqs
        task_id = uuid.UUID(bytes=raw_bytes)

        task_event_entity = self.db_dao.get_task_event(task_id)
        if task_event_entity is None:
            raise ValueError("task event不存在")
        
        return TaskEvent(**task_event_entity)

    def update_task_event(self, 
                        task_id: str, 
                        status: TaskEventStatus,
                        stage: Optional[EventStage] = None,
                        error_message: str = "") -> None:
        """更新任務事件狀態
        
        統一的任務狀態更新方法，處理可能的異常
        
        Args:
            task_id: 任務ID
            status: 任務狀態
            stage: 任務階段（可選）
            error_message: 錯誤信息（可選）
        """
        params = UpdateTaskEventParams(
            id=task_id,
            status=status,
            updated_at=datetime.datetime.now(datetime.timezone.utc),
            error_message=error_message
        )
        if stage:
            params.event_stage = stage
        self.db_dao.update_task_event(params)