import os
import uuid
from pathlib import Path
from typing import Generator, List

import duckdb
import pytest
from dotenv import load_dotenv

from infra.repo.duckdb.gcs_config import GcsDuckDBConfig
from infra.repo.duckdb_manager import DuckDBManager
from infra.repo.object_storage import ObjectStorageConfig, StorageBackend, create_filesystem, to_fs_uri

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# --- DuckDB GCS 整合測試參數（環境變數或 .env 可覆蓋）---
# 憑證：GCS_HMAC_ACCESS_KEY / GCS_HMAC_SECRET_KEY（非 gcloud auth，需於 GCP 建立 HMAC 金鑰）
GCS_TEST_BUCKET = "sexy_stock_test"
GCS_TEST_PREFIX = "test/duckdb"
GCS_HMAC_ACCESS_KEY = ""
GCS_HMAC_SECRET_KEY = ""


def gcs_test_bucket() -> str:
    return os.getenv("GCS_TEST_BUCKET", GCS_TEST_BUCKET).strip()


def gcs_test_prefix() -> str:
    return os.getenv("GCS_TEST_PREFIX", GCS_TEST_PREFIX).strip().strip("/")


def build_gcs_duckdb_config() -> GcsDuckDBConfig:
    access_key = os.getenv("GCS_HMAC_ACCESS_KEY", GCS_HMAC_ACCESS_KEY) or None
    secret_key = os.getenv("GCS_HMAC_SECRET_KEY", GCS_HMAC_SECRET_KEY) or None
    if not access_key or not secret_key:
        raise ValueError("GCS HMAC 模式需設定 GCS_HMAC_ACCESS_KEY 與 GCS_HMAC_SECRET_KEY")
    return GcsDuckDBConfig(hmac_access_key=access_key, hmac_secret_key=secret_key)


def build_gcs_storage_config() -> ObjectStorageConfig:
    """fsspec 用設定（HMAC + S3 互通）。"""
    return ObjectStorageConfig(
        backend=StorageBackend.GCS,
        use_adc=False,
        access_key=os.getenv("GCS_HMAC_ACCESS_KEY", GCS_HMAC_ACCESS_KEY) or None,
        secret_key=os.getenv("GCS_HMAC_SECRET_KEY", GCS_HMAC_SECRET_KEY) or None,
    )


def new_test_path_prefix() -> str:
    return f"{gcs_test_prefix()}/{uuid.uuid4().hex}"


def track_gcs_path(created_paths: List[str], rel_path: str) -> None:
    created_paths.append(rel_path)


def _ensure_gcs_hmac_credentials() -> None:
    access_key = os.getenv("GCS_HMAC_ACCESS_KEY", GCS_HMAC_ACCESS_KEY)
    secret_key = os.getenv("GCS_HMAC_SECRET_KEY", GCS_HMAC_SECRET_KEY)
    if not access_key or not secret_key:
        msg = "DuckDB GCS 測試需設定 GCS_HMAC_ACCESS_KEY 與 GCS_HMAC_SECRET_KEY"
        print(f"[duckdb-gcs] {msg}")
        pytest.skip(msg)

    print("[duckdb-gcs] HMAC 金鑰已設定")


@pytest.fixture(scope="module")
def gcs_duckdb_config() -> GcsDuckDBConfig:
    if not gcs_test_bucket():
        msg = "請設定 GCS_TEST_BUCKET（tests/integration/repo/duckdb/conftest.py 或環境變數）"
        print(f"[duckdb-gcs] {msg}")
        pytest.skip(msg)

    _ensure_gcs_hmac_credentials()
    return build_gcs_duckdb_config()


@pytest.fixture(scope="module")
def gcs_storage_config() -> ObjectStorageConfig:
    if not gcs_test_bucket():
        msg = "請設定 GCS_TEST_BUCKET（tests/integration/repo/duckdb/conftest.py 或環境變數）"
        print(f"[duckdb-gcs] {msg}")
        pytest.skip(msg)

    _ensure_gcs_hmac_credentials()
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
