import os
from typing import Generator

import psycopg2
import pytest
from psycopg2 import OperationalError

from infra.repo.pg_dao import DBConfig, DatabaseRepository

pytest_plugins = ["tests.mocks.conftest"]


def _db_config() -> DBConfig:
    return DBConfig(
        host=os.getenv("PG_HOST", "localhost"),
        database=os.getenv("PG_DATABASE", "sexy_stock"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", "password"),
        port=int(os.getenv("PG_PORT", "5432")),
    )


@pytest.fixture(scope="session")
def pg_config() -> DBConfig:
    return _db_config()


@pytest.fixture(scope="session")
def pg_connection(pg_config: DBConfig) -> Generator[psycopg2.extensions.connection, None, None]:
    try:
        conn = psycopg2.connect(**pg_config.as_dict())
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL 無法連線: {exc}")

    yield conn
    conn.close()


@pytest.fixture
def db_conn(pg_connection: psycopg2.extensions.connection) -> Generator[psycopg2.extensions.connection, None, None]:
    yield pg_connection
    pg_connection.rollback()


@pytest.fixture
def repo(db_conn: psycopg2.extensions.connection) -> DatabaseRepository:
    return DatabaseRepository(db_conn)
