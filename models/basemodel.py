from typing import Any

from pydantic import BaseModel, ConfigDict, model_serializer


def _decode_bytes_recursive(obj: Any) -> Any:
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    if isinstance(obj, dict):
        return {k: _decode_bytes_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode_bytes_recursive(v) for v in obj]
    return obj


class BaseModelWithConfig(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # 允許使用別名
        validate_assignment=True,  # 賦值時進行驗證
        extra='forbid',  # 禁止額外字段
        arbitrary_types_allowed=True,  # 允許任意類型
    )

    @model_serializer(mode="wrap", when_used="json")
    def _serialize_for_json(self, handler):
        return _decode_bytes_recursive(handler(self))

    def as_dict(self, exclude_none: bool = True):
        """
        轉換為字典，增加選項控制
        :param exclude_none: 是否排除 None 值
        """
        return self.model_dump(exclude_none=exclude_none)

    def as_json(self, exclude_none: bool = True):
        """
        轉換為 JSON 字串
        :param exclude_none: 是否排除 None 值
        """
        return self.model_dump_json(exclude_none=exclude_none)

    @classmethod
    def from_dict(cls, data: dict):
        """
        從字典創建實例
        """
        return cls(**data)