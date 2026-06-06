from decimal import Decimal
import numpy as np
import pandas as pd


"""_summary_
    pattern都是同一周期已知數據, 實際用法是要預測下一周期
"""


HANGING_MAN_BODY = 15.0
HANGING_MAN_HEIGHT = 75.0
SHOOTING_STAR_HEIGHT = 25.0
SPINNING_TOP_MIN = 40.0
SPINNING_TOP_MAX = 60.0
MARUBOZU = 98.0
ENGULFING_FACTOR = 1.1
MORNING_STAR_PREV2_BODY = 90.0
MORNING_STAR_PREV_BODY = 10.0
TWEEZER_BODY = 15.0
TWEEZER_HL = 0.01
TWEEZER_TOP_BODY = 40.0
TWEEZER_BOTTOM_BODY = 60.0

apply_marubozu = lambda x: x.body_perc > MARUBOZU

def apply_hanging_man(row):
    # 判断吊颈线形态：
    # 1. 底部75%以上
    # 2. 身體小于总高度的15%
    if row.body_bottom_perc > HANGING_MAN_HEIGHT:
        if row.body_perc < HANGING_MAN_BODY:
            return True
    return False

def apply_shooting_star(row):
    # 判断流星形态：
    # 1. 上部小於整體25%
    # 2. 身體小於整體的15%
    if row.body_top_perc < SHOOTING_STAR_HEIGHT:
        if row.body_perc < HANGING_MAN_BODY:
            return True
    return False

def apply_spinning_top(row):
    # 判断陀螺形态：
    # 1. 上部小於整體40%
    # 2. 下部大於整體60%
    # 3. 身體小於整體的15%
    if row.body_top_perc < SPINNING_TOP_MAX:
        if row.body_bottom_perc > SPINNING_TOP_MIN:
            if row.body_perc < HANGING_MAN_BODY:
                return True
    return False

def apply_engulfing(row):
    #反轉信號
    # 判断吞没形态：
    # 1. 當前K線方向與前一根相反
    # 2. 當前K線實體大於前一根的指定倍數
    if row.direction != row.direction_prev:
        if row.body_size > row.body_size_prev * ENGULFING_FACTOR:
            return True
    return False

def apply_tweezer_top(row):
    # 判断顶部镊子线：
    # 1. 當前與前一根實體大小變化小於閾值
    # 2. 當前為陰線且與前一根方向不同
    # 3. 最高價和最低價變化都小於閾值
    # 4. 上部小於整體指定百分比
    if abs(row.body_size_change) < TWEEZER_BODY:
        if row.direction == -1 and row.direction != row.direction_prev:
            if abs(row.low_change) < TWEEZER_HL and abs(row.high_change) < TWEEZER_HL:
                if row.body_top_perc < TWEEZER_TOP_BODY:
                    return True
    return False

def apply_tweezer_bottom(row):
    # 判断底部镊子线：
    # 1. 當前與前一根實體大小變化小於閾值
    # 2. 當前為陽線且與前一根方向不同
    # 3. 最高價和最低價變化都小於閾值
    # 4. 下部大於整體指定百分比
    if abs(row.body_size_change) < TWEEZER_BODY:
        if row.direction == 1 and row.direction != row.direction_prev:
            if abs(row.low_change) < TWEEZER_HL and abs(row.high_change) < TWEEZER_HL:
                if row.body_bottom_perc > TWEEZER_BOTTOM_BODY:
                    return True
    return False

def apply_morning_star(row, direction=1):
    # 判断启明星/黄昏星形态：
    # 1. 前前根K線實體大於指定閾值
    # 2. 前一根K線實體小於指定閾值
    # 3. 當前K線方向與指定方向相同，且與前前根不同
    # 4. 當前K線中點高於（啟明星）或低於（黃昏星）前前根中點
    if row.body_perc_prev_2 > MORNING_STAR_PREV2_BODY:
        if row.body_perc_prev < MORNING_STAR_PREV_BODY:
            if row.direction == direction and row.direction_prev_2 != direction:
                if direction == 1:
                    if row.close > row.mid_point_prev_2:
                        return True
                else:
                    if row.close < row.mid_point_prev_2:
                        return True
    return False

def remove_columns(df: pd.DataFrame)-> pd.DataFrame:
    """
    清除不必要欄位
    remove created_at and updated_at columns
    """
    return df.drop(columns=["created_at", "updated_at"], errors='ignore')

def apply_candle_props(df: pd.DataFrame) -> pd.DataFrame:
    """
    計算基本特徵欄位
    """
    df_an = df.copy()
    
    # 基礎價差計算
    direction_val = df_an.close - df_an.open
    body_size = abs(direction_val)
    full_range = df_an.high - df_an.low

    safe_range = full_range.replace(0, np.nan)

    # 計算各項百分比
    body_perc = ((body_size / safe_range) * 100).fillna(0).round(2)
    
    body_lower = df_an[['close','open']].min(axis=1)
    body_upper = df_an[['close','open']].max(axis=1)
    
    body_bottom_perc = ((body_lower - df_an.low) / safe_range).fillna(0) * 100
    body_top_perc = 100 - (((df_an.high - body_upper) / safe_range).fillna(0) * 100)
    
    mid_point = (full_range / 2) + df_an.low
    # ----------------------------------

    # 寫回 DataFrame
    df_an['body_lower'] = body_lower
    df_an['body_upper'] = body_upper
    df_an['body_bottom_perc'] = body_bottom_perc
    df_an['body_top_perc'] = body_top_perc
    df_an['body_perc'] = body_perc
    df_an['direction'] = [1 if x >= 0 else -1 for x in direction_val]
    df_an['body_size'] = body_size
    df_an['mid_point'] = mid_point
    df_an['daily_range'] = full_range

    return df_an

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df_cleaned = df.copy()

    for column in df_cleaned.columns:
        s = df_cleaned[column]
        dtype = s.dtype

        # 1. 處理物件型別 (String / Decimal)
        if dtype == object:
            non_null = s.dropna()
            if len(non_null) > 0:
                first_val = non_null.iloc[0]
                # 強烈建議：將 Decimal 轉為 float，增加後續相容性
                if isinstance(first_val, Decimal):
                    df_cleaned[column] = pd.to_numeric(s, errors='coerce')
                else:
                    # 字串清理
                    df_cleaned[column] = s.astype(str).str.strip()
                    df_cleaned[column] = df_cleaned[column].replace(["", "nan", "None"], np.nan)

        # 2. 處理時間型別 (解決你遇到的 datetime64[ns, UTC] 問題)
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            if hasattr(s.dt, "tz") and s.dt.tz is not None:
                # 轉 UTC 並抹除時區標籤
                df_cleaned[column] = s.dt.tz_convert("UTC").dt.tz_localize(None)

        # 3. 處理布林型別
        elif dtype == bool or (hasattr(dtype, "kind") and dtype.kind == "b"):
            df_cleaned[column] = s.fillna(False).astype(bool)

    # 4. 核心價格欄位檢查
    core_columns = ["open", "high", "low", "close"]
    cols_to_check = [c for c in core_columns if c in df_cleaned.columns]
    if cols_to_check:
        df_cleaned = df_cleaned.dropna(subset=cols_to_check)

    return df_cleaned


def convert_float_to_decimal(df):
    # 創建一個新的 DataFrame 來存儲結果
    df_decimal = df.copy()
    
    # 遍歷所有列
    for column in df_decimal.columns:
        # 檢查列的數據類型
        if df_decimal[column].dtype == 'float64':
            # 將 float64 轉換為 Decimal
            df_decimal[column] = df_decimal[column].apply(lambda x: Decimal(str(x)) if pd.notnull(x) else x)
    
    return df_decimal


def trade_price_post_process(df: pd.DataFrame) -> pd.DataFrame:
    """
    與 spark_process_trade_price.trade_price_post_process 相同邏輯的 pandas 版本。
    處理時間列並依 code、candle 分組計算每組的 start_date、end_date。
    """
    df = df.copy()
    # 確保 trade_time 為 datetime
    df["trade_time"] = pd.to_datetime(df["trade_time"])
    # 日期欄位（僅日期部分，對應 Spark cast("date")）
    df["trade_time_date"] = df["trade_time"].dt.normalize()
    # 將 trade_time 格式化成 yyyy-MM-dd HH:mm:ss.SSSSSS 再轉回（與 Spark 一致）
    df["trade_time"] = pd.to_datetime(
        df["trade_time"].dt.strftime("%Y-%m-%d %H:%M:%S.%f"),
        format="%Y-%m-%d %H:%M:%S.%f",
        errors="coerce",
    )
    # 依 code, candle 分組，取每組最早與最晚日期
    df["start_date"] = df.groupby(["code", "candle"], dropna=False)[
        "trade_time_date"
    ].transform("min")
    df["end_date"] = df.groupby(["code", "candle"], dropna=False)[
        "trade_time_date"
    ].transform("max")

    return df