import json
import logging
from typing import Any, List, Optional, Tuple, Union

import pandas as pd

from infra.repo.data_loaders.base import DataLoader
from util.generate_util import format_date_to_utc_midnight
from util.memory_log import log_mem

_OHLC_COLUMNS = ("open", "high", "low", "close")
logger = logging.getLogger(__name__)


def _coerce_ohlc_columns(df: pd.DataFrame) -> pd.DataFrame:
    """PG decimal(10,2) 經 psycopg2 會是 Decimal/object，轉成 float64 供 Pandera 驗證。"""
    for col in _OHLC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _parse_code_list(code: Union[str, List[Any], Tuple[Any, ...]]) -> List[str]:
    """將 code 參數正規化為字串列表（trade_price.code 為 varchar）。"""
    if isinstance(code, str):
        if code.startswith("["):
            parsed = json.loads(code)
            if not isinstance(parsed, list):
                raise ValueError(f"code JSON must be a list, got {type(parsed).__name__}")
            raw_list = parsed
        else:
            raw_list = [code]
    else:
        raw_list = list(code)

    return [str(item).strip() for item in raw_list if str(item).strip()]


class SQLLoader(DataLoader):
    """_summary_
    postgres db loader
    只能用來讀取trade_price table
    Args:
        conn (psycopg2.connection):
    """
    def __init__(self, conn):
        self.conn = conn

    def query_data(self, **kwargs: Any) -> Tuple[Optional[Any], Optional[str]]:
        """
        從 postgres db trade_price table 表查詢數據。
        查詢邏輯與 SparkPGTradePriceLoader 一致。

        :param kwargs: 可包含以下參數：
            - code (Optional[Union[str, List[str]]]): 代碼，若為 "*" 則為特殊模式（使用 created_at 過濾），
              也可以為字串列表，會使用 IN 條件查詢。
            - start_time (Optional[str]): 開始時間
            - end_time (Optional[str]): 結束時間
            - candle (Optional[str]): 蠟燭圖類型
            - filter_time_col string: 過濾時間的欄位名稱
        :return: 包含查詢結果的 pandas DataFrame 和相關信息
        """
        code = kwargs.get('code', "*")
        start_time = kwargs.get('start_time')
        end_time = kwargs.get('end_time')
        candle = kwargs.get('candle')
        filter_time_col = kwargs.get('filter_time_col', "trade_time")
        try:
            # 1. 建立動態 WHERE 條件清單（與 spark_pg_trade_price_loader 邏輯一致）
            filters = []
            params: List[Any] = []


            if code != "*":
                code_list = _parse_code_list(code)

                if code_list:
                    filters.append("code = ANY(%s::text[])")
                    params.append(code_list)
            # 決定時間過濾要使用的欄位名稱

            # Start Time 過濾
            if start_time is not None:
                start_time = format_date_to_utc_midnight(start_time)
                start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
                filters.append(f"{filter_time_col} >= %s")
                params.append(f"{start_str}+00")

            # End Time 過濾
            if end_time is not None:
                end_time = format_date_to_utc_midnight(end_time)
                end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
                filters.append(f"{filter_time_col} <= %s")
                params.append(f"{end_str}+00")

            # Candle 過濾
            if candle is not None:
                filters.append("candle = %s")
                params.append(candle)

            # 2. 組成 WHERE 子句
            where_clause = " AND ".join(filters) if filters else "1=1"
            query = f"SELECT * FROM trade_price WHERE {where_clause}"

            # 3. 執行查詢並回傳 pandas DataFrame
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                log_mem(
                    logger,
                    "sql_before_fetchall",
                    code=code,
                    candle=candle,
                    filter_time_col=filter_time_col,
                )
                res = cursor.fetchall()
                log_mem(
                    logger,
                    "sql_after_fetchall",
                    code=code,
                    candle=candle,
                    row_count=len(res),
                )
                self.conn.commit()
                data_df = pd.DataFrame(res, columns=columns)
                data_df = _coerce_ohlc_columns(data_df)
                data_df = data_df.sort_values("trade_time", ascending=True)
                log_mem(
                    logger,
                    "sql_after_dataframe",
                    data_df,
                    code=code,
                    candle=candle,
                    row_count=len(data_df),
                )
                del res
                log_mem(
                    logger,
                    "sql_after_del_res",
                    data_df,
                    code=code,
                    candle=candle,
                    row_count=len(data_df),
                )
                return data_df, None
        except Exception as e:
            self.conn.rollback()
            return None, str(e)


    def query_datas(self, **kwargs: Any) -> Tuple[Optional[List[Any]], Optional[str]]:
        raise NotImplementedError("This method must be implemented by subclass")