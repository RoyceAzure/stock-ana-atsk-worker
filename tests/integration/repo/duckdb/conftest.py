import os
import uuid
from pathlib import Path
from typing import Generator, List

import duckdb
import google.auth
import pytest
from dotenv import load_dotenv

from infra.repo.duckdb.gcs_config import GcsDuckDBConfig
from infra.repo.duckdb_manager import DuckDBManager
from infra.repo.gcp.gcp_auth import GcpAuthMode, gcp_auth_mode_from_env, resolve_service_account_key_file
from infra.repo.object_storage import ObjectStorageConfig, create_filesystem, to_fs_uri

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_PROJECT_ROOT / ".env", override=False)

GCS_TEST_BUCKET = "sexy_stock_test"
GCS_TEST_PREFIX = "test/duckdb"


def gcs_test_bucket() -> str:
    return os.getenv("GCS_TEST_BUCKET", GCS_TEST_BUCKET).strip()


def gcs_test_prefix() -> str:
    return os.getenv("GCS_TEST_PREFIX", GCS_TEST_PREFIX).strip().strip("/")


def build_gcs_duckdb_config() -> GcsDuckDBConfig:
    return GcsDuckDBConfig.from_env()


def build_gcs_storage_config() -> ObjectStorageConfig:
    return ObjectStorageConfig.from_env()


def new_test_path_prefix() -> str:
    return f"{gcs_test_prefix()}/{uuid.uuid4().hex}"


def track_gcs_path(created_paths: List[str], rel_path: str) -> None:
    created_paths.append(rel_path)


def _ensure_gcs_credentials() -> None:
    if gcp_auth_mode_from_env() is GcpAuthMode.SERVICE_ACCOUNT_JSON:
        resolve_service_account_key_file()
        return
    try:
        google.auth.default()
    except Exception as exc:
        msg = (
            "DuckDB GCS 整合測試需 ADC（gcloud auth application-default login）"
            f"或 GCP_SA_KEY_FILE: {exc}"
        )
        print(f"[duckdb-gcs] {msg}")
        pytest.skip(msg)


@pytest.fixture(scope="module")
def gcs_duckdb_config() -> GcsDuckDBConfig:
    if not gcs_test_bucket():
        msg = "請設定 GCS_TEST_BUCKET（tests/integration/repo/duckdb/conftest.py 或環境變數）"
        print(f"[duckdb-gcs] {msg}")
        pytest.skip(msg)

    _ensure_gcs_credentials()
    return build_gcs_duckdb_config()


@pytest.fixture(scope="module")
def gcs_storage_config() -> ObjectStorageConfig:
    if not gcs_test_bucket():
        msg = "請設定 GCS_TEST_BUCKET（tests/integration/repo/duckdb/conftest.py 或環境變數）"
        print(f"[duckdb-gcs] {msg}")
        pytest.skip(msg)

    _ensure_gcs_credentials()
    return build_gcs_storage_config()


@pytest.fixture(scope="module")
def duckdb_manager_gcs(gcs_duckdb_config: GcsDuckDBConfig) -> Generator[None, None, None]:
    DuckDBManager.initialize(gcs_duckdb_config, pool_size=2)
    yield
    DuckDBManager.close_all()


@pytest.fixture
def duckdb_conn(duckdb_manager_gcs) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    conn = DuckDBManager.get_conn()
    yield conn
    DuckDBManager.return_conn(conn)


@pytest.fixture
def gcs_fs(gcs_storage_config: ObjectStorageConfig):
    return create_filesystem(gcs_storage_config)


@pytest.fixture
def gcs_test_path() -> str:
    return new_test_path_prefix()


@pytest.fixture
def gcs_created_paths() -> List[str]:
    return []


@pytest.fixture(autouse=True)
def cleanup_gcs_duckdb_objects(
    gcs_storage_config: ObjectStorageConfig,
    gcs_fs,
    gcs_created_paths: List[str],
) -> Generator[None, None, None]:
    yield

    bucket = gcs_test_bucket()
    prefix = gcs_test_prefix()
    for rel_path in gcs_created_paths:
        uri = to_fs_uri(gcs_storage_config, f"{bucket}/{rel_path}")
        try:
            if gcs_fs.exists(uri):
                gcs_fs.rm(uri)
        except Exception:
            pass

    try:
        for path in gcs_fs.glob(f"{bucket}/{prefix}/**"):
            try:
                gcs_fs.rm(path)
            except Exception:
                pass
    except Exception:
        pass
