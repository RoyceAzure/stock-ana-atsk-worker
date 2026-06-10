import uuid

from pytest_mock import MockerFixture

from models.task_result import ConsumerResult, TaskResult
from tests.mocks.service.task.handler import create_task_handler_mock


class TestTaskHandlerMock:
    def test_default_mock_exposes_handler_interface(self, mocker: MockerFixture):
        handler = create_task_handler_mock(mocker)
        task_event = mocker.Mock()

        result = handler.process(task_event)

        assert isinstance(result, TaskResult)
        assert result.is_successed == ConsumerResult.SUCCESSED
        assert handler.get_stage == "preprocessing"
        assert handler.event_stage == "preprocessing"
        handler.process.assert_called_once_with(task_event)

    def test_set_stage_updates_stage(self, mocker: MockerFixture):
        handler = create_task_handler_mock(mocker, stage="init")

        handler.set_stage("backtesting")

        assert handler.get_stage == "backtesting"
        assert handler.event_stage == "backtesting"
        handler.set_stage.assert_called_once_with("backtesting")

    def test_custom_process_return(self, mocker: MockerFixture):
        task_id = str(uuid.uuid4())
        expected = TaskResult(
            id=task_id,
            is_successed=ConsumerResult.FAILED,
            message="failed",
        )
        handler = create_task_handler_mock(mocker, process_return=expected)

        result = handler.process(mocker.Mock())

        assert result.id == task_id
        assert result.message == "failed"

    def test_mock_fixture_available(self, mock_task_handler, mocker):
        mock_task_handler.process(mocker.Mock())

        mock_task_handler.process.assert_called_once()
