from abc import ABC, abstractmethod
import datetime
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from pydantic import Field
from models.basemodel import BaseModelWithConfig
from models.strategy.base import Direction, SaverParams, TPSLParms, TradeAction
from technicals.indicator import Indicator


class DataModel(ABC):
    """Source data for Tester, include pd.Dataframe (from db table) and meta data 
        
    Args:
        df (DataFrame): The data stored in a pandas DataFrame
    """
    def __init__(self, df: pd.DataFrame):
        if not isinstance(df, pd.DataFrame):
            raise ValueError("df must be a pandas DataFrame")
        self.data_df: pd.DataFrame = df

    @property
    def is_empty(self) -> bool:
        return self.data_df.empty

    def as_dict(self) -> Dict[str, Any]:
        pass
        

class I_TP_SL(ABC):
    """
        策略模式:
            計算TP and SL
    """
    @abstractmethod
    def apply_take_profit(self, row):
        pass

    @abstractmethod
    def apply_stop_loss(self, row):
        pass
    
    def get_describe(self): 
        pass

    
class TP_SL_1(I_TP_SL):
    """_summary_
            "TP" : "價格變化 * profit_factor + close",
            "SL" : "open"
    """
    def __init__(self, parmas : TPSLParms): 
        self.profit_factor = parmas.profit_factor
        self.loss_factor = parmas.loss_factor
    
    def apply_take_profit(self, row):
        if row.SIGNAL != TradeAction.NONE.value:
            return row.open * (1 + self.profit_factor)
        else:
            return 0.0
    
    def apply_stop_loss(self, row):
        if row.SIGNAL != TradeAction.NONE.value:
            return row.open * (1 + self.loss_factor)
        else:
            return 0.0
        
    def get_describe(self):
        return {
            "TP" : "row.open * (1 + self.profit_factor)",
            "SL" : "row.open * (1 + self.loss_factor)"
        }
        
def NewTP_SL_1(params : TPSLParms) -> TP_SL_1:
    return TP_SL_1(params)


class StrategyParms(BaseModelWithConfig):
    """策略參數主模型
    
    屬性:
        name: 策略名稱
        data_model: 數據模型類型
        tpsl: 止盈止損策略實例
        tpsl_parms: 止盈止損參數
        saver_parms: 儲存參數（可選）
    """
    name: str = Field(
        min_length=1,
        max_length=50,
        description="策略名稱"
    )
    data_model: DataModel = Field(
        description="數據模型類型",
    )
    tpsl: Optional[I_TP_SL] = Field(
        default=None,
        description="止盈止損策略實例"
    )
    tpsl_parms: Optional[TPSLParms] = Field(
        default=None,
        description="止盈止損參數設置"
    )
    saver_parms: Optional[SaverParams] = Field(
        default=None,
        description="儲存參數設置（可選）"
    )

    def as_dict(self):
        return {
            "name" : self.name,
            "data_model" : self.data_model.as_dict(),
            "tpsl" : self.tpsl.get_describe() if self.tpsl else None,
            "tpsl_parms" : self.tpsl_parms.as_dict() if self.tpsl_parms else None,
            "saver_parms" : self.saver_parms.as_dict() if self.saver_parms else {}
        }


class IStrategy(ABC):
    default_strategy_cols = ["trade_time", "open", "high", "low", "close","volume", "direction"]
    
    def __init__(self, strategy_names : str):
        self.strategy_names = strategy_names
        self.indicators : List[Indicator] = None
        
    @abstractmethod
    def _apply_signal(self, row):
        pass

    @abstractmethod
    def apply_signal(self, source_data : pd.DataFrame, is_shift_signal : bool) -> pd.DataFrame:
        """
            實行買賣交易訊號
        """
        pass
    
    @abstractmethod
    def scope_data_by_strategy(self, start_date : datetime.datetime) -> datetime.datetime:
        """
            根據不同策略需要的資料範圍，對資料進行延長，以確保資料長度足夠執行策略
        """
        pass
    
    def trading_days_to_calendar_days(self, n: int) -> int:
        """
        將交易天數轉換為大約的實際天數 (2.5 倍率  把假日也考慮進去)
        """
        if n <= 0:
            return 0
        return round(n * 2.5)
    
    def pre_process_data(self, source_data : pd.DataFrame,extra_cols : List[str] = None) -> pd.DataFrame:
        """清理,預處理資料，實行指標計算，並回傳處理後的資料
        
        Args:
            extra_cols: 非indicator的其餘指標列表
                Example:
                    ["HANGINGMAN", "ENGULFING", "TWEEZER"]
        """
            
        cols = IStrategy.default_strategy_cols.copy()
        

        added_direction_df = self.add_direction(source_data)

        #增加所有策略指標
        if self.indicators is not None:
            for indicator in self.indicators:
                added_direction_df = indicator.apply(added_direction_df)
                
            cols.extend([name for indicator in self.indicators for name in indicator.get_info().display_name])

        if extra_cols:
            cols.extend(extra_cols)

        # 去除重複的列名，避免 DataFrame 出現重複列導致 Series 布林值歧義錯誤
        cols = list(dict.fromkeys(cols))  # 保持順序的去重方法

        return self.add_default_column(self.clean_df_and_filter_column(added_direction_df, cols))
    
    def clean_df_and_filter_column(self, df : pd.DataFrame, columns : List[str]) -> pd.DataFrame:
        df_slim = df[columns].copy()
        df_slim.reset_index(drop=True, inplace=True)
        return df_slim
    
    def add_default_column(self, df : pd.DataFrame) -> pd.DataFrame:
        df["SIGNAL"] = TradeAction.NONE.value
        return df
    
    def excute_trade_mark(self, source_data : pd.DataFrame, is_shift_signal : bool) -> pd.DataFrame:
        """ 實行本身策略，標註交易訊號
        
        Args:
            source_data: 原始資料
            is_shift_signal: 是否將所有交易訊號往後一天 表示隔天根據前一天的訊號做買賣動作，預設為False
            
        Returns:
            pd.DataFrame: 處理後的資料
        """
        source_data["SIGNAL"] = source_data.apply(self._apply_signal, axis = 1)
        if is_shift_signal:
            source_data["SIGNAL"] = source_data["SIGNAL"].shift(1)  #交易訊號要往後一天 表示隔天根據前一天的訊號做買賣動作
            source_data = source_data.fillna(TradeAction.NONE.value) #去除第一筆資料
        
        return source_data
    
    def add_direction(self, df : pd.DataFrame) -> pd.DataFrame:
        """對 DataFrame 新增 "direction" 欄位，根據 open 和 close 比較結果使用 TradeSignal enum 的值
        
        Args:
            df: 輸入的 DataFrame，必須包含 "open" 和 "close" 欄位
            
        Returns:
            pd.DataFrame: 新增 "direction" 欄位後的 DataFrame
            
        計算邏輯:
            - 如果 close > open: direction = TradeSignal.UP (1) 上漲
            - 如果 close < open: direction = TradeSignal.DOWN (-1) 下跌
            - 如果 close == open: direction = TradeSignal.NONE (0) 無變化
        """
        df_result = df.copy()
        
        # 檢查必要的欄位是否存在
        if "open" not in df_result.columns or "close" not in df_result.columns:
            raise ValueError("DataFrame 必須包含 'open' 和 'close' 欄位")
        
        # 根據 open 和 close 比較結果計算 direction
        df_result["direction"] = df_result.apply(
            lambda row: Direction.UP.value if row.close > row.open 
                       else (Direction.DOWN.value if row.close < row.open 
                             else Direction.NONE.value),
            axis=1
        )
        
        return df_result

    def dropNa(self, df: pd.DataFrame) -> pd.DataFrame:
        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
    
    
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