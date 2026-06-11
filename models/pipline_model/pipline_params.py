from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field, field_validator, model_validator

from infra.repo.object_storage import ObjectStorageConfig, StorageBackend, location_to_backend
from models.basemodel import BaseModelWithConfig


class SinkLocationType(str, Enum):
    LOCAL = "local"
    MINIO = "minio"
    S3 = "s3"
    GCS = "gcs"


def _minio_dict_to_storage_config(data: Dict[str, Any]) -> ObjectStorageConfig:
    return ObjectStorageConfig(
        backend=StorageBackend.MINIO,
        access_key=data.get("access_key"),
        secret_key=data.get("secret_key"),
        region=data.get("region"),
        host=data.get("host"),
        port=int(data["port"]) if data.get("port") is not None else None,
    )


class SinkParams(BaseModelWithConfig):
    location: SinkLocationType = Field(..., description="儲存位置類型")
    path: Optional[str] = Field(None, description="儲存路徑，物件儲存時為 bucket 名稱")
    storage_config: Optional[ObjectStorageConfig] = Field(None, description="物件儲存配置")

    @field_validator("location")
    def validate_location(cls, v):
        if isinstance(v, str):
            try:
                return SinkLocationType(v.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid location type. Must be one of {[e.value for e in SinkLocationType]}"
                )
        return v

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_minio_config(cls, data: Any):
        if not isinstance(data, dict):
            return data
        if data.get("storage_config") is not None:
            data.pop("minio_config", None)
            return data
        legacy = data.pop("minio_config", None)
        if legacy is None:
            return data
        if isinstance(legacy, ObjectStorageConfig):
            data["storage_config"] = legacy
        elif isinstance(legacy, dict):
            data["storage_config"] = _minio_dict_to_storage_config(legacy)
        return data

    @model_validator(mode="after")
    def resolve_storage_config(self):
        if self.storage_config is not None:
            return self
        if self.location in {
            SinkLocationType.MINIO,
            SinkLocationType.S3,
            SinkLocationType.GCS,
        }:
            self.storage_config = ObjectStorageConfig.from_env(
                location_to_backend(self.location.value)
            )
        return self

    def resolved_storage_config(self) -> ObjectStorageConfig:
        if self.storage_config is not None:
            return self.storage_config
        if self.location in {
            SinkLocationType.MINIO,
            SinkLocationType.S3,
            SinkLocationType.GCS,
        }:
            return ObjectStorageConfig.from_env(location_to_backend(self.location.value))
        raise ValueError(f"Missing storage config for location: {self.location.value}")


@dataclass
class PiplineParams:
    sinkParams: SinkParams
    setParams: Dict[str, str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "sink_params": self.sinkParams.as_dict(),
            "set_params": self.setParams,
        }
