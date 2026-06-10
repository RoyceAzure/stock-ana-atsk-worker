from typing import Any

from pytest_mock import MockerFixture

TASK_COORDINATOR_METHODS = ("execute",)


def create_task_coordinator_mock(
    mocker: MockerFixture,
    *,
    execute_side_effect: Any = None,
) -> Any:
    """建立 ITaskCoordinator Protocol 的 mock。

    Args:
        mocker: pytest-mock 提供的 fixture
        execute_side_effect: execute 自訂行為

    Returns:
        符合 ITaskCoordinator 介面的 MagicMock
    """
    mock = mocker.Mock(spec=TASK_COORDINATOR_METHODS)

    if execute_side_effect is not None:
        mock.execute.side_effect = execute_side_effect
    else:
        mock.execute.return_value = None

    return mock
