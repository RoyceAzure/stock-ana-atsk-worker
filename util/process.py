from decimal import Decimal, getcontext
from datetime import datetime
import numpy as np
import pandas as pd
import math
getcontext().prec = 5

def calculate_log_returns(prices : pd.Series) -> pd.Series:
    """
    log return = ln(Pt / Pt-1)
    计算 Decimal 类型价格序列的对数收益率。
    
    :param prices: Decimal 类型的价格序列（pandas Series）
    :return: 对数收益率序列
    """
    price_ratio = prices / prices.shift(1)
    return safe_log(price_ratio)


def decimal_log(x):
    """
        parm:
            x 數值資料
        why:
            for apply
            交易資料為Decimal 所以不能使用np.log
            pd 裡面沒有decimal type  是object, 所以還得做一層判斷跟轉型
        how:
            Decimal似乎很適合從str轉換
            非Decimal數值類型先換成Decimal
            使用換抵公式取對數log
        
    """
    if not isinstance(x, Decimal):
        x = Decimal(str(x))
    if x < 0:
        raise ValueError("Cannot calculate logarithm of non-positive number")
        
    return x.log10 / Decimal(str(math.log10(math.e)))

def safe_log(price : pd.Series) -> pd.Series:
    """
    parm 
        price pd.Series 是價差ratio
    """
    if price.dtype == "object" and isinstance(price[0], Decimal):
        return price.apply(decimal_log)
    else:
        return np.log(price.astype("float"))

def preProcessTradePrice(trade_price:pd.DataFrame) -> pd.DataFrame:
    """
        calculate log return, cusum_rewards,  clean data
        
        columns : ['id', 'code', 'open', 'close', 'high', 'low', 'trade_time', 'candle','volume', 'volume_weight']
    """
    processed_df = trade_price.copy()
    processed_df = processed_df.dropna()
    processed_df["code"] = processed_df["code"].astype(str)
    processed_df = convert_to_datetime(processed_df)
    processed_df = drop_duplicate_date(processed_df)
    processed_df = processed_df.sort_values("trade_time", ascending = True)
    processed_df = processed_df.reset_index(drop = True)
    processed_df["log_returns"] = calculate_log_returns(processed_df.close)
    processed_df["cusum_rewards"] = cusum_log_return(processed_df.log_returns)
    processed_df = processed_df.drop("id", axis=1)
    # display_column_types(processed_df)
    return processed_df

def cusum_log_return(log_returns :pd.Series) -> pd.Series:
    return np.exp(log_returns.cumsum())

def drop_duplicate_date(df :pd.DataFrame):
    """
    drop trad_time date重複資料
    """
    df_copy = df.copy()
    date = pd.to_datetime(df_copy["trade_time"]).dt.date
    df_copy = df_copy[~date.duplicated(keep= "first")] 
    return df_copy

def caculate_CAGR_log(log_returns :pd.Series):
    """
    使用daily log return 計算CAGR
    
    :param log_return: daily log return series
    :return: CAGR 值（百分比）
    """
    years = (log_returns.index[-1] - log_returns.index[0]) / 365.25
    
    total_return = log_returns.sum()
    annual_log_return = total_return / years
    
    cagr = (np.exp(annual_log_return) -1)*100
    return cagr


def caculate_risk_and_sharp(log_returns :pd.Series, risk_free_rate=0.02):
    """
    使用daily log return 計算 risk and sharp
    
    :param log_return: daily log return series
    :return:         
    {
        "annualized_return": annualized_return * 100,  # 轉換為百分比
        "annualized_risk": annualized_volatility * 100,  # 轉換為百分比
        "sharpe_ratio": sharpe_ratio
    }
    """
    years = (log_returns.index[-1] - log_returns.index[0]) / 365.25
    
    total_return = log_returns.sum()
    annual_log_return = total_return / years
    
    annualized_return  = (np.exp(annual_log_return) -1)
    
    daily_volatility = log_returns.std()
    annualized_volatility = daily_volatility * np.sqrt(years)
    
    sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
    
    return {
        "annualized_return": annualized_return * 100,  
        "annualized_risk": annualized_volatility * 100,  
        "sharpe_ratio": sharpe_ratio
    }
    
def convert_to_datetime(df, column='trade_time'):
    """
    将指定的列转换为 datetime 类型，处理可能的混合数据类型和格式。
    
    :param df: 输入的 Pandas DataFrame
    :param column: 要转换的列名
    :return: 转换后的 DataFrame
    """
    def parse_date(x):
        if pd.isna(x):
            return pd.NaT
        if isinstance(x, (pd.Timestamp, datetime)):
            return x
        try:
            return pd.to_datetime(x)
        except ValueError:
            print(f"Warning: Unable to parse date: {x}")
            return pd.NaT

    df[column] = df[column].apply(parse_date)
    return df


def convert_float_to_decimal(df, precision=2):
    """
    将 pandas DataFrame 中的所有 float64 列转换为 Decimal(10,precision)。
    
    :param df: 输入的 pandas DataFrame
    :param precision: Decimal 的精度，默认为 2
    :return: 转换后的 DataFrame
    """
    df_copy = df.copy()
    float_columns = df_copy.select_dtypes(include=['float64']).columns
    
    for col in float_columns:
        df_copy[col] = df_copy[col].apply(lambda x: Decimal(str(round(x, precision))))
    
    return df_copy

def display_column_types(df):
    """
    显示 pandas DataFrame 中所有列的数据类型。
    
    :param df: 输入的 pandas DataFrame
    :return: 包含列名和数据类型的 DataFrame
    """
    # 创建一个包含列名和数据类型的字典
    type_dict = dict(df.dtypes)
    
    # 将字典转换为 DataFrame
    type_df = pd.DataFrame(list(type_dict.items()), columns=['Column', 'Data Type'])
    
    # 将 'Data Type' 列转换为字符串，以便更好地显示
    type_df['Data Type'] = type_df['Data Type'].astype(str)
    
    return type_df


def ewm(series : pd.Series, **kargs):
    return series.ewm(**kargs).mean()


def series_to_decimal(series, precision=2):
    """
    将 pandas Series 转换为 Decimal 类型，指定精度。
    
    :param series: 输入的 pandas Series
    :param precision: 小数点后的精度，默认为 2
    :return: 转换后的 Series
    """
    return series.astype(object).apply(lambda x: Decimal(str(round(x, precision))))


def remove_timezone(df, datetime_columns=None) -> pd.DataFrame:
    """
    从 DataFrame 的 datetime 列中移除时区信息。
    
    :param df: 输入的 pandas DataFrame
    :param datetime_columns: 要处理的 datetime 列名列表。如果为 None，将处理所有 datetime 列
    :return: 处理后的 DataFrame
    """
    df = df.copy()  # 创建副本以避免修改原始数据
    
    if datetime_columns is None:
        datetime_columns = df.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns
    
    for col in datetime_columns:
        if col in df.columns:
            if df[col].dt.tz is not None:
                df[col] = df[col].dt.tz_localize(None)
                print(f"已从列 '{col}' 中移除时区信息")
            else:
                print(f"列 '{col}' 没有时区信息")
    
    return df