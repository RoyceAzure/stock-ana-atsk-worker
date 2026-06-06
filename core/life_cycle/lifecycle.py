import signal
import threading
import logging

# ==========================================
# 1. 全域唯一的 Event 物件
# ==========================================
# 只要其他檔案 import 這個變數，拿到的都會是同一個記憶體位址
shutdown_event = threading.Event()

def _signal_handler(signum, frame):
    """
    訊號處理的 Callback 函式
    當接收到 GKE 的 SIGTERM 或手動的 Ctrl+C 時觸發
    """
    # 將訊號代碼轉為可讀名稱 (例如 SIGTERM)
    signame = signal.Signals(signum).name
    logging.warning(f"\n[Lifecycle] 接收到系統訊號: {signame} ({signum})")
    logging.warning("[Lifecycle] 正在設定全域關閉標記，通知所有組件準備優雅退出...")

    # 觸發 Event，將內部狀態設為 True
    shutdown_event.set()

def register_graceful_shutdown():
    """
    在主程式啟動時呼叫此函式，註冊要監聽的訊號。
    ⚠️ 注意：此函式必須在 Main Thread 中呼叫！
    """
    # GKE (Kubernetes) 縮容或刪除 Pod 時預設發送的訊號
    signal.signal(signal.SIGTERM, _signal_handler)

    # 開發階段在終端機按下 Ctrl+C 發送的訊號 (方便本地測試)
    signal.signal(signal.SIGINT, _signal_handler)

    logging.info("[Lifecycle] 訊號監聽器已註冊完畢 (SIGTERM, SIGINT)。")