import json
import logging
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional, Protocol

from google.api_core import retry
from google.api_core.exceptions import DeadlineExceeded
from google.cloud import pubsub_v1
from pydantic import BaseModel, Field, ValidationError

from core.life_cycle.lifecycle import shutdown_event
from infra.repo.gcp.gcp_auth import GcpAuthMode, create_subscriber_client
from models.task_event import EventStage, TaskEvent, TaskEventStatus
from models.task_message import TaskMessage
from service.task.task_coordinator import ITaskCoordinator
from service.taskevent.helper import TaskEventHelper

logger = logging.getLogger(__name__)


class PubSubConsumerConfig(BaseModel):
    project_id: str = Field(..., description="GCP 專案 ID")
    subscription_id: str = Field(..., description="訂閱通道 (Subscription) ID")
    batch_size: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="單次拉取的最大訊息數量 (對應 max_messages)",
    )
    visibility_timeout: int = Field(
        default=30,
        ge=10,
        le=600,
        description="訊息隱藏/處理時間 (Ack Deadline)，單位為秒。逾時未 ACK 則重派",
    )
    pull_timeout: float = Field(
        default=5.0,
        ge=0.0,
        description="同步拉取 (pull) 時，若無訊息的等待超時時間，單位為秒",
    )
    shutdown_drain_timeout: float = Field(
        default=30.0,
        ge=0.0,
        description="關閉時等待進行中任務完成的逾時秒數",
    )
    auth_mode: GcpAuthMode = Field(
        default=GcpAuthMode.ADC,
        description="adc=Workload Identity / ADC；service_account_json=SA JSON 金鑰檔",
    )
    service_account_key_file: Optional[str] = Field(
        default=None,
        description="SA JSON 路徑（auth_mode=service_account_json 時必填）",
    )


class IMessageConsumer(Protocol):
    """消息消費者：負責監聽消息對列並執行任務。"""

    def start(self) -> None:
        ...

    def close(self, timeout: float = 30.0) -> None:
        """停止拉取、等待進行中任務結束，並釋放資源。"""
        ...


class ITaskClaimDao(Protocol):
    def db_claim_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        ...


class GCPMessageConsumer(IMessageConsumer):
    """GCP 消息消費者。"""

    def __init__(
        self,
        config: PubSubConsumerConfig,
        task_cooridinaor: ITaskCoordinator,
        task_event_helper: TaskEventHelper,
        db_dao: ITaskClaimDao,
    ):
        self.config = config
        self.task_cooridinaor = task_cooridinaor
        self.task_event_helper = task_event_helper
        self.db_dao = db_dao
        self._in_flight = 0
        self._in_flight_lock = threading.Lock()
        self._closed = False
        self._init_consumer()

    def _init_consumer(self) -> None:
        self.subscriber = create_subscriber_client(
            auth_mode=self.config.auth_mode,
            service_account_key_file=self.config.service_account_key_file,
        )
        self.subscription_path = self.subscriber.subscription_path(
            self.config.project_id,
            self.config.subscription_id,
        )

    def start(self) -> None:
        logger.info("[Worker] 啟動，開始監聽 %s", self.subscription_path)
        try:
            while not shutdown_event.is_set():
                try:
                    response = self.subscriber.pull(
                        request={
                            "subscription": self.subscription_path,
                            "max_messages": self.config.batch_size,
                        },
                        timeout=self.config.pull_timeout,
                        retry=retry.Retry(deadline=self.config.visibility_timeout),
                    )
                except DeadlineExceeded:
                    continue
                except Exception as exc:
                    logger.error("[Worker] 拉取訊息發生錯誤: %s", exc)
                    time.sleep(1)
                    continue

                messages = response.received_messages
                if not messages:
                    continue

                logger.info("[Worker] 成功拉取 %s 筆任務", len(messages))
                pending_ack_ids = [msg.ack_id for msg in messages]

                for msg in messages:
                    if shutdown_event.is_set():
                        logger.warning(
                            "[Worker] 收到關閉訊號，停止處理本批次剩餘訊息"
                        )
                        break
                    logger.info("[Worker] 開始處理任務 %s", msg.message.data)
                    self._process_message(msg, pending_ack_ids)

                if pending_ack_ids:
                    logger.info(
                        "[Shutdown] 主動退回 %s 筆未處理的任務...",
                        len(pending_ack_ids),
                    )
                    self.subscriber.modify_ack_deadline(
                        request={
                            "subscription": self.subscription_path,
                            "ack_ids": pending_ack_ids,
                            "ack_deadline_seconds": 0,
                        }
                    )
        finally:
            self.close(timeout=self.config.shutdown_drain_timeout)

        logger.info("[Shutdown] Worker 優雅退出")

    def close(self, timeout: float = 30.0) -> None:
        if self._closed:
            return

        drained = self._wait_for_drain(timeout)
        if not drained:
            with self._in_flight_lock:
                remaining = self._in_flight
            logger.warning(
                "[Worker] 關閉逾時，仍有 %s 個任務未完成",
                remaining,
            )

        subscriber = getattr(self, "subscriber", None)
        if subscriber is not None:
            try:
                subscriber.close()
                logger.info("[Worker] Pub/Sub Subscriber 客戶端已關閉")
            except Exception as exc:
                logger.warning("[Worker] 關閉 Pub/Sub Subscriber 失敗: %s", exc)
            finally:
                self.subscriber = None

        self._closed = True

    def _ack_message(self, ack_id: str) -> None:
        self.subscriber.acknowledge(
            request={
                "subscription": self.subscription_path,
                "ack_ids": [ack_id],
            }
        )

    def _parse_task_message(self, raw_data: bytes) -> TaskMessage:
        raw = raw_data.decode("utf-8")
        payload = json.loads(raw)
        return TaskMessage.model_validate(payload)

    def _prepare_task_event(self, msg) -> Optional[TaskEvent]:
        """解析 JSON 訊息、驗證 task_id、claim DB 並組裝 TaskEvent。失敗時回傳 None。"""
        task_id = ""
        try:
            task_message = self._parse_task_message(msg.message.data)
            task_id = str(task_message.task_id)
        except UnicodeDecodeError as exc:
            logger.error("[Worker] 任務解析訊息失敗: %s", exc)
            return None
        except json.JSONDecodeError as exc:
            logger.error("[Worker] 任務訊息非有效 JSON: %s", exc)
            return None
        except ValidationError as exc:
            logger.error("[Worker] 任務訊息格式無效: %s", exc)
            return None

        try:
            payload = self.db_claim_task(task_id)
            if not payload:
                logger.warning("[Worker] 任務 %s 不存在或無法 claim", task_id)
                self.task_event_helper.update_task_event(
                    task_id,
                    TaskEventStatus.TaskStatusFailed,
                    EventStage.CLAIM_STAGE,
                    "Task not found",
                )
                return None
            return TaskEvent.from_dict(payload)
        except Exception as exc:
            logger.error("[Worker] 任務 %s 準備階段失敗: %s", task_id, exc)
            self.task_event_helper.handle_error(
                task_id, EventStage.CLAIM_STAGE, exc
            )
            return None

    def _execute_task_event(self, task_event: TaskEvent) -> None:
        task_id = str(task_event.id)
        try:
            with self._track_in_flight():
                self.task_cooridinaor.execute(task_event)
        except Exception as exc:
            logger.error("[Worker] 任務 %s 執行失敗: %s", task_id, exc)
            try:
                stage = EventStage(task_event.event_stage)
            except ValueError:
                stage = EventStage.CLAIM_STAGE
            self.task_event_helper.handle_error(task_id, stage, exc)

    def _process_message(self, msg, pending_ack_ids: list[str]) -> None:
        try:
            task_event = self._prepare_task_event(msg)
            if task_event is not None:
                self._execute_task_event(task_event)
        finally:
            self._ack_message(msg.ack_id)
            if msg.ack_id in pending_ack_ids:
                pending_ack_ids.remove(msg.ack_id)

    @contextmanager
    def _track_in_flight(self):
        with self._in_flight_lock:
            self._in_flight += 1
        try:
            yield
        finally:
            with self._in_flight_lock:
                self._in_flight -= 1

    def _wait_for_drain(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._in_flight_lock:
                if self._in_flight == 0:
                    return True
            time.sleep(0.1)

        with self._in_flight_lock:
            return self._in_flight == 0

    def db_claim_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.db_dao.db_claim_task(task_id)
