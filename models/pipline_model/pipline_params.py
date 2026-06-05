from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
from infra.repo.minio_dao import MinioConfig
from models.basemodel import BaseModelWithConfig
from pydantic import Field, field_validator

class SinkLocationType(str, Enum):
    LOCAL = "local"
    MINIO = "minio"


class SinkParams(BaseModelWithConfig):
    location: SinkLocationType = Field(..., description="儲存位置類型")
    path: Optional[str] = Field(None, description="儲存路徑，minio時為bucket名稱")
    minio_config: Optional[MinioConfig] = Field(None, description="MinIO 配置")

    @field_validator('location')
    def validate_location(cls, v):
        if isinstance(v, str):
            try:
                return SinkLocationType(v.lower())
            except ValueError:
                raise ValueError(f"Invalid location type. Must be one of {[e.value for e in SinkLocationType]}")
        return v

@dataclass
class PiplineParams:
    sinkParams :SinkParams
    setParams: Dict[str, str]
    
    
    def as_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "sink_params" : self.sinkParams.as_dict(),
            "set_params" : self.setParams
        }


