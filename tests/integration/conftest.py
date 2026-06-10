from typing import Generator

import psycopg2.extensions
import pytest

PYTEST_TRIGGERED_BY = "pytest"


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
