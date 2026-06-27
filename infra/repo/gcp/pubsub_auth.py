from __future__ import annotations

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Optional

from google.cloud import pubsub_v1
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

_VALID_AUTH_MODES = frozenset({"adc", "service_account_json"})


class PubSubAuthMode(str, Enum):
    """Pub/Sub 憑證模式。"""

    ADC = "adc"
    SERVICE_ACCOUNT_JSON = "service_account_json"


def resolve_pubsub_auth_mode(raw: Optional[str] = None) -> PubSubAuthMode:
    mode = (raw or os.getenv("GCP_PUBSUB_AUTH_MODE", "adc")).strip().lower()
    if mode not in _VALID_AUTH_MODES:
        raise ValueError(
            f"GCP_PUBSUB_AUTH_MODE 不支援: {mode!r}（允許: adc, service_account_json）"
        )
    return PubSubAuthMode(mode)


def resolve_service_account_key_file() -> str:
    key_file = (
        os.getenv("GCP_SA_KEY_FILE", "").strip()
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )
    if not key_file:
        raise ValueError(
            "Pub/Sub service_account_json 模式需設定 GCP_SA_KEY_FILE "
            "或 GOOGLE_APPLICATION_CREDENTIALS（指向 SA JSON 檔路徑）"
        )
    path = Path(key_file)
    if not path.is_file():
        raise FileNotFoundError(f"Pub/Sub SA key 檔不存在: {key_file}")
    return str(path)


def pubsub_auth_mode_from_env() -> PubSubAuthMode:
    return resolve_pubsub_auth_mode()


def pubsub_service_account_key_file_from_env() -> Optional[str]:
    mode = pubsub_auth_mode_from_env()
    if mode is PubSubAuthMode.ADC:
        return None
    return resolve_service_account_key_file()


def create_subscriber_client(
    *,
    auth_mode: PubSubAuthMode = PubSubAuthMode.ADC,
    service_account_key_file: Optional[str] = None,
) -> pubsub_v1.SubscriberClient:
    """建立 Pub/Sub SubscriberClient。

    - adc: Workload Identity / gcloud ADC（不傳 credentials）
    - service_account_json: 使用 SA JSON 金鑰檔（kind / 本機 K8s）
    """
    if auth_mode is PubSubAuthMode.ADC:
        logger.info("[Pub/Sub] 憑證模式: ADC（Workload Identity / 預設應用程式憑證）")
        return pubsub_v1.SubscriberClient()

    key_file = service_account_key_file or resolve_service_account_key_file()
    logger.info("[Pub/Sub] 憑證模式: service_account_json (%s)", key_file)
    credentials = service_account.Credentials.from_service_account_file(key_file)
    return pubsub_v1.SubscriberClient(credentials=credentials)
