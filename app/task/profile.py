from __future__ import annotations

from dataclasses import dataclass

from app.env import env_str
from models.task_event import EventName

_DEFAULT_TASK_TYPE = EventName.PREPROCESS.value


def _parse_event_names(raw: str) -> frozenset[EventName]:
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        raise ValueError("WORKER_TASK_TYPES 不可為空")

    value_to_enum = {event_name.value: event_name for event_name in EventName}
    resolved: set[EventName] = set()
    for part in parts:
        event_name = value_to_enum.get(part)
        if event_name is None:
            supported = ", ".join(sorted(value_to_enum))
            raise ValueError(
                f"不支援的 WORKER_TASK_TYPES: {part}（支援: {supported}）"
            )
        resolved.add(event_name)

    return frozenset(resolved)


@dataclass(frozen=True)
class TaskWorkerProfile:
    """第二層組裝：此 Pod 啟用的任務 event_name 集合。"""

    enabled_event_names: frozenset[EventName]

    @classmethod
    def from_env(cls) -> TaskWorkerProfile:
        raw = env_str("WORKER_TASK_TYPES", _DEFAULT_TASK_TYPE)
        return cls(enabled_event_names=_parse_event_names(raw))

    @property
    def enabled_values(self) -> tuple[str, ...]:
        return tuple(sorted(event_name.value for event_name in self.enabled_event_names))

    @property
    def app_name(self) -> str:
        """模組名稱：task-worker-{WORKER_TASK_TYPES}。"""
        return f"task-worker-{','.join(self.enabled_values)}"
