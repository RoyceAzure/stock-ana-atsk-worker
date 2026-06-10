import uuid

from pytest_mock import MockerFixture

from models.task_result import ConsumerResult, TaskResult
from tests.mocks.service.taskevent.helper import create_task_event_helper_mock


class TestTaskEventHelperMock:
    def test_default_mock_exposes_protocol_methods(self, mocker: MockerFixture):
        helper = create_task_event_helper_mock(mocker)

        helper.handle_success(
            TaskResult(id=str(uuid.uuid4()), is_successed=ConsumerResult.SUCCESSED),
            "preprocessing",
        )
        helper.handle_error(str(uuid.uuid4()), "preprocessing", RuntimeError("err"))
        helper.update_task_event(
            str(uuid.uuid4()),
            "completed",
            "preprocessing",
        )

        helper.handle_success.assert_called_once()
        helper.handle_error.assert_called_once()
        helper.update_task_event.assert_called_once()

    def test_mock_fixture_available(self, mock_task_event_helper):
        mock_task_event_helper.handle_success.return_value = None

        mock_task_event_helper.handle_success(
            TaskResult(id=str(uuid.uuid4()), is_successed=ConsumerResult.SUCCESSED),
            "preprocessing",
        )

        mock_task_event_helper.handle_success.assert_called_once()
