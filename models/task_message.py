import uuid

from pydantic import Field

from models.basemodel import BaseModelWithConfig


class TaskMessage(BaseModelWithConfig):
    """Pub/Sub 任務訊息格式（JSON）。"""

    task_id: uuid.UUID = Field(..., description="任務 ID")
