from abc import ABC, abstractmethod
from infra.repo.data_loaders.base import DataLoader
from typing import Tuple, Optional, TypeVar, Generic
import pandas as pd

T = TypeVar("T", pd.DataFrame)

class IDataSet(ABC, Generic[T]):
    """
        仿DataBricks data set
        DataSet不關心資料從哪裡取得  重點在於驗證
    """
    def __init__(self, dao:DataLoader,**kwargs):
        """
        初始化 DataSet，設置數據加載所需的參數
        Args:
            dao: 數據加載器
            expected_schema: 期望的數據模式
            kwargs: query parameters , ex: code, start_time, end_time, candle
        """ 
        self.dao = dao
        self.parms = kwargs
    
    def load_data(self) -> Tuple[Optional[T], Optional[str]]:
        """
        加載並驗證數據
        Returns:
            Tuple[Optional[T], Optional[str]]: (dataframe, error_message)
        """
        try:
            source_df, err = self._fetch_data()
            if err is not None:
                return None, err
            
            err = self._validate(source_df)
            if err is not None:
                return None, err
            
            return source_df, None
            
        except Exception as e:
            return None, str(e)

    @abstractmethod
    def _validate(self, df: T) -> Optional[str]:
        """
        驗證數據
        Returns:
            Optional[str]: 錯誤訊息
        """
        pass
    
    @abstractmethod
    def _fetch_data(self) -> Tuple[Optional[T], Optional[str]]:
        """
        獲取原始數據
        Returns:
            DataFrame: 原始的 Spark DataFrame
        """
        pass