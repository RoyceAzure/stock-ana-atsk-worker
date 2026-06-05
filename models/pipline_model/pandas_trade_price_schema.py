"""
Pandas 版本的 trade_price schema，用於 DataFrame 欄位驗證。
對應 spark_trade_price_schema 的 INPUT_SCHEMA / OUTPUT_SCHEMA。
使用 Pandera 與 @pa.check_types 進行驗證。

注意：Pandera Field 不支援 dtype 參數，型別由 Series[...] 註解推斷。
傳入 Field 的未註冊參數會被當作 custom check，會觸發 SchemaInitError。
"""
import pandas as pd
import pandera as pa
from pandera.typing import DataFrame, Series
from pandera import DataFrameModel, Field


class PandasTradePriceInputSchema(DataFrameModel):
    """
    輸入 DataFrame schema，對應 trade_price 表原始欄位。
    與 spark_trade_price_schema.INPUT_SCHEMA 一致。
    """
    id: Series[int] = Field(nullable=False)
    code: Series[str] = Field(nullable=False)
    open: Series[float] = Field(nullable=False)
    close: Series[float] = Field(nullable=False)
    high: Series[float] = Field(nullable=False)
    low: Series[float] = Field(nullable=False)
    trade_time: Series = Field(nullable=False)
    candle: Series[str] = Field(nullable=False)
    volume: Series[int] = Field(nullable=True)
    volume_weight: Series[int] = Field(nullable=True)
    updated_at: Series = Field(nullable=False)
    created_at: Series = Field(nullable=False)


class PandasTradePriceOutputSchema(DataFrameModel):
    """
    輸出 DataFrame schema，包含計算後的特徵欄位。
    這裡只包含計算後的基本特徵欄位，不包括高階指標欄位
    """
    id: Series[int] = Field(nullable=True)
    code: Series[str] = Field(nullable=True)
    open: Series[float] = Field(nullable=True)
    close: Series[float] = Field(nullable=True)
    high: Series[float] = Field(nullable=True)
    low: Series[float] = Field(nullable=True)
    trade_time: Series = Field(nullable=True)
    candle: Series[str] = Field(nullable=True)
    volume: Series[int] = Field(nullable=True)
    volume_weight: Series[int] = Field(nullable=True)
    direction: Series[int] = Field(nullable=False)
    body_size: Series[float] = Field(nullable=True)
    body_perc: Series[float] = Field(nullable=True)
    body_lower: Series[float] = Field(nullable=True)
    body_upper: Series[float] = Field(nullable=True)
    body_bottom_perc: Series[float] = Field(nullable=True)
    body_top_perc: Series[float] = Field(nullable=True)
    daily_range: Series[float] = Field(nullable=True)
    mid_point: Series[float] = Field(nullable=True)
    # low_change: Series[float] = Field(nullable=True)
    # high_change: Series[float] = Field(nullable=True)


@pa.check_types
def validate_pandas_trade_price_input(df: pd.DataFrame) -> DataFrame[PandasTradePriceInputSchema]:
    """驗證輸入 DataFrame 是否符合 InputSchema"""
    return df


@pa.check_types
def validate_pandas_trade_price_output(df: pd.DataFrame) -> DataFrame[PandasTradePriceOutputSchema]:
    """驗證輸出 DataFrame 是否符合 OutputSchema"""
    return df
