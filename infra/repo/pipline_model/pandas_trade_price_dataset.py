from typing import Tuple, Optional
import pandas as pd
from infra.repo.pipline_model.data_set import IDataSet

class PandasTradePriceDataSet(IDataSet[pd.DataFrame]):
    """
        Args:
            dao (DataLoader) : used to fetch data
            expected_schema (StructType) : used to validete
    """
    def _fetch_data(self) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        獲取原始數據
        Returns:
            DataFrame: 原始的 Spark DataFrame
        """
        df, err = self.dao.query_data(**self.parms)
        if err is not None:
            return None, err
        
        if df.empty:
            return None, "empty data set"
        
        return df, None

    def _validate(self, df: pd.DataFrame) -> Optional[str]:
        return None