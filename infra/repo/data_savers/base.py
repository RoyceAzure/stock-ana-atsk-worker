from abc import ABC, abstractmethod
import datetime
import json
from typing import Any, BinaryIO, Dict, List, Tuple, Optional, Union
from pandas import DataFrame
from models.backtest import FilePaths
from models.strategy.base import TestResult
from util.util import util

class DataSaver(ABC):
    trade_result_default_column : List[str] = [
        "start_index","close_index","start_time","end_time", "start_price", "TP","SL", "close_price", "total_return","total_return_rate","status"
        ]
    @abstractmethod
    def save_file(self, full_path: str, data: Union[BinaryIO, bytes, DataFrame], is_trade_result : bool = False):
        """

        """
        pass
    
    @abstractmethod
    def as_dict(self) -> dict:
        """
        Returns:
            dict : 返回DataSaver info
        """
        pass
    
    @abstractmethod
    def append_to_file(self, full_path: str, data: dict) -> Tuple[Optional[Any], Optional[str]]:
        """ used to append exists json file

        Args:
            full_path (str): 儲存路徑
            data (dict): 目前用來處理測試結果的metajson

        Returns:
            Tuple[Optional[Any], Optional[str]]: 返回儲存路徑, 可能得錯誤訊息
        """
        pass
    
def extract_data_model_info(data: TestResult) -> Dict[str,str]:
    """
    提取資料模型資訊
    
    Args:
        data (TestResult): 回測結果資料，包含策略參數和測試結果
        
    Returns:
        Dict[str,str]: 資料模型資訊
    """
    data_model = data.strategy_parms.get("data_model", {})
    
    code = data_model.get("code", "")
    candle = data_model.get("candle", "")
    start_time = data_model.get("start_time", "")
    end_time = data_model.get("end_time", "")
    
    return {
        "code" : code,
        "candle" : candle,
        "start_time" :start_time,
        "end_time" : end_time
    }


def prepare_save_file_key(data: TestResult) -> str:
    """準備儲存檔案的唯一名稱，會補上微秒級時間搓以確保唯一性。
    
    Args:
        data (TestResult): 回測結果資料，包含策略參數和測試結果
        
    Returns:
        str: 儲存檔案的唯一名稱
    """
    key_dict = {
        "name": data.strategy_parms["name"]
    } | extract_data_model_info(data) | \
        data.tester_params
        
    return  util.generate_deterministic_key(key_dict) + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S") # 加上微秒級時間搓


def prepare_save_file_path(base_path: str, data: TestResult) -> FilePaths:
    """準備回測結果的檔案儲存路徑 full path。

    根據策略參數和資料模型資訊，生成標準化的檔案路徑結構。

    Args:
        base_path (str): 基礎儲存路徑
        data (TestResult): 回測結果資料，包含策略參數和測試結果

    Returns:
        FilePaths: 包含以下路徑的 NamedTuple:
            - file_key: 檔案唯一名稱
            - trade_res: 交易結果 Excel 完整檔案路徑
            - test_df: 測試資料 Excel 完整檔案路徑
            - trade_chart: 交易圖表 SVG 完整檔案路徑
            - final_report: 統一儲存所有檔案的meta

    Example:
        >>> paths = _prepare_save_file_path("/data", test_result)
        >>> paths.trade_res
        'trade_res_strategy1_2330_d1_2023-01-01_2023-12-31.xlsx'
    """
    strategy_name = data.strategy_parms.get("name", "default_strategy")
    data_model_info = extract_data_model_info(data)
    
    path = f"{base_path}/{strategy_name}/{data_model_info['code']}"
    file_key = prepare_save_file_key(data)
    
    return FilePaths(
        file_key = file_key,
        trade_res=f"{path}/trade_res_{file_key}.csv",
        test_df=f"{path}/test_df_{file_key}.csv",
        trade_chart=f"{path}/chart/trade_res_{file_key}.svg",
        final_report = f"{base_path}/report_metadata.json"
    )


def prepare_final_report(file_path : Optional[FilePaths] = None, data : Optional[TestResult] = None) -> Tuple[Optional[dict], Optional[str]]:
    """準備結果報告，包含以下資訊:
    - key_string: 檔案唯一名稱
    - strategy_parms: 策略參數
    - tester_params: 測試參數
    - summary: 摘要
    - file: 檔案路徑
    - completed_at: 完成時間
    - updated_at: 更新時間
    - task_event_id: 任務事件ID
    Args:
        file_path: 檔案路徑
        data: 買賣標記結果
        
    Returns:
        Tuple[Optional[dict], Optional[str]]: 買賣標記結果的報告
    """
    file_path_temp = {}    
    if file_path is not None:
        file_path_temp.update(file_path.as_dict()) 

    now = datetime.datetime.now(datetime.timezone.utc)
    return {
            "key_string" : file_path.file_key + now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "strategy_parms" : json.dumps(data.strategy_parms),
            "tester_params" : json.dumps(data.tester_params),
            "summary":json.dumps({
                "total_return" : 0.00,
                "total_return_rate" : 0.000000
            }),
            "file": json.dumps(file_path_temp),
            "completed_at": data.completed_at.strftime("%Y-%m-%d %H:%M:%S") if data.completed_at else "",
            "updated_at": now,
            "task_event_id" : data.task_id
    }, None