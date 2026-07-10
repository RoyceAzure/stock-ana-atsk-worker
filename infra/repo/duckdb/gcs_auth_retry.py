from __future__ import annotations

import logging
from typing import Callable, TypeVar

import duckdb

from infra.repo.duckdb_manager import DuckDBManager

logger = logging.getLogger(__name__)

T = TypeVar("T")

_GCS_AUTH_ERROR_KEYWORDS = (
    "unauthorized",
    "401",
    "403",
    "authentication",
    "access token",
    "invalid credentials",
    "permission denied",
)


def is_gcs_auth_error(exc: BaseException) -> bool:
    """判斷 DuckDB httpfs 錯誤是否可能為 GCS 憑證過期。"""
    msg = str(exc).lower()
    return any(keyword in msg for keyword in _GCS_AUTH_ERROR_KEYWORDS)


def with_gcs_auth_retry(
    conn: duckdb.DuckDBPyConnection,
    operation: Callable[[], T],
) -> T:
    """執行 operation；若為 GCS auth 錯誤則 refresh token 後重試一次。"""
    try:
        return operation()
    except Exception as exc:
        if not is_gcs_auth_error(exc):
            raise
        logger.warning("[DuckDB GCS] auth 失敗，refresh token 後重試一次: %s", exc)
        DuckDBManager.refresh_gcs_auth(conn)
        return operation()
