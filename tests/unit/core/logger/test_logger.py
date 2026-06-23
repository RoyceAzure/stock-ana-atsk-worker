import logging

import pytest

from core.logger.logger import parse_log_level, setup_logging


def test_parse_log_level_info():
    assert parse_log_level("info") == logging.INFO
    assert parse_log_level("INFO") == logging.INFO


def test_parse_log_level_debug():
    assert parse_log_level("debug") == logging.DEBUG


def test_parse_log_level_rejects_invalid():
    with pytest.raises(ValueError, match="不支援的 LOG_LEVEL"):
        parse_log_level("warning")


def test_setup_logging_debug_emits_debug_records(capsys):
    setup_logging("task-worker-preprocessing", level=logging.DEBUG)
    logging.getLogger("test.logger").debug("debug-msg")

    captured = capsys.readouterr().out.strip()
    assert '"level": "DEBUG"' in captured
    assert "debug-msg" in captured


def test_setup_logging_json_uses_timestamp_and_unicode_message(capsys):
    setup_logging("task-worker-preprocessing", level=logging.INFO)
    logging.getLogger("test.logger").info("資源釋放完成")

    captured = capsys.readouterr().out.strip()
    assert '"timestamp":' in captured
    assert '"asctime":' not in captured
    assert "資源釋放完成" in captured
    assert "\\u8cc7" not in captured


def test_setup_logging_info_suppresses_debug(capsys):
    setup_logging("task-worker-preprocessing", level=logging.INFO)
    logging.getLogger("test.logger").debug("hidden")
    logging.getLogger("test.logger").info("visible")

    captured = capsys.readouterr().out.strip()
    assert "hidden" not in captured
    assert "visible" in captured
