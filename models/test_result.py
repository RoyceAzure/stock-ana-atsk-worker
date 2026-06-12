from enum import Enum
from typing import Any, Dict, Optional, Union
import uuid
from pydantic import Field, Json
from models.basemodel import BaseModelWithConfig
import pandas as pd
import datetime
class CandleIntervalEnum(Enum):
    D1 = "d1"

class SortOrderEnum(Enum):
    ASC ="asc"
    DESC    = "desc"

class GetTestResultsParamsSortEnum(Enum):
    NAME ="name"
    CODE = "code"
    PROFIT = "profit"
    START_TIME = "start_time"
    END_TIME = "end_time"

class TestResult(BaseModelWithConfig):
    """策略測試結果類別，用於封裝策略回測的所有相關資訊。
    
    該類別儲存策略回測的狀態、參數配置、交易記錄以及測試用的數據框架。
    
    Attributes:
        status: 策略執行狀態
        strategy_parms (dict): 策略基本參數，包含策略名稱和止盈止損設置
        tester_params (dict): 測試器的參數配置
        trades_res (pd.DataFrame, optional): 所有交易記錄，包含每筆交易的詳細資訊
        test_df (pd.DataFrame, optional): 回測過程中使用的數據框架
        last_data_signal: 最後一筆資料的交易訊號
    """
    task_id: str = Field(...,description="執行的backtest任務id")
    
    status: bool = Field(
        description="策略執行狀態，True表示成功，False表示失敗"
    )
    
    test_df: Union[pd.DataFrame, Dict[str, Any]] = Field(
        description="回測數據框架或其字典表示"
    )
    
    strategy_parms: Dict[str, Any] = Field(
        description="策略參數配置",
    )
    
    tester_params: Dict[str, Any] = Field(
        description="測試器參數配置"
    )
    
    trades_res: Optional[Union[pd.DataFrame, Dict[str, Any]]] = Field(
        default=None,
        description="交易記錄數據框架或其字典表示"
    )
    
    completed_at: Optional[datetime.datetime] = Field(
        default=None,
        description="完成時間戳"
    )

    last_data_signal: Optional[int] = Field(
        default=0,
        description="最後一筆資料的交易訊號, 1 : BUY, -1 : SELL, 0 : NONE"
    )

    def as_dict(self) -> dict:
        """將測試結果轉換為字典格式。
        
        Returns:
            dict: 包含以下鍵值對的字典：
                - task_id : task id
                - status: 策略執行狀態
                - strategy_name: 策略名稱
                - tester_params: 測試器參數
                - tpsl_parms: 止盈止損參數
                - all_traders: 交易記錄數據框架
                - test_df: 回測數據框架
                - last_data_signal: 最後一筆資料的交易訊號
        """
        return {
            "task_id" : self.task_id,
            "status": self.status,
            "strategy_name": self.strategy_parms["name"],
            "tester_params": self.tester_params,
            "tpsl_parms": self.strategy_parms["tpsl_parms"],
            "trades_res": self.trades_res,
            "test_df": self.test_df,
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M:%S") if self.completed_at else "",
            "last_data_signal": self.last_data_signal
        }

    def get_tester_info(self) -> dict:
        """獲取測試器的基本資訊。
        
        Returns:
            dict: 包含以下鍵值對的字典：
                - status: 策略執行狀態
                - strategy_name: 策略名稱
                - tester_params: 測試器參數
                - tpsl_parms: 止盈止損參數
        """
        return {
            "status": self.status,
            "strategy_name": self.strategy_parms["name"],
            "tester_params": self.tester_params,
            "tpsl_parms": self.strategy_parms["tpsl_parms"],
        }




class GetTestResultsParams(BaseModelWithConfig):
    str_name: Optional[str]= Field(default="", description="策略名稱")
    code: Optional[str]= Field(default="", description="股票代碼")
    candle: Optional[CandleIntervalEnum]= Field(default="", description="標的時間間隔")
    sort_by: Optional[GetTestResultsParamsSortEnum]= Field(default=GetTestResultsParamsSortEnum.NAME, description="排序欄位")
    sort_order: Optional[SortOrderEnum]= Field(default=SortOrderEnum.ASC, description="排序方式")
    page : Optional[int] = Field(default=1, description="分頁頁數")
    page_size : Optional[int] = Field(default=20, description="分頁大小")
    
class TestResultEntity(BaseModelWithConfig):
    id: int = Field(..., description="自動遞增的主鍵，唯一識別回測結果")
    key_string: str = Field(..., description="原始的 Key 字串，用於快速查找特定回測結果")
    strategy_parms: Json[Dict[str, Any]] = Field(..., description="策略參數 JSON 區塊，包含策略的相關設定")
    tester_params: Json[Dict[str, Any]] = Field(..., description="測試器參數 JSON 區塊，包含回測測試器的相關設定")
    summary: Json[Dict[str, Any]] = Field(..., description="回測結果摘要 JSON 區塊，包含回測的總體績效指標")
    file: Json[Dict[str, Any]] = Field(..., description="檔案資訊 JSON 區塊，包含回測結果相關檔案的路徑")
    completed_at: datetime.datetime = Field(..., description="回測完成時間")
    created_at: datetime.datetime = Field(..., description="資料建立時間")
    updated_at: datetime.datetime = Field(..., description="資料最後更新時間")
    
    
class TestResultUpsertParams(BaseModelWithConfig):
    key_string: str = Field(..., description="原始的 Key 字串，用於快速查找特定回測結果")
    strategy_parms: Json[Dict[str, Any]] = Field(..., description="策略參數 JSON 區塊，包含策略的相關設定")
    tester_params: Json[Dict[str, Any]] = Field(..., description="測試器參數 JSON 區塊，包含回測測試器的相關設定")
    summary: Json[Dict[str, Any]] = Field(..., description="回測結果摘要 JSON 區塊，包含回測的總體績效指標")
    file: Json[Dict[str, Any]] = Field(..., description="檔案資訊 JSON 區塊，包含回測結果相關檔案的路徑")
    completed_at: datetime.datetime = Field(..., description="回測完成時間")
    updated_at: datetime.datetime = Field(..., description="資料最後更新時間")
    task_event_id: uuid.UUID = Field(..., description="執行此任務的task event id")