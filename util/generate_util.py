import datetime
import hashlib
import json

def get_utc_day_range(target_date: datetime.datetime | None = None) -> tuple[datetime.datetime, datetime.datetime]:
    """
    回傳給定日期（預設為今天）的 UTC 起點與終點 datetime。
    """
    from datetime import datetime, time, timedelta, timezone
    # 1. 取得基準日期 (若未傳入則取當前 UTC)
    base_date = (target_date or datetime.now(timezone.utc)).date()
    
    # 2. 建立當天 00:00:00.000000 UTC
    start_of_day = datetime.combine(base_date, time.min).replace(tzinfo=timezone.utc)
    
    # 3. 建立隔天 00:00:00.000000 UTC
    end_of_day = start_of_day + timedelta(days=1)
    
    return start_of_day, end_of_day


def format_date_to_utc_midnight(date_str: str) -> datetime.datetime:
    """
    將 'YYYY-MM-DD' 格式的日期字符串轉換為代表 UTC 午夜的 datetime 對象。

    Args:
        date_str: 'YYYY-MM-DD' 格式的日期字符串。

    Returns:
        datetime.datetime: 一個時區為 UTC 的 datetime 對象，表示輸入日期的午夜。

    Raises:
        ValueError: 如果輸入的日期字符串格式不正確。
    """
    try:
        # 1. 解析輸入的日期字符串
        parsed_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

        # 2. 創建一個表示當天午夜的 naive datetime 對象
        midnight_time = datetime.time(0, 0, 0)
        naive_dt = datetime.datetime.combine(parsed_date, midnight_time)

        # 3. 將 naive datetime 設置為 UTC 時區 (使其成為 aware 對象)
        utc_dt = naive_dt.replace(tzinfo=datetime.timezone.utc)

        return utc_dt

    except ValueError as e: 
        # 包含原始錯誤以提供更多上下文
        raise ValueError(f"輸入的日期格式不正確: '{date_str}'，應為 'YYYY-MM-DD' (Error: {e})")
    except Exception as ex: 
        # 捕獲其他潛在錯誤
        print(f"[ERROR util.py] Unexpected error in date conversion: {ex}")
        raise

# --- 示例用法 (可選) ---
# date_string = '2025-04-18'
# timestamp_obj = format_date_to_utc_midnight(date_string)
# print(f"原始日期: {date_string}")
# print(f"轉換後 datetime 對象: {timestamp_obj}")
# print(f"對象類型: {type(timestamp_obj)}")
# print(f"時區信息: {timestamp_obj.tzinfo}")


def to_rfc3339(d) -> str:
    if isinstance(d, datetime.date):
        # 轉成 datetime, 設定時間為午夜, 設定時區為 UTC
        dt = datetime.datetime.combine(d, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
        # 轉字串並將 +00:00 替換成 Z (Go 對 Z 的支援度最好)
        return dt.isoformat().replace('+00:00', 'Z')
    return str(d)

def generate_deterministic_key(params: dict) -> str:
    # 1. 排序並序列化 (確保 key 順序一致)
    # ensure_ascii=False 處理中文，separators 移除空格減少長度
    param_str = json.dumps(params, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    
    # 2. MD5 雜湊
    hash_obj = hashlib.md5(param_str.encode('utf-8'))
    return  hash_obj.hexdigest() # 原始長度為 32 字元
    