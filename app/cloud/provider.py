from __future__ import annotations

from enum import Enum


class CloudProvider(str, Enum):
    """雲端廠商：決定 queue consumer 與物件儲存模組組裝路徑。"""

    GCP = "gcp"
    AWS = "aws"
