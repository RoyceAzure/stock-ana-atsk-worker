from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, field_validator
from uuid import UUID


class ConsumerResult(str, Enum):
    """消費者處理結果枚舉
    
    用於標識任務處理的結果狀態
    """
    SUCCESSED = "SUCCESSED"
    FAILED = "FAILED"


class TaskResult(BaseModel):
    """任務處理結果模型
    
    用於封裝任務處理的結果信息，包括：
    - 任務ID
    - 處理結果
    - 錯誤信息
    - 額外數據
    """
    id: str  # uuid str, for 序列化傳輸
    is_successed: ConsumerResult
    message: str = ""
    extras: Optional[Dict[str, Any]] = None

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    def to_dict(self):
        """for 序列化"""
        return {
            'is_successed': self.is_successed.value,
            'message': self.message,
            'parms': self.extras
        }


class TaskResultException(Exception):
    """任務結果異常
    
    用於封裝任務執行過程中的異常，包含任務結果信息
    """
    def __init__(self, task_result: TaskResult):
        self.task_result = task_result
        super().__init__(task_result.message) 