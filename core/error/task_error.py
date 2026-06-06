class ProcessorBaseError(Exception):
    """Processor 拋出的基礎錯誤"""
    pass

# ==========================================
# 1. 可忽略錯誤 (Ignorable) - 不算真正失敗，直接 ACK
# ==========================================
class TaskAlreadyClaimedError(ProcessorBaseError):
    """任務已經被其他 Worker 領取 (UPDATE RETURNING 0筆)"""
    pass

class TaskAlreadyCompletedError(ProcessorBaseError):
    """任務狀態已是 COMPLETED (通常發生在重複派發時)"""
    pass

# ==========================================
# 2. 瞬態錯誤 (Transient) - 需要指數退避重試
# ==========================================
class TransientError(ProcessorBaseError):
    """所有可重試錯誤的基礎類別"""
    pass

class DatabaseConnectionError(TransientError):
    """資料庫連線失敗或 Timeout"""
    pass

class DatabaseDeadlockError(TransientError):
    """資料庫發生死鎖 (Deadlock)"""
    pass

# ==========================================
# 3. 永久錯誤 (Permanent) - 絕不重試，直接宣告失敗並 ACK
# ==========================================
class PermanentError(ProcessorBaseError):
    """所有不可重試錯誤的基礎類別"""
    pass

class InvalidPayloadError(PermanentError):
    """MQ Payload 格式錯誤或缺少必要欄位 (例如沒有 code)"""
    pass

class RawDataNotFoundError(PermanentError):
    """DB 中找不到該批次的 Raw Data (可能上游下載根本沒寫入成功)"""
    pass

class DataMergeLogicError(PermanentError):
    """資料合併邏輯發生致命錯誤 (例如欄位型別無法計算)"""
    pass