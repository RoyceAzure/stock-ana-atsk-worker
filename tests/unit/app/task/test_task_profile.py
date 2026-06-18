import pytest

from app.task.profile import TaskWorkerProfile
from models.task_event import EventName


def test_from_env_defaults_to_preprocess(monkeypatch):
    monkeypatch.delenv("WORKER_TASK_TYPES", raising=False)
    profile = TaskWorkerProfile.from_env()
    assert profile.enabled_event_names == frozenset({EventName.PREPROCESS})


def test_from_env_parses_multiple_types(monkeypatch):
    monkeypatch.setenv(
        "WORKER_TASK_TYPES",
        "preprocessing, backtesting",
    )
    profile = TaskWorkerProfile.from_env()
    assert profile.enabled_event_names == frozenset(
        {EventName.PREPROCESS, EventName.BACKTEST}
    )


def test_from_env_rejects_unknown_type(monkeypatch):
    monkeypatch.setenv("WORKER_TASK_TYPES", "unknown_task")
    with pytest.raises(ValueError, match="不支援的 WORKER_TASK_TYPES"):
        TaskWorkerProfile.from_env()


def test_from_env_rejects_empty_string(monkeypatch):
    monkeypatch.setenv("WORKER_TASK_TYPES", "  ,  ")
    with pytest.raises(ValueError, match="WORKER_TASK_TYPES 不可為空"):
        TaskWorkerProfile.from_env()


def test_enabled_values_sorted(monkeypatch):
    monkeypatch.setenv("WORKER_TASK_TYPES", "backtesting,preprocessing")
    profile = TaskWorkerProfile.from_env()
    assert profile.enabled_values == ("backtesting", "preprocessing")
