from abc import ABC, abstractmethod
from infra.repo.data_loaders.base import DataLoader
from typing import Tuple, Optional, TypeVar, Generic, Type
import pandas as pd
from pandera import DataFrameModel

T = TypeVar("T", bound=pd.DataFrame)


class IDataSet(ABC, Generic[T]):
    """
        仿DataBricks data set
        DataSet不關心資料從哪裡取得  重點在於驗證
    """
    def __init__(
        self,
        dao: DataLoader,
        expected_schema: Optional[Type[DataFrameModel]] = None,
        **kwargs,
    ):
        """
        初始化 DataSet，設置數據加載所需的參數
        Args:
            dao: 數據加載器
            expected_schema: Pandera DataFrameModel，用於驗證欄位結構
            kwargs: query parameters , ex: code, start_time, end_time, candle
        """
        self.dao = dao
        self.expected_schema = expected_schema
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

    def _validate(self, df: T) -> Optional[str]:
        """
        驗證數據（預設使用 Pandera expected_schema）
        Returns:
            Optional[str]: 錯誤訊息
        """
        return self._validate_schema(df)

    def _validate_schema(self, df: pd.DataFrame) -> Optional[str]:
        if self.expected_schema is None:
            return None
        try:
            self.expected_schema.validate(df, lazy=True)
            return None
        except Exception as e:
            return str(e)

    @abstractmethod
    def _fetch_data(self) -> Tuple[Optional[T], Optional[str]]:
        """
        獲取原始數據
        Returns:
            DataFrame: 原始的 pandas DataFrame
        """
        pass
