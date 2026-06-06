from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import Field, Json
from models.basemodel import BaseModelWithConfig

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
    completed_at: datetime = Field(..., description="回測完成時間")
    created_at: datetime = Field(..., description="資料建立時間")
    updated_at: datetime = Field(..., description="資料最後更新時間")
    
    
class TestResultUpsertParams(BaseModelWithConfig):
    key_string: str = Field(..., description="原始的 Key 字串，用於快速查找特定回測結果")
    strategy_parms: Json[Dict[str, Any]] = Field(..., description="策略參數 JSON 區塊，包含策略的相關設定")
    tester_params: Json[Dict[str, Any]] = Field(..., description="測試器參數 JSON 區塊，包含回測測試器的相關設定")
    summary: Json[Dict[str, Any]] = Field(..., description="回測結果摘要 JSON 區塊，包含回測的總體績效指標")
    file: Json[Dict[str, Any]] = Field(..., description="檔案資訊 JSON 區塊，包含回測結果相關檔案的路徑")
    completed_at: datetime = Field(..., description="回測完成時間")
    updated_at: datetime = Field(..., description="資料最後更新時間")
    task_event_id: uuid.UUID = Field(..., description="執行此任務的task event id")