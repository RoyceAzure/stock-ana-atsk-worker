from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, Sequence

from app.application import Application
from app.mode import WorkerMode

_DEFAULT_MODE_ENV_KEY = "WORKER_MODE"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock-ana-task-worker",
        description="stock-ana-task-worker",
    )
    supported_modes = ", ".join(mode.value for mode in WorkerMode)
    default_mode = os.getenv(_DEFAULT_MODE_ENV_KEY, WorkerMode.CONSUMER.value)
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in WorkerMode],
        default=default_mode,
        help=(
            f"執行模式（預設: {WorkerMode.CONSUMER.value}，"
            f"亦可設環境變數 {_DEFAULT_MODE_ENV_KEY}）。支援: {supported_modes}"
        ),
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def run_mode(mode: WorkerMode) -> None:
    if mode is WorkerMode.CONSUMER:
        Application().run()
        return

    if mode is WorkerMode.ONESHOT:
        raise NotImplementedError("oneshot 模式尚未實作")

    if mode is WorkerMode.MIGRATE:
        raise NotImplementedError("migrate 模式尚未實作")

    if mode is WorkerMode.HEALTH:
        raise NotImplementedError("health 模式尚未實作")

    raise ValueError(f"不支援的 mode: {mode.value}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        mode = WorkerMode(args.mode)
    except ValueError as exc:
        supported = ", ".join(item.value for item in WorkerMode)
        print(
            f"不支援的 --mode: {args.mode}（支援: {supported}）",
            file=sys.stderr,
        )
        return 2

    try:
        run_mode(mode)
    except NotImplementedError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130

    return 0
