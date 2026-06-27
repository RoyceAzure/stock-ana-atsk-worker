from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field, field_validator, model_validator

from infra.repo.object_storage import ObjectStorageConfig, StorageBackend, location_to_backend
from models.basemodel import BaseModelWithConfig


class SinkLocationType(str, Enum):
    LOCAL = "local"
    GCS = "gcs"


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

    @model_validator(mode="after")
    def resolve_storage_config(self):
        if self.storage_config is not None:
            return self
        if self.location is SinkLocationType.GCS:
            self.storage_config = ObjectStorageConfig.from_env(
                location_to_backend(self.location.value)
            )
        return self

    def resolved_storage_config(self) -> ObjectStorageConfig:
        if self.storage_config is not None:
            return self.storage_config
        if self.location is SinkLocationType.GCS:
            return ObjectStorageConfig.from_env(location_to_backend(self.location.value))
        raise ValueError(f"Missing storage config for location: {self.location.value}")
