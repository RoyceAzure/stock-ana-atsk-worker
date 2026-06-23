import json
import uuid

import pytest
from pydantic import ValidationError

from models.task_message import TaskMessage


def test_task_message_from_json():
    task_id = uuid.uuid4()
    raw = json.dumps({"task_id": str(task_id)}).encode("utf-8")

    message = TaskMessage.model_validate(json.loads(raw.decode("utf-8")))

    assert message.task_id == task_id


def test_task_message_rejects_missing_task_id():
    with pytest.raises(ValidationError):
        TaskMessage.model_validate({})


def test_task_message_rejects_invalid_uuid():
    with pytest.raises(ValidationError):
        TaskMessage.model_validate({"task_id": "not-a-uuid"})
