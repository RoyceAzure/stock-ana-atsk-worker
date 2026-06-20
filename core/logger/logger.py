import logging
import sys
from typing import Final

from pythonjsonlogger.json import JsonFormatter

from core.logger.task_context import TaskContextFilter

LOG_LEVEL_INFO: Final[str] = "info"
LOG_LEVEL_DEBUG: Final[str] = "debug"
SUPPORTED_LOG_LEVELS: Final[tuple[str, ...]] = (LOG_LEVEL_INFO, LOG_LEVEL_DEBUG)

JSON_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
STANDARD_LOG_FORMAT = (
    "[%(asctime)s] %(level)s [%(app)s] [%(task_event_id)s] "
    "[%(name)s.%(funcName)s:%(lineno)d] %(message)s"
)


def parse_log_level(raw: str) -> int:
    """解析 log_level（info / debug）為 logging 等級常數。"""
    normalized = raw.strip().lower()
    if normalized == LOG_LEVEL_DEBUG:
        return logging.DEBUG
    if normalized == LOG_LEVEL_INFO:
        return logging.INFO
    supported = ", ".join(SUPPORTED_LOG_LEVELS)
    raise ValueError(f"不支援的 LOG_LEVEL: {raw}（支援: {supported}）")


class AppJsonFormatter(JsonFormatter):
    """JSON log：固定欄位 app、level；任務期間附加 task_event_id。"""

    def __init__(self, app: str) -> None:
        super().__init__(
            fmt=JSON_LOG_FORMAT,
            rename_fields={"levelname": "level"},
            static_fields={"app": app},
        )

    def add_fields(
        self,
        log_record: dict,
        record: logging.LogRecord,
        message_dict: dict,
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        task_event_id = getattr(record, "task_event_id", None)
        if task_event_id:
            message_dict["task_event_id"] = task_event_id


class AppStandardFormatter(logging.Formatter):
    """純文字 log（本地除錯用）：含 app、level、task_event_id。"""

    def __init__(self, app: str) -> None:
        super().__init__(fmt=STANDARD_LOG_FORMAT)
        self._app = app

    def format(self, record: logging.LogRecord) -> str:
        record.app = self._app
        record.level = record.levelname
        record.task_event_id = getattr(record, "task_event_id", None) or "-"
        return super().format(record)


def setup_logging(
    app: str,
    *,
    level: int = logging.INFO,
    use_json: bool = True,
) -> None:
    """初始化全域日誌；app 為模組名稱（例：task-worker-preprocessing）。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.addFilter(TaskContextFilter())
    if use_json:
        handler.setFormatter(AppJsonFormatter(app))
    else:
        handler.setFormatter(AppStandardFormatter(app))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
