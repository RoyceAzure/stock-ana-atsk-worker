from datetime import datetime
from pydantic import BaseModel, ConfigDict

class BaseModelWithConfig(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # 允許使用別名
        validate_assignment=True,  # 賦值時進行驗證
        extra='forbid',  # 禁止額外字段
        arbitrary_types_allowed=True,  # 允許任意類型
        json_encoders={  # 添加常用類型的 JSON 編碼器
            datetime: lambda v: v.isoformat(),
            bytes: lambda v: v.decode('utf-8')
        }
    )

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