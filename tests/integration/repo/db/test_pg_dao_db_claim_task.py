import uuid

import psycopg2.extensions
import pytest

from infra.repo.pg_dao import DatabaseRepository
from tests.integration.repo.db.task_event_factory import TaskEventFactory

pytestmark = pytest.mark.integration


class TestDbClaimTask:
    def test_claim_pending_task_success(
        self,
        repo: DatabaseRepository,
        task_event_factory: TaskEventFactory,
        db_conn: psycopg2.extensions.connection,
    ):
        task_id = task_event_factory.create(status="pending")

        result = repo.db_claim_task(str(task_id))

        assert result is not None
        assert str(result["id"]) == str(task_id)
        assert result["status"] == "running"

        with db_conn.cursor() as cur:
            cur.execute("SELECT status FROM task_event WHERE id = %s", (str(task_id),))
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "running"

    def test_claim_nonexistent_task_returns_none(self, repo: DatabaseRepository):
        result = repo.db_claim_task(str(uuid.uuid4()))
        assert result is None

    @pytest.mark.parametrize("status", ["running", "completed", "failed"])
    def test_claim_non_pending_task_returns_none(
        self,
        repo: DatabaseRepository,
        task_event_factory: TaskEventFactory,
        status: str,
    ):
        task_id = task_event_factory.create(status=status)

        result = repo.db_claim_task(str(task_id))

        assert result is None

    def test_claim_same_task_twice_only_first_succeeds(
        self,
        repo: DatabaseRepository,
        task_event_factory: TaskEventFactory,
    ):
        task_id = task_event_factory.create(status="pending")

        first = repo.db_claim_task(str(task_id))
        second = repo.db_claim_task(str(task_id))

        assert first is not None
        assert first["status"] == "running"
        assert second is None

    def test_claim_updates_updated_at(
        self,
        repo: DatabaseRepository,
        task_event_factory: TaskEventFactory,
        db_conn: psycopg2.extensions.connection,
    ):
        task_id = task_event_factory.create(status="pending")

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT updated_at FROM task_event WHERE id = %s",
                (str(task_id),),
            )
            before = cur.fetchone()[0]

        result = repo.db_claim_task(str(task_id))
        assert result is not None

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT updated_at FROM task_event WHERE id = %s",
                (str(task_id),),
            )
            after = cur.fetchone()[0]

        assert after >= before

    def test_task_event_cleaned_up_after_test(
        self,
        task_event_factory: TaskEventFactory,
        db_conn: psycopg2.extensions.connection,
    ):
        task_id = task_event_factory.create(status="pending")

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM task_event WHERE id = %s",
                (str(task_id),),
            )
            assert cur.fetchone()[0] == 1

        task_event_factory.cleanup()

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM task_event WHERE id = %s",
                (str(task_id),),
            )
            assert cur.fetchone()[0] == 0
