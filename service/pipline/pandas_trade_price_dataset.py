from typing import Tuple, Optional, Type
import pandas as pd
from pandera import DataFrameModel

from models.pipline_model.pandas_trade_price_schema import PandasTradePriceInputSchema
from service.pipline.data_set import IDataSet


class PandasTradePriceDataSet(IDataSet[pd.DataFrame]):
    """
        Args:
            dao (DataLoader): used to fetch data
            expected_schema (DataFrameModel): Pandera schema，預設為輸入欄位結構
    """
    def __init__(
        self,
        dao,
        expected_schema: Type[DataFrameModel] = PandasTradePriceInputSchema,
        **kwargs,
    ):
        super().__init__(dao, expected_schema=expected_schema, **kwargs)

    def _fetch_data(self) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        獲取原始數據
        Returns:
            DataFrame: 原始的 pandas DataFrame
        """
        df, err = self.dao.query_data(**self.parms)
        if err is not None:
            return None, err

        if df.empty:
            return None, "empty data set"

        return df, None
