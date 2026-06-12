import json

import pandas as pd
import pytest

from infra.repo.data_savers.base import DataSaver
from infra.repo.data_savers.object_storage_saver import ObjectStorageSaver
from tests.integration.repo.data_savers.gcs_settings import full_object_path, track_path

pytestmark = [pytest.mark.integration, pytest.mark.integration_gcs]


class TestObjectStorageSaverGcs:
    def test_as_dict_reports_gcs_backend(self, gcs_saver: ObjectStorageSaver):
        info = gcs_saver.as_dict()
        assert info["saver_name"] == "ObjectStorageSaver"
        assert info["backend"] == "gcs"

    def test_save_file_bytes(self, gcs_saver: ObjectStorageSaver, gcs_test_path: str):
        rel_path = f"{gcs_test_path}/bytes.txt"
        track_path(gcs_saver, rel_path)
        payload = b"pytest-gcs-bytes"

        ok, err = gcs_saver.save_file(full_object_path(rel_path), payload)

        assert ok is True
        assert err is None
        uri = gcs_saver._object_uri(full_object_path(rel_path))
        assert gcs_saver.fs.exists(uri)
        with gcs_saver.fs.open(uri, "rb") as f:
            assert f.read() == payload

    def test_save_file_dataframe(self, gcs_saver: ObjectStorageSaver, gcs_test_path: str):
        rel_path = f"{gcs_test_path}/data.csv"
        track_path(gcs_saver, rel_path)
        df = pd.DataFrame({"code": ["2330"], "close": [580.0]})

        ok, err = gcs_saver.save_file(full_object_path(rel_path), df)

        assert ok is True
        assert err is None
        uri = gcs_saver._object_uri(full_object_path(rel_path))
        with gcs_saver.fs.open(uri, "rb") as f:
            content = f.read().decode("utf-8")
        assert "2330" in content
        assert "close" in content

    def test_save_file_empty_trade_result_writes_default_columns(
        self, gcs_saver: ObjectStorageSaver, gcs_test_path: str
    ):
        rel_path = f"{gcs_test_path}/empty_trade.csv"
        track_path(gcs_saver, rel_path)
        df = pd.DataFrame()

        ok, err = gcs_saver.save_file(full_object_path(rel_path), df, is_trade_result=True)

        assert ok is True
        assert err is None
        uri = gcs_saver._object_uri(full_object_path(rel_path))
        with gcs_saver.fs.open(uri, "rb") as f:
            content = f.read().decode("utf-8")
        for col in DataSaver.trade_result_default_column:
            assert col in content

    def test_save_file_rejects_empty_bytes(self, gcs_saver: ObjectStorageSaver, gcs_test_path: str):
        rel_path = f"{gcs_test_path}/empty.bin"
        track_path(gcs_saver, rel_path)

        ok, err = gcs_saver.save_file(full_object_path(rel_path), b"")

        assert ok is None
        assert err == "Buffer is empty"

    def test_append_to_file_creates_new_json(self, gcs_saver: ObjectStorageSaver, gcs_test_path: str):
        rel_path = f"{gcs_test_path}/meta.json"
        track_path(gcs_saver, rel_path)

        ok, err = gcs_saver.append_to_file(full_object_path(rel_path), {"task_id": "t-1"})

        assert ok is True
        assert err is None
        uri = gcs_saver._object_uri(full_object_path(rel_path))
        with gcs_saver.fs.open(uri, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
        assert data == {"task_id": "t-1"}

    def test_append_to_file_merges_existing_json(self, gcs_saver: ObjectStorageSaver, gcs_test_path: str):
        rel_path = f"{gcs_test_path}/merge.json"
        track_path(gcs_saver, rel_path)

        first_ok, first_err = gcs_saver.append_to_file(full_object_path(rel_path), {"a": 1})
        second_ok, second_err = gcs_saver.append_to_file(full_object_path(rel_path), {"b": 2})

        assert first_ok is True and first_err is None
        assert second_ok is True and second_err is None

        uri = gcs_saver._object_uri(full_object_path(rel_path))
        with gcs_saver.fs.open(uri, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
        assert data == {"a": 1, "b": 2}
