import logging
import logging.config
import sys
from pythonjsonlogger import jsonlogger

# 1. 定義 Cloud-Native 的標準設定字典
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False, # 確保第三方套件的 log 不被吃掉
    "formatters": {
        "json": {
            # 指定給 JSON Formatter 的欄位
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
        },
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,          # Cloud-Native 標準：輸出至 stdout
            "formatter": "json",           # 正式環境改為 "json"，本地開發可改 "standard"
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

def setup_logging():
    """初始化全域日誌設定"""
    logging.config.dictConfig(LOGGING_CONFIG)
