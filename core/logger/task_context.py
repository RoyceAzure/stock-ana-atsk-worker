from __future__ import annotations

import contextvars
import logging
import uuid
from contextlib import contextmanager
from typing import Iterator, Optional, Union

_task_event_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "task_event_id",
    default=None,
)

TaskEventId = Union[str, uuid.UUID]


def bind_task_event_id(task_event_id: TaskEventId) -> contextvars.Token[Optional[str]]:
    return _task_event_id.set(str(task_event_id))


def reset_task_event_id(token: contextvars.Token[Optional[str]]) -> None:
    _task_event_id.reset(token)


def get_task_event_id() -> Optional[str]:
    return _task_event_id.get()


@contextmanager
def task_log_context(task_event_id: TaskEventId) -> Iterator[None]:
    """在任務執行期間注入結構化 log 欄位 task_event_id。"""
    token = bind_task_event_id(task_event_id)
    try:
        yield
    finally:
        reset_task_event_id(token)


class TaskContextFilter(logging.Filter):
    """將 task_log_context 的 task_event_id 注入每筆 LogRecord。"""

    def filter(self, record: logging.LogRecord) -> bool:
        task_event_id = get_task_event_id()
        if task_event_id is not None:
            record.task_event_id = task_event_id
        return True
