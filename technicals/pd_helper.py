from typing import List, Tuple

import pandas as pd

_CODE_CANDLE_COLUMNS = ("code", "candle")


def distinct_code_candle_pairs(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """
    從 trade_price DataFrame 取出所有不重複的 (code, candle) 組合。

    Args:
        df: 需含 code、candle 欄位（對應 PandasTradePriceInput/OutputSchema）

    Returns:
        List[Tuple[str, str]]: 排序後的 (code, candle) 清單
    """
    if df.empty:
        return []

    missing = set(_CODE_CANDLE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    pairs = (
        df.loc[:, _CODE_CANDLE_COLUMNS]
        .dropna()
        .drop_duplicates()
        .sort_values(list(_CODE_CANDLE_COLUMNS))
    )
    return [(str(code), str(candle)) for code, candle in pairs.itertuples(index=False, name=None)]
