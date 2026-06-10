from typing import Any, Generator

import pytest
from pytest_mock import MockerFixture

from tests.mocks.service.task.handler import create_task_handler_mock
from tests.mocks.service.task.task_coordinator import create_task_coordinator_mock
from tests.mocks.service.taskevent.helper import create_task_event_helper_mock


@pytest.fixture
def mock_task_event_helper(mocker: MockerFixture) -> Generator[Any, None, None]:
    """TaskEventHelper Protocol 的預設 mock fixture。"""
    yield create_task_event_helper_mock(mocker)


@pytest.fixture
def mock_task_handler(mocker: MockerFixture) -> Generator[Any, None, None]:
    """TaskHandler 的預設 mock fixture。"""
    yield create_task_handler_mock(mocker)


@pytest.fixture
def mock_task_coordinator(mocker: MockerFixture) -> Generator[Any, None, None]:
    """ITaskCoordinator Protocol 的預設 mock fixture。"""
    yield create_task_coordinator_mock(mocker)
