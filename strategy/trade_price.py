import datetime
from typing import Any, Dict
from pandas import DataFrame
from pydantic import Field
from models.basemodel import BaseModelWithConfig
from models.strategy.base import DataModel, SourceMetaData


class TradePriceMeta(BaseModelWithConfig):
    """交易價格元數據模型
    
    Attributes:
        code: 交易代碼
        start_time: 開始時間
        end_time: 結束時間
        candle: K線類型
    """
    code: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    candle: str
    true_start_time: datetime.datetime = Field(description="真實的資料開始時間，使用者真實的測試起始時間")
    

class TradePrice(DataModel):
    """Trade price entity with metadata
    
    Args:
        data_df (DataFrame): trade_price entity dataframe
        code (str, optional): stock code
        start_time (str/datetime, optional): start time filter
        end_time (str/datetime, optional): end time filter
        candle (str, optional): candle stick type
        true_start_time (str/datetime, optional): true start time of the data, which may differ from start_time due to strategy scope extension
    """
    def __init__(self, 
                 data_df: DataFrame,
                meta_data: SourceMetaData):
        super().__init__(data_df)   
        self.meta_data = meta_data
    
    def as_dict(self) -> Dict[str, Any]:
        return {
            "rows": len(self.data_df),
        } | self.meta_data.as_dict()