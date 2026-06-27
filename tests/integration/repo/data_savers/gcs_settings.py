import os
import uuid

from infra.repo.data_savers.object_storage_saver import ObjectStorageSaver
from infra.repo.object_storage import ObjectStorageConfig


def gcs_test_bucket() -> str:
    return os.getenv("GCS_TEST_BUCKET", "sexy_stock_test").strip()


def gcs_test_prefix() -> str:
    return os.getenv("GCS_TEST_PREFIX", "test/reoo").strip().strip("/")


def build_gcs_storage_config() -> ObjectStorageConfig:
    return ObjectStorageConfig.from_env()


def full_object_path(rel_path: str) -> str:
    return f"{gcs_test_bucket()}/{rel_path}"


def new_test_path_prefix() -> str:
    return f"{gcs_test_prefix()}/{uuid.uuid4().hex}"


def track_path(saver: ObjectStorageSaver, rel_path: str) -> None:
    saver._test_created_paths.append(rel_path)  # type: ignore[attr-defined]
