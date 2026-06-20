import logging

from core.logger.logger import setup_logging
from core.logger.task_context import task_log_context


def test_task_log_context_injects_structured_field(capsys):
    setup_logging("task-worker-preprocessing", level=logging.INFO)
    task_id = "550e8400-e29b-41d4-a716-446655440000"

    with task_log_context(task_id):
        logging.getLogger("service.task").info("processing")

    captured = capsys.readouterr().out.strip()
    assert f'"task_event_id": "{task_id}"' in captured
    assert '"message": "processing"' in captured


def test_task_log_context_omitted_outside_scope(capsys):
    setup_logging("task-worker-preprocessing", level=logging.INFO)
    logging.getLogger("service.consumer").info("啟動 worker")

    captured = capsys.readouterr().out.strip()
    assert "task_event_id" not in captured
