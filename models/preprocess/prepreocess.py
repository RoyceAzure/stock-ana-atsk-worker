from typing import Any, Dict
import uuid
from pydantic import Field
from models.basemodel import BaseModelWithConfig
from models.pipline_model.pipline_params import SinkParams


class PreProcessTaskModel(BaseModelWithConfig):
    """for preprocess task model
    """
    id : uuid.UUID = Field(..., description="必須提供的 preprocess task id")
    sink_params: SinkParams = Field(..., description="必須提供的 sink 參數")
    set_params: Dict[str, Any] = Field(..., description="必須提供的設定參數")
    
    def as_dict(self):
        return self.model_dump()