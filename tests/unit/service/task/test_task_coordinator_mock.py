from pytest_mock import MockerFixture

from tests.mocks.service.task.task_coordinator import create_task_coordinator_mock


class TestTaskCoordinatorMock:
    def test_default_mock_exposes_execute(self, mocker: MockerFixture):
        coordinator = create_task_coordinator_mock(mocker)
        task_event = mocker.Mock()

        coordinator.execute(task_event)

        coordinator.execute.assert_called_once_with(task_event)

    def test_execute_side_effect(self, mocker: MockerFixture):
        coordinator = create_task_coordinator_mock(
            mocker,
            execute_side_effect=RuntimeError("boom"),
        )
        task_event = mocker.Mock()

        try:
            coordinator.execute(task_event)
            assert False, "應拋出例外"
        except RuntimeError as exc:
            assert str(exc) == "boom"

    def test_mock_fixture_available(self, mock_task_coordinator, mocker):
        task_event = mocker.Mock()

        mock_task_coordinator.execute(task_event)

        mock_task_coordinator.execute.assert_called_once_with(task_event)
