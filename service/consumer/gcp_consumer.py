import time
import logging
from typing import Any, Dict, Optional, Protocol
from core.life_cycle.lifecycle import shutdown_event
from google.cloud import pubsub_v1
from google.api_core import retry
from google.api_core.exceptions import DeadlineExceeded
from models.task_event import TaskEvent
from service.task.task_coordinator import TaskCoordinator
from service.taskevent.helper import TaskEventHelper
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class PubSubConsumerConfig(BaseModel):
    # 基礎連線資訊
    project_id: str = Field(..., description="GCP 專案 ID")
    subscription_id: str = Field(..., description="訂閱通道 (Subscription) ID")

    # 流量控制與行為設定
    batch_size: int = Field(
        default=10, 
        ge=1, 
        le=1000, 
        description="單次拉取的最大訊息數量 (對應 max_messages)"
    )
    visibility_timeout: int = Field(
        default=30, 
        ge=10, 
        le=600, 
        description="訊息隱藏/處理時間 (Ack Deadline)，單位為秒。逾時未 ACK 則重派"
    )
    pull_timeout: float = Field(
        default=5.0, 
        ge=0.0, 
        description="同步拉取 (pull) 時，若無訊息的等待超時時間，單位為秒"
    )

class IMessageConsumer(Protocol):
    """消息消費者
    
    負責監聽消息對列，並執行任務
    """
    def start(self) -> None:
        ...

class GCPMessageConsumer(IMessageConsumer):
    """GCP 消息消費者
    
    負責監聽 GCP 消息對列，並執行任務
    """
    def __init__(self, config: PubSubConsumerConfig, task_cooridinaor: TaskCoordinator ,task_event_helper: TaskEventHelper):
        self.config = config
        self.task_cooridinaor = task_cooridinaor
        self.task_event_helper = task_event_helper
        self._init_consumer()

    def _init_consumer(self) -> None:
        # 1. 初始化 Subscriber 客戶端
        self.subscriber = pubsub_v1.SubscriberClient()
        # 2. 組合 Subscription 完整路徑
        self.subscription_path = self.subscriber.subscription_path(self.config.project_id, self.config.subscription_id)


    def start(self)-> None:
        logging.info(f"[Worker] 啟動，開始監聽 {self.config.subscription_path}")
        # Loop: is_running == True?
        while not shutdown_event.is_set():
            try:
                # 依 Flow Control 限制批次拉取訊息
                response = self.subscriber.pull(
                    request={
                        "subscription": self.subscription_path,
                        "max_messages": self.config.batch_size,
                    },
                    timeout=5.0, # 控制無訊息時的阻塞時間
                    retry=retry.Retry(deadline=self.config.visibility_timeout)
                )
            except DeadlineExceeded:
                # 取得任務? -> No (Sleep 避免空轉，pull timeout 本身已有阻塞效果)
                continue
            except Exception as e:
                logging.error(f"[Worker] 拉取訊息發生錯誤: {e}")
                time.sleep(1)
                continue

            messages = response.received_messages
            if not messages:
                continue

            logging.info(f"[Worker] 成功拉取 {len(messages)} 筆任務")
            
            # 記錄尚未處理的 ack_ids，用於觸發關機時的 Active NACK
            pending_ack_ids = [msg.ack_id for msg in messages]

            # 逐一迭代 Batch 內的訊息
            for msg in messages:
                # CheckRun: is_running == True?
                if shutdown_event.is_set():
                    logging.warning("[Worker] 收到關閉訊號，中斷 Batch 迴圈！")
                    break

                task_id = ""
                try:
                    task_id = msg.message.data.decode("utf-8")

                    # 1. 執行 DB UPDATE RETURNING (原子性 Claim)
                    payload = self.db_claim_task(task_id)
                    
                    if not payload:
                        # Claim 失敗 (已被領走) -> 發送 ACK (丟棄)
                        self.subscriber.acknowledge(
                            request={"subscription": self.subscription_path, "ack_ids": [msg.ack_id]}
                        )
                    else:
                        #解析payload
                        task_event = TaskEvent.from_dict(payload)
                        #執行任務
                        self.task_cooridinaor.execute(task_event)
                        
                except Exception as e:
                    if task_id!="":
                        logging.error(f"[Worker] 任務 {task_id} 發生例外: {e}")
                    logging.error("[Worker] 任務解析訊息失敗")
                finally:
                    # 單筆處理完畢，無論成功失敗，ack此訊息，並將此 ack_id 從 pending 清單移除
                    self.subscriber.acknowledge(
                            request={"subscription": self.subscription_path, "ack_ids": [msg.ack_id]}
                        )
                    pending_ack_ids.remove(msg.ack_id)

            # 攔截關閉訊號的 Active NACK 處理 (對剩餘未處理訊息全部發送 NACK)
            if pending_ack_ids:
                logging.info(f"[Shutdown] 主動退回 {len(pending_ack_ids)} 筆未處理的任務...")
                self.subscriber.modify_ack_deadline(
                    request={
                        "subscription": self.subscription_path,
                        "ack_ids": pending_ack_ids,
                        "ack_deadline_seconds": 0
                    }
                )

        logging.info("[Shutdown] Worker 優雅退出 (Exit 0)")

    def db_claim_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.db_dao.db_claim_task(task_id)


