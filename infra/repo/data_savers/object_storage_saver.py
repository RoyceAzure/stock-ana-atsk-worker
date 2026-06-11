import json
import logging
from typing import Any, BinaryIO, Optional, Tuple, Union

from pandas import DataFrame

from infra.repo.object_storage import (
    ObjectStorageConfig,
    create_filesystem,
    to_fs_uri,
)
from .base import DataSaver

logger = logging.getLogger(__name__)


class ObjectStorageSaver(DataSaver):
    """物件儲存數據保存器（支援 S3 / MinIO / GCS）。"""

    def __init__(self, config: ObjectStorageConfig):
        self.config = config
        self.saver_type = config.backend.value
        self.fs = create_filesystem(config)

    def _object_uri(self, full_path: str) -> str:
        return to_fs_uri(self.config, full_path)

    def save_file(
        self,
        full_path: str,
        data: Union[BinaryIO, bytes, DataFrame],
        is_trade_result: bool = False,
    ) -> Tuple[Optional[Any], Optional[str]]:
        try:
            if isinstance(data, DataFrame):
                if data.empty and is_trade_result:
                    data = DataFrame(columns=DataSaver.trade_result_default_column)
                payload = data.to_csv(index=False).encode("utf-8")
            elif isinstance(data, bytes):
                payload = data
            elif hasattr(data, "read"):
                payload = data.read()
            else:
                return None, f"Unsupported data type: {type(data)}"

            if not payload:
                return None, "Buffer is empty"

            with self.fs.open(self._object_uri(full_path), "wb") as f:
                f.write(payload)

            return True, None
        except Exception as e:
            logger.error("save_file failed for %s: %s", full_path, e)
            return None, str(e)

    def as_dict(self) -> dict:
        return {
            "saver_name": self.__class__.__name__,
            "backend": self.config.backend.value,
        }

    def append_to_file(self, full_path: str, data: dict) -> Tuple[Optional[Any], Optional[str]]:
        try:
            object_uri = self._object_uri(full_path)
            existing_data = {}
            if self.fs.exists(object_uri):
                with self.fs.open(object_uri, "rb") as f:
                    existing_data = json.loads(f.read().decode("utf-8"))

            existing_data.update(data)
            json_bytes = json.dumps(existing_data, indent=2).encode("utf-8")

            with self.fs.open(object_uri, "wb") as f:
                f.write(json_bytes)

            return True, None
        except Exception as e:
            logger.error("append_to_file failed for %s: %s", full_path, e)
            return None, str(e)
