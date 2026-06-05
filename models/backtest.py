from typing import Any, Dict, NamedTuple, Optional
from pydantic import Field
from models.basemodel import BaseModelWithConfig
from models.scheduler_config import TriggerType
from models.strategy.base import SaverParams, SourceMetaData, StrategyParms, TPSLParms

class Summary(BaseModelWithConfig):
    total_return: str
    total_return_rate: str

class FileInfo(BaseModelWithConfig):
    file_key: str
    trade_res: str
    test_df: str
    trade_chart: str
    final_report: str

class BackTestResult(BaseModelWithConfig):
    strategy_parms: StrategyParms
    tester_params: Dict[str, Any]
    summary: Summary
    file: FileInfo
    completed_at: str
    
class BackTestTask(BaseModelWithConfig):
    tester_name: str = Field(..., description="測試器名稱")
    tester_params: Dict[str, Any] = Field(..., description="測試器參數")
    data_provider_name: str = Field(..., description="數據提供者名稱")
    source_meta_data: SourceMetaData = Field(..., description="源數據信息")
    tpsl_name: str = Field(..., description="止盈止損名稱")
    tpsl_params: TPSLParms = Field(..., description="止盈止損參數")
    saver_params: Optional[SaverParams] = None
    use_process_pool: bool = Field(..., description="是否使用進程池")
    notify_record: Optional[bool] = Field(default=False, description="是否通知紀錄")
    trigger_type: TriggerType = Field(..., description="觸發類型")
    triggered_by: str = Field(default="", description="觸發者")
    
class FilePaths(NamedTuple):
   file_key: str
   trade_res: str
   test_df: str
   trade_chart: str
   final_report :str
   
   def as_dict(self):
        return self._asdict()