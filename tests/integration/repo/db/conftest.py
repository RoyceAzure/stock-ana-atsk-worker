from typing import Generator

import psycopg2.extensions
import pytest

from tests.integration.repo.db.task_event_factory import PYTEST_TRIGGERED_BY, TaskEventFactory


def _delete_pytest_task_events(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM task_event WHERE triggered_by = %s",
            (PYTEST_TRIGGERED_BY,),
        )
    conn.commit()


@pytest.fixture(autouse=True)
def cleanup_task_event_test_data(
    db_conn: psycopg2.extensions.connection,
) -> Generator[None, None, None]:
    _delete_pytest_task_events(db_conn)
    yield
    _delete_pytest_task_events(db_conn)


@pytest.fixture
def task_event_factory(
    db_conn: psycopg2.extensions.connection,
) -> Generator[TaskEventFactory, None, None]:
    factory = TaskEventFactory(db_conn)
    yield factory
    factory.cleanup()
