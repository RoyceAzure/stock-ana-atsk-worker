import logging
import threading
import uuid
from domain.model.sqs_consumer import Consumer, TaskEventProcesser
from domain.model.task_event import EventStage, TaskEventStatus
from domain.model.task_processer import TaskProcessor
from pkg.util.status_manager import StatusManager, WorkStatus

class SQSPreprocessConsumer:
    """SQS 預處理消費者
    
    處理 SQS 預處理任務，負責：
    1. 接收 SQS 預處理任務
    2. 執行預處理
    3. 更新任務狀態
    """
    def __init__(self, consumer: Consumer, task_event_processer: TaskEventProcesser, processer: TaskProcessor):
        self._current_stage = EventStage.PRE_STAGE # 標示為哪種任務階段.
        self.consumer_thread = None # 消費者線程
        self.consumer = consumer
        self.task_event_processer = task_event_processer
        self.processer = processer
        self.consumer_id = f"{__name__}_{uuid.uuid4().hex[:8]}"
        self.status_manager = StatusManager(work_name=self.consumer_id, initial_state=WorkStatus.READY)
        self.logger = logging.getLogger(__name__)
    
    def consume(self) -> None:
        while self.status_manager.is_state(WorkStatus.RUNNING):
            try:
                messages = self.consumer.consume()
            except Exception as e:
                self.logger.error(f"SQSBacktestConsumer-{self.consumer_id} 取得消費資料失敗: {e}")
                continue
            if len(messages) == 0:
                continue

            task_events, receipt_handles, failed_receipt_handles = self.task_event_processer.decode_message(messages)
            #先處理解析失敗的資料，直接刪除訊息
            for failed_receipt_handle in failed_receipt_handles:
                try:    
                    self.consumer.delete_message(failed_receipt_handle)
                except Exception as e:
                    self.logger.error(f"SQSBacktestConsumer-{self.consumer_id} 刪除消費資料失敗: {e}")
                    self.logger.warning(f"將會有遺留的訊息未刪除，請手動刪除，或者後續流程恢復後刪除")
                    continue

            #再處理解析成功的資料
            for task_event, receipt_handle in zip(task_events, receipt_handles):
                try: 
                    # 更新任務狀態為運行中
                    self.task_event_processer.update_task_event(
                        task_id=task_event.id,
                        status=TaskEventStatus.TaskStatusRunning.value,
                        stage=self._current_stage
                    )
                    # 執行任務
                    task_result = self.processer.process(task_event)

                    # 處理成功``
                    self.task_event_processer.handle_success(task_result, self._current_stage)
                except Exception as e:
                    self.task_event_processer.handle_error(task_event.id, self._current_stage, e)
                finally:
                    self.consumer.delete_message(receipt_handle)
        self.logger.error(f"SQSBacktestConsumer-{self.consumer_id} 消費者結束消費循環，開始清理資源 ")
        self._cleanup()
    def start(self) -> None:
        if self.status_manager.is_state(WorkStatus.RUNNING):
            return

        if self.consumer_thread and self.consumer_thread.is_alive():
            return

        try:
            self.status_manager.transition_to(WorkStatus.RUNNING)
            self.logger.info(f"SQSBacktestConsumer-{self.consumer_id} 正在啟動")
            self.consumer_thread = threading.Thread(target=self.consume, name=f"SQSBacktestConsumer-{self.consumer_id}", daemon=False)
            self.consumer_thread.start()
            self.logger.info(f"SQSBacktestConsumer-{self.consumer_id} 已啟動")
        except Exception as e:
            self.logger.error(f"SQSBacktestConsumer-{self.consumer_id} 啟動失敗: {e}")
            self._cleanup()
            raise 

    def stop(self) -> None:
        if self.status_manager.is_state(WorkStatus.STOPPED):
            return
        self._cleanup()


    def _cleanup(self) -> None:
        """只清理消費者thread"""
        try:
            self.logger.info(f"SQSBacktestConsumer-{self.consumer_id} 正在清理資源")
            if not self.consumer_thread or not self.consumer_thread.is_alive():
                return
            self.consumer.stop()
            # self.consumer_thread.join(timeout=self.consumer.get_config().WaitTimeSeconds + 10)
            # if self.consumer_thread.is_alive():
            #     self.logger.warning(f"SQSBacktestConsumer-{self.consumer_id} 線程未能在超時時間內結束")
        except Exception as e:
            self.logger.warning(f"SQSBacktestConsumer-{self.consumer_id} 清理資源失敗: {e}")
        finally:
            self.consumer_thread = None
            self.status_manager.transition_to(WorkStatus.STOPPED)
            self.logger.info(f"SQSBacktestConsumer-{self.consumer_id} 資源清理完成")