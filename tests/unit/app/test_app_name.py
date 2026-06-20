from models.task_event import EventName

from app.task.profile import TaskWorkerProfile


def test_app_name_single_type():
    profile = TaskWorkerProfile(enabled_event_names=frozenset({EventName.PREPROCESS}))
    assert profile.app_name == "task-worker-preprocessing"


def test_app_name_multiple_types():
    profile = TaskWorkerProfile(
        enabled_event_names=frozenset({EventName.PREPROCESS, EventName.BACKTEST})
    )
    assert profile.app_name == "task-worker-backtesting,preprocessing"
