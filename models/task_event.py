import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import Field
from models.basemodel import BaseModelWithConfig
from models.strategy.base import SourceMetaData, TPSLParms
from models.pipline_model.pipline_params import SinkParams
from models.scheduler_config import TriggerType
from models.strategy.base import SaverParams


class TaskEventStatus(Enum):
	TaskStatusPending    = "pending"
	TaskStatusRunning    = "running"
	TaskStatusCompleted  = "completed"
	TaskStatusFailed     = "failed"
 
class EventStage(Enum):
    INIT_STAGE    = "init"
    RAW_STAGE    = "download_raw_data"
    PRE_STAGE  = "preprocessing"
    BACKTEST_STAGE     = "backtesting"
    BUY_SELL_MARK_STAGE = "buy_sell_mark"
    SIMILARITY_STAGE = "similarity"

class EventName(Enum):
    PREPROCESS    = "preprocessing"
    BACKTEST    = "backtesting"
    FULLBACKTEST  = "full_backtest"
    BUY_SELL_MARK  = "buy_sell_mark"
    SIMILARITY = "similarity"
 
 
class TaskEvent(BaseModelWithConfig):
    """
    所有任務通用模型
    """    
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    status: TaskEventStatus
    tester_name: Optional[str]= Field(default="", description="測試器名稱")
    tester_params: Optional[Dict[str, Any]] = Field(default=None, description="測試器參數, 每個tester需要的參數不相同, 若非backtest task, ")
    data_provider_name: Optional[str]= Field(default="", description="數據提供者名稱") 
    source_meta_data: SourceMetaData
    tpsl_name: Optional[str] = Field(default = "", description="止盈止損名稱")
    tpsl_params: Optional[TPSLParms] = Field(default=None, description="止盈止損參數")
    saver_params : SaverParams
    trigger_type: TriggerType
    triggered_by: str
    event_name: str
    event_stage : str
    used_process_pool : bool = Field(default=False, description="是否使用進程池")
    
    
    
    schedule_id: Optional[str] = Field(default="")
    schedule_name: Optional[str] = Field(default="")
    start_time: Optional[datetime.datetime]= Field(default=None)
    end_time: Optional[datetime.datetime] = Field(default=None)
    error_message:  Optional[str] = Field(default="")
    
    #for preprocess task
    sink_params :Optional[SinkParams]= Field(default=None)
    set_params: Optional[Dict[str, str]]= Field(default=None)

    #for notified
    is_notify: bool = Field(..., description="是否通知紀錄")
    
    def as_dict(self):
        return self.model_dump()
    
    
class UpdateTaskEventParams(BaseModelWithConfig):
    """
    for update task event
    """    
    id: uuid.UUID
    updated_at: Optional[datetime.datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    event_stage : Optional[str] = Field(default=None)
    error_message:  Optional[str] = Field(default=None)
    
    
    def as_dict(self):
        return self.model_dump()