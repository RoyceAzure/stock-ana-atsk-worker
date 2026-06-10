import uuid
from typing import Any, Optional
from unittest.mock import PropertyMock

from pytest_mock import MockerFixture

from models.task_result import ConsumerResult, TaskResult

TASK_HANDLER_METHODS = (
    "process",
    "set_stage",
)


def create_task_handler_mock(
    mocker: MockerFixture,
    *,
    stage: str = "preprocessing",
    process_return: Optional[TaskResult] = None,
    process_side_effect: Any = None,
) -> Any:
    """建立 TaskHandler 的 mock。

    Args:
        mocker: pytest-mock 提供的 fixture
        stage: 預設任務階段（EventStage 值）
        process_return: process 預設回傳值
        process_side_effect: process 自訂行為

    Returns:
        符合 TaskHandler 介面的 MagicMock
    """
    mock = mocker.Mock(spec=TASK_HANDLER_METHODS)
    mock.event_stage = stage
    type(mock).get_stage = PropertyMock(return_value=stage)

    if process_side_effect is not None:
        mock.process.side_effect = process_side_effect
    else:
        mock.process.return_value = process_return or TaskResult(
            id=str(uuid.uuid4()),
            is_successed=ConsumerResult.SUCCESSED,
        )

    def _set_stage(new_stage: str) -> None:
        mock.event_stage = new_stage
        type(mock).get_stage = PropertyMock(return_value=new_stage)

    mock.set_stage.side_effect = _set_stage

    return mock
