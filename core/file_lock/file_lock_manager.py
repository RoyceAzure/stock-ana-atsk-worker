from threading import Lock
import time
from typing import Dict


class FileLocker:
    """檔案鎖管理器，用於管理多線程讀寫同一檔案的同步機制

    Attributes:
        _locks (dict): 儲存檔案路徑與對應的鎖物件的字典
        _lock (Lock): 用於保護 _locks 字典操作的全局鎖
        _last_used (dict): 記錄每個鎖的最後使用時間
    """
    _locks: Dict[str, Lock] = {}
    _lock: Lock = Lock()
    _last_used: Dict[str, float] = {}

    @classmethod
    def get_lock(cls, file_path: str) -> Lock:
        """獲取指定檔案路徑的鎖，如果不存在則創建

        Args:
            file_path: 檔案路徑作為鎖的標識符

        Returns:
            Lock: 對應檔案路徑的線程鎖物件
        """
        now = time.time()
        with cls._lock:
            cls._cleanup(timeout=1800)
            
            if file_path not in cls._locks:
                cls._locks[file_path] = Lock()
            
            cls._last_used[file_path] = now
            return cls._locks[file_path]

    @classmethod
    def _cleanup(cls, timeout: int):
        """清理長時間未使用的鎖以釋放記憶體

        Args:
            timeout: 超時時間(秒)，超過此時間未使用的鎖將被清理
        """
        now = time.time()
        to_remove = [
            path for path, last_used in cls._last_used.items()
            if now - last_used > timeout
        ]
        
        for path in to_remove:
            del cls._locks[path]
            del cls._last_used[path]