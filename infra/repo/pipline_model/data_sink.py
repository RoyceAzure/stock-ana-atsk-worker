from abc import ABC, abstractmethod
from typing import Tuple, Optional, TypeVar, Generic
import pandas as pd
from models.pipline_model.pipline_params import SinkLocationType, SinkParams

T = TypeVar("T", bound=pd.DataFrame)

class IDataSink(ABC, Generic[T]):
    """
    for spark, df and dao already combine
    """
    def __init__(self, args : SinkParams = None):
        """
        初始化 DataSet，設置數據加載所需的參數
        """ 
        self.parms = args

    def _release_df_select(self) -> None:
        self._df_selelct = None

    def save_data(self, dataFrame : T) -> Optional[str]:
        """
        """
        try:
            self._df_selelct, err = self._validate(dataFrame)
            if err is not None:
                return err

            save_err = self._save()
            return save_err

        except Exception as e:
            return str(e)
        finally:
            self._release_df_select()

    @abstractmethod
    def _validate(self, df: T) -> Tuple[Optional[T], Optional[str]]:
        """
        驗證數據
        Returns:
            Tuple[Optional[T], Optional[str]]: (dataframe, error_message)
        """
        pass
    

    
    @abstractmethod
    def _save(self) -> Optional[str]:
        """
        獲取原始數據
        Returns:
            DataFrame: 原始的 Spark DataFrame
        """
        pass
    
