from typing import Any

from pytest_mock import MockerFixture

TASK_EVENT_HELPER_METHODS = (
    "handle_success",
    "handle_error",
    "update_task_event",
)


def create_task_event_helper_mock(
    mocker: MockerFixture,
    *,
    handle_success_side_effect: Any = None,
    handle_error_side_effect: Any = None,
    update_task_event_side_effect: Any = None,
) -> Any:
    """建立 TaskEventHelper Protocol 的 mock。

    Args:
        mocker: pytest-mock 提供的 fixture
        handle_success_side_effect: handle_success 自訂行為
        handle_error_side_effect: handle_error 自訂行為
        update_task_event_side_effect: update_task_event 自訂行為

    Returns:
        符合 TaskEventHelper 介面的 MagicMock
    """
    mock = mocker.Mock(spec=TASK_EVENT_HELPER_METHODS)

    if handle_success_side_effect is not None:
        mock.handle_success.side_effect = handle_success_side_effect
    else:
        mock.handle_success.return_value = None

    if handle_error_side_effect is not None:
        mock.handle_error.side_effect = handle_error_side_effect
    else:
        mock.handle_error.return_value = None

    if update_task_event_side_effect is not None:
        mock.update_task_event.side_effect = update_task_event_side_effect
    else:
        mock.update_task_event.return_value = None

    return mock
