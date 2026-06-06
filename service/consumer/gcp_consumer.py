import time
import logging
from core.life_cycle.lifecycle import shutdown_event
from google.cloud import pubsub_v1
from google.api_core import retry
from google.api_core.exceptions import DeadlineExceeded

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


class IMessageConsumer(Protocol):
    """消息消費者
    
    負責監聽消息對列，並執行任務
    """
    def consume(self) -> None:
        ...




class GCPMessageConsumer(IMessageConsumer):
    """GCP 消息消費者
    
    負責監聽 GCP 消息對列，並執行任務
    """
    def __init__(self, project_id: str, subscription_id: str):
        self.project_id = project_id
        self.subscription_id = subscription_id

    def consume(self) -> None:
        ...




def start_consumer(project_id: str, subscription_id: str, batch_size: int = 100):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    logging.info(f"[Worker] 啟動，開始監聽 {subscription_path}")

    # Loop: is_running == True?
    while not shutdown_event.is_set():
        try:
            # 依 Flow Control 限制批次拉取訊息
            response = subscriber.pull(
                request={
                    "subscription": subscription_path,
                    "max_messages": batch_size,
                },
                timeout=5.0, # 控制無訊息時的阻塞時間
                retry=retry.Retry(deadline=30)
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

            task_id = msg.message.data.decode("utf-8")
            
            try:
                # 1. 執行 DB UPDATE RETURNING (原子性 Claim)
                payload = db_claim_task(task_id)
                
                if not payload:
                    # Claim 失敗 (已被領走) -> 發送 ACK (丟棄)
                    subscriber.acknowledge(
                        request={"subscription": subscription_path, "ack_ids": [msg.ack_id]}
                    )
                else:
                    # Claim 成功 -> 2. 撈取 Raw Data 3. 執行 Data Merge
                    process_task(payload)
                    
                    # 處理成功 -> 更新 DB 狀態並發送 ACK
                    db_update_task_completed(task_id)
                    subscriber.acknowledge(
                        request={"subscription": subscription_path, "ack_ids": [msg.ack_id]}
                    )
                    
            except Exception as e:
                logging.error(f"[Worker] 任務 {task_id} 發生例外: {e}")
                # 處理失敗 -> 發送 NACK (退回佇列)
                # GCP Pub/Sub 的 NACK 實作方式是將 Ack Deadline 設為 0
                subscriber.modify_ack_deadline(
                    request={
                        "subscription": subscription_path,
                        "ack_ids": [msg.ack_id],
                        "ack_deadline_seconds": 0
                    }
                )
            finally:
                # 單筆處理完畢，無論成功失敗，將此 ack_id 從 pending 清單移除
                pending_ack_ids.remove(msg.ack_id)

        # 攔截關閉訊號的 Active NACK 處理 (對剩餘未處理訊息全部發送 NACK)
        if pending_ack_ids:
            logging.info(f"[Shutdown] 主動退回 {len(pending_ack_ids)} 筆未處理的任務...")
            subscriber.modify_ack_deadline(
                request={
                    "subscription": subscription_path,
                    "ack_ids": pending_ack_ids,
                    "ack_deadline_seconds": 0
                }
            )

    logging.info("[Shutdown] Worker 優雅退出 (Exit 0)")

# ==========================================
# 以下為抽象的 DB 與邏輯處理函式
# ==========================================
def db_claim_task(task_id: str) -> dict:
    """
    實作: UPDATE task_metadata SET status='RUNNING' WHERE id=X AND status='PENDING' RETURNING payload
    回傳 payload dict，若已被領走則回傳 None
    """
    return {"code": ["1103", "1104"], "query_mode": 2} # Mock

def process_task(payload: dict):
    """
    實作: 根據 payload 撈取當日 Raw Data，執行不重複增量合併
    """
    pass # Mock

def db_update_task_completed(task_id: str):
    """
    實作: UPDATE task_metadata SET status='COMPLETED' WHERE id=X
    """
    pass # Mock

if __name__ == "__main__":
    # 填入你的 GCP 專案與 Subscription 設定
    # start_consumer("my-gcp-project", "my-subscription", batch_size=100)
    pass