from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple

import duckdb

_URI_PREFIXES: Tuple[str, ...] = ("s3://", "gs://", "gcs://")


def strip_uri_scheme(path: str) -> str:
    for prefix in _URI_PREFIXES:
        if path.startswith(prefix):
            return path[len(prefix) :].rstrip("/")
    return path.rstrip("/")


class DuckDBStorageConfig(ABC):
    """DuckDB 物件儲存連線設定（與 fsspec 用的 ObjectStorageConfig 分離）。"""

    @abstractmethod
    def setup_connection(self, con: duckdb.DuckDBPyConnection) -> None:
        """安裝 extension 並建立 SECRET。"""

    @abstractmethod
    def object_uri(self, bucket: str, key: str = "") -> str:
        """組出 DuckDB SQL 可用的物件 URI。"""

    def to_uri(self, path: str) -> str:
        normalized = strip_uri_scheme(path)
        return self.object_uri(*self._split_bucket_key(normalized))

    @staticmethod
    def _split_bucket_key(normalized: str) -> Tuple[str, str]:
        parts = normalized.split("/", 1)
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]
