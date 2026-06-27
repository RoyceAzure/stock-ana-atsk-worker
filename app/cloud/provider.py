from __future__ import annotations

from enum import Enum


class CloudProvider(str, Enum):
    """雲端廠商：目前僅實作 GCP（Pub/Sub + GCS）。"""

    GCP = "gcp"
