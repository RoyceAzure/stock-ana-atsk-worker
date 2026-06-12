import os
import uuid

from infra.repo.data_savers.object_storage_saver import ObjectStorageSaver
from infra.repo.object_storage import ObjectStorageConfig, StorageBackend

# --- 請填入 GCS 測試參數（環境變數可覆蓋）---
GCS_TEST_BUCKET = ""  # e.g. "my-test-bucket"
GCS_TEST_PREFIX = "pytest/object-storage-saver"
GCS_TEST_USE_ADC = True
GCS_HMAC_ACCESS_KEY = ""
GCS_HMAC_SECRET_KEY = ""


def gcs_test_bucket() -> str:
    return os.getenv("GCS_TEST_BUCKET", GCS_TEST_BUCKET).strip()


def gcs_test_prefix() -> str:
    return os.getenv("GCS_TEST_PREFIX", GCS_TEST_PREFIX).strip().strip("/")


def build_gcs_storage_config() -> ObjectStorageConfig:
    use_adc = os.getenv("GCS_USE_ADC")
    if use_adc is not None:
        use_adc_flag = use_adc.lower() in {"1", "true", "yes", "on"}
    else:
        use_adc_flag = GCS_TEST_USE_ADC

    return ObjectStorageConfig(
        backend=StorageBackend.GCS,
        use_adc=use_adc_flag,
        access_key=os.getenv("GCS_HMAC_ACCESS_KEY", GCS_HMAC_ACCESS_KEY) or None,
        secret_key=os.getenv("GCS_HMAC_SECRET_KEY", GCS_HMAC_SECRET_KEY) or None,
    )


def full_object_path(rel_path: str) -> str:
    return f"{gcs_test_bucket()}/{rel_path}"


def new_test_path_prefix() -> str:
    return f"{gcs_test_prefix()}/{uuid.uuid4().hex}"


def track_path(saver: ObjectStorageSaver, rel_path: str) -> None:
    saver._test_created_paths.append(rel_path)  # type: ignore[attr-defined]
