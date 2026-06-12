from typing import Generator, List

import pytest

from infra.repo.data_savers.object_storage_saver import ObjectStorageSaver
from infra.repo.object_storage import ObjectStorageConfig, to_fs_uri
from tests.integration.repo.data_savers.gcs_settings import (
    build_gcs_storage_config,
    gcs_test_bucket,
    gcs_test_prefix,
    new_test_path_prefix,
)


@pytest.fixture(scope="module")
def gcs_storage_config() -> ObjectStorageConfig:
    if not gcs_test_bucket():
        pytest.skip(
            "請設定 GCS_TEST_BUCKET（tests/integration/repo/data_savers/gcs_settings.py 或環境變數）"
        )
    config = build_gcs_storage_config()
    if not config.use_adc and (not config.access_key or not config.secret_key):
        pytest.skip("GCS HMAC 模式需設定 GCS_HMAC_ACCESS_KEY 與 GCS_HMAC_SECRET_KEY")
    return config


@pytest.fixture
def gcs_saver(gcs_storage_config: ObjectStorageConfig) -> Generator[ObjectStorageSaver, None, None]:
    saver = ObjectStorageSaver(gcs_storage_config)
    created_paths: List[str] = []
    saver._test_created_paths = created_paths  # type: ignore[attr-defined]
    yield saver

    bucket = gcs_test_bucket()
    prefix = gcs_test_prefix()
    for rel_path in created_paths:
        uri = to_fs_uri(gcs_storage_config, f"{bucket}/{rel_path}")
        try:
            if saver.fs.exists(uri):
                saver.fs.rm(uri)
        except Exception:
            pass

    try:
        for path in saver.fs.glob(f"{bucket}/{prefix}/**"):
            try:
                saver.fs.rm(path)
            except Exception:
                pass
    except Exception:
        pass


@pytest.fixture
def gcs_test_path() -> str:
    return new_test_path_prefix()
