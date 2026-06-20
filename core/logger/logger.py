import logging
import logging.config
import sys

from pythonjsonlogger.json import JsonFormatter

# 本地開發可改 formatter_cls 為 logging.Formatter 並使用 STANDARD_LOG_FORMAT
JSON_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
STANDARD_LOG_FORMAT = "[%(asctime)s] %(level)s [%(app)s] [%(name)s.%(funcName)s:%(lineno)d] %(message)s"


class AppJsonFormatter(JsonFormatter):
    """JSON log：固定欄位 app、levelname 簡化為 level。"""

    def __init__(self, app: str) -> None:
        super().__init__(
            fmt=JSON_LOG_FORMAT,
            rename_fields={"levelname": "level"},
            static_fields={"app": app},
        )


class AppStandardFormatter(logging.Formatter):
    """純文字 log（本地除錯用）：含 app、level。"""

    def __init__(self, app: str) -> None:
        super().__init__(fmt=STANDARD_LOG_FORMAT)
        self._app = app

    def format(self, record: logging.LogRecord) -> str:
        record.app = self._app
        record.level = record.levelname
        return super().format(record)


def setup_logging(app: str, *, use_json: bool = True) -> None:
    """初始化全域日誌；app 為模組名稱（例：task-worker-preprocessing）。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    if use_json:
        handler.setFormatter(AppJsonFormatter(app))
    else:
        handler.setFormatter(AppStandardFormatter(app))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
