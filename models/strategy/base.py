from abc import ABC, abstractmethod
import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from pydantic import Field
from models.basemodel import BaseModelWithConfig

class Direction(int, Enum):
    UP = 1
    DOWN = -1
    NONE = 0
    
class TradeAction(int, Enum):
    BUY = 1
    SELL = -1
    NONE = 0

class TechnicalIndicator(int, Enum):
    RSI_LIMIT = 50


class Candle(str, Enum):
    CandleD1 = "d1"

class BackTestResultFileType(str, Enum):
    TestDF = "test_df"
    TreadeRES = "trade_res"


class TPSLParms(BaseModelWithConfig):
    profit_factor: float = Field(..., description="獲利因子")
    loss_factor: float = Field(..., description="損失因子")

class TPSL(BaseModelWithConfig):
    tp: str = Field(..., alias="TP", description="止盈設定")
    sl: str = Field(..., alias="SL", description="止損設定")
    
class SaverParams(BaseModelWithConfig):
    saver_name: str = Field(..., description="存儲器名稱") # 通用於SinkParams.Location
    saver_base_path: Optional[str] = None

class SourceMetaData(BaseModelWithConfig):
    """ todo start time, end time要根據candle轉換日期格式
    """
    code: Optional[str]
    candle: Optional[str]
    start_time: Optional[datetime.datetime] = Field(default=None, description="整體資料開始時間，此時間有可能是經過策略延長的資料時間，並非使用者真實的測試範圍")
    end_time: Optional[datetime.datetime] = Field(default=None, description="整體資料結束時間")
    true_start_time: Optional[datetime.datetime] = Field(default=None, description="真實的資料開始時間，使用者真實的測試起始時間")
    window_size: Optional[int] = Field(default=None, description="策略需要的資料窗口大小，單位為天數")

    def as_dict(self, date_format='%Y-%m-%d') -> dict:
        return {
            'code': self.code if self.code else None,
            'candle': self.candle if self.candle else None,
            'start_time': self.start_time.strftime(date_format) if self.start_time else None,
            'end_time': self.end_time.strftime(date_format) if self.end_time else None,
            'true_start_time': self.true_start_time.strftime(date_format) if self.true_start_time else None,
            'window_size': self.window_size if self.window_size is not None else None
        }
