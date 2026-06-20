import logging

from core.logger.logger import setup_logging


def test_setup_logging_includes_app_and_level(capsys):
    setup_logging("task-worker-preprocessing")
    logging.getLogger("test.logger").info("hello")

    captured = capsys.readouterr().out.strip()
    assert '"app": "task-worker-preprocessing"' in captured
    assert '"level": "INFO"' in captured
    assert "levelname" not in captured
