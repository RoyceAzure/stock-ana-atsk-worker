from __future__ import annotations

from enum import Enum


class WorkerMode(str, Enum):
    """main 入口執行模式（瑞士刀）。"""

    CONSUMER = "consumer"
    ONESHOT = "oneshot"
    MIGRATE = "migrate"
    HEALTH = "health"
