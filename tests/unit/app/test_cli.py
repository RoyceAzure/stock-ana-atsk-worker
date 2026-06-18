import pytest

from app.cli import main, parse_args
from app.mode import WorkerMode


def test_parse_args_defaults_to_consumer(monkeypatch):
    monkeypatch.delenv("WORKER_MODE", raising=False)
    args = parse_args([])
    assert args.mode == WorkerMode.CONSUMER.value


def test_parse_args_reads_worker_mode_env(monkeypatch):
    monkeypatch.setenv("WORKER_MODE", WorkerMode.CONSUMER.value)
    args = parse_args([])
    assert args.mode == WorkerMode.CONSUMER.value


def test_parse_args_cli_overrides_env(monkeypatch):
    monkeypatch.setenv("WORKER_MODE", WorkerMode.MIGRATE.value)
    args = parse_args(["--mode", WorkerMode.CONSUMER.value])
    assert args.mode == WorkerMode.CONSUMER.value


def test_main_rejects_unimplemented_mode():
    exit_code = main(["--mode", WorkerMode.MIGRATE.value])
    assert exit_code == 2


def test_main_runs_consumer_mode(monkeypatch):
    calls: list[str] = []

    class FakeApplication:
        def run(self) -> None:
            calls.append("run")

    monkeypatch.setattr("app.cli.Application", FakeApplication)
    exit_code = main(["--mode", WorkerMode.CONSUMER.value])
    assert exit_code == 0
    assert calls == ["run"]
