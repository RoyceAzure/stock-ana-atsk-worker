import pandas as pd

def get_last_non_zero_signal(df: pd.DataFrame, column_name: str = 'SIGNAL', lookback_count: int = 5, default_value: int = 0) -> int:
    """從DataFrame的最後幾筆往回看，取第一個非0的欄位值
    
    Args:
        df: 要查詢的DataFrame
        column_name: 要查詢的欄位名稱，預設為 'SIGNAL'
        lookback_count: 往回看的筆數，預設為 5
        default_value: 如果都是0或NaN時的預設值，預設為 0
        
    Returns:
        int: 找到的第一個非0值，如果都是0或NaN則回傳預設值
    """
    if len(df) == 0:
        return default_value
    
    # 確保往回看的筆數不超過DataFrame的長度
    actual_lookback = min(lookback_count, len(df))
    last_signals = df.iloc[-actual_lookback:][column_name]
    
    # 從後往前找第一個非0且非NaN的值
    for signal in reversed(last_signals.values):
        if pd.notna(signal) and int(signal) != 0:
            return int(signal)
    
    return default_value