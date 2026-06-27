from __future__ import annotations

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from google.auth import credentials as google_credentials
from google.auth import default as google_auth_default
from google.auth.transport import requests as google_auth_requests
from google.cloud import pubsub_v1
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

_VALID_AUTH_MODES = frozenset({"adc", "service_account_json"})


class GcpAuthMode(str, Enum):
    """GCP API 憑證模式（Pub/Sub、gcsfs 共用）。"""

    ADC = "adc"
    SERVICE_ACCOUNT_JSON = "service_account_json"


# 向後相容舊名稱
PubSubAuthMode = GcpAuthMode


def _auth_mode_env_raw() -> str:
    return (
        os.getenv("GCP_AUTH_MODE", "").strip()
        or os.getenv("GCP_PUBSUB_AUTH_MODE", "adc").strip()
    )


def resolve_gcp_auth_mode(raw: Optional[str] = None) -> GcpAuthMode:
    mode = (raw or _auth_mode_env_raw()).lower()
    if mode not in _VALID_AUTH_MODES:
        raise ValueError(
            f"GCP_AUTH_MODE 不支援: {mode!r}（允許: adc, service_account_json）"
        )
    return GcpAuthMode(mode)


def resolve_service_account_key_file() -> str:
    key_file = (
        os.getenv("GCP_SA_KEY_FILE", "").strip()
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )
    if not key_file:
        raise ValueError(
            "service_account_json 模式需設定 GCP_SA_KEY_FILE "
            "或 GOOGLE_APPLICATION_CREDENTIALS（指向 SA JSON 檔路徑）"
        )
    path = Path(key_file)
    if not path.is_file():
        raise FileNotFoundError(f"GCP SA key 檔不存在: {key_file}")
    return str(path)


def gcp_auth_mode_from_env() -> GcpAuthMode:
    return resolve_gcp_auth_mode()


def gcp_service_account_key_file_from_env() -> Optional[str]:
    if gcp_auth_mode_from_env() is GcpAuthMode.ADC:
        return None
    return resolve_service_account_key_file()


def load_gcp_credentials(
    *,
    auth_mode: GcpAuthMode = GcpAuthMode.ADC,
    service_account_key_file: Optional[str] = None,
) -> Optional[service_account.Credentials]:
    if auth_mode is GcpAuthMode.ADC:
        return None
    key_file = service_account_key_file or resolve_service_account_key_file()
    return service_account.Credentials.from_service_account_file(key_file)


def resolve_google_credentials(
    *,
    auth_mode: GcpAuthMode = GcpAuthMode.ADC,
    service_account_key_file: Optional[str] = None,
) -> google_credentials.Credentials:
    """取得可 refresh 的 Google Credentials（ADC 或 SA JSON）。"""
    credentials = load_gcp_credentials(
        auth_mode=auth_mode,
        service_account_key_file=service_account_key_file,
    )
    if credentials is not None:
        return credentials

    credentials, _ = google_auth_default()
    return credentials


def refresh_gcp_access_token(
    *,
    auth_mode: GcpAuthMode = GcpAuthMode.ADC,
    service_account_key_file: Optional[str] = None,
) -> str:
    """取得 GCP OAuth2 access token（DuckDB GCS bearer secret 用）。"""
    credentials = resolve_google_credentials(
        auth_mode=auth_mode,
        service_account_key_file=service_account_key_file,
    )
    credentials.refresh(google_auth_requests.Request())
    token = credentials.token
    if not token:
        raise ValueError("無法取得 GCP access token")
    return token


def create_subscriber_client(
    *,
    auth_mode: GcpAuthMode = GcpAuthMode.ADC,
    service_account_key_file: Optional[str] = None,
) -> pubsub_v1.SubscriberClient:
    """建立 Pub/Sub SubscriberClient（ADC 或 SA JSON）。"""
    credentials = load_gcp_credentials(
        auth_mode=auth_mode,
        service_account_key_file=service_account_key_file,
    )
    if credentials is None:
        logger.info("[Pub/Sub] 憑證模式: ADC（Workload Identity / 預設應用程式憑證）")
        return pubsub_v1.SubscriberClient()

    key_file = service_account_key_file or resolve_service_account_key_file()
    logger.info("[Pub/Sub] 憑證模式: service_account_json (%s)", key_file)
    return pubsub_v1.SubscriberClient(credentials=credentials)


def create_gcs_filesystem(
    *,
    auth_mode: GcpAuthMode = GcpAuthMode.ADC,
    service_account_key_file: Optional[str] = None,
) -> Any:
    """建立 gcsfs 檔案系統（ADC 或 SA JSON）。"""
    import gcsfs

    credentials = load_gcp_credentials(
        auth_mode=auth_mode,
        service_account_key_file=service_account_key_file,
    )
    if credentials is None:
        logger.info("[GCS] 憑證模式: ADC（Workload Identity / 預設應用程式憑證）")
        return gcsfs.GCSFileSystem()

    key_file = service_account_key_file or resolve_service_account_key_file()
    logger.info("[GCS] 憑證模式: service_account_json (%s)", key_file)
    return gcsfs.GCSFileSystem(token=credentials)


# 向後相容
resolve_pubsub_auth_mode = resolve_gcp_auth_mode
pubsub_auth_mode_from_env = gcp_auth_mode_from_env
pubsub_service_account_key_file_from_env = gcp_service_account_key_file_from_env
