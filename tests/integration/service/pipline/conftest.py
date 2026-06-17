import pytest

from infra.repo.data_meger.blob_parquet_meger import BlobParquetMerger
from infra.repo.duckdb_manager import DuckDBManager
from tests.integration.repo.duckdb.conftest import gcs_test_bucket
from tests.integration.service.pipline.trade_price_factory import (
    build_trade_price_input_df,
    build_trade_price_merge_input_df,
)

pytest_plugins = ["tests.integration.repo.duckdb.conftest"]


@pytest.fixture
def trade_price_input_df():
    return build_trade_price_input_df()


@pytest.fixture
def mock_sql_loader(mocker, trade_price_input_df):
    loader = mocker.Mock()
    loader.query_data.return_value = (trade_price_input_df, None)
    mocker.patch(
        "service.pipline.pandas_trade_price_pipline.SQLLoader",
        return_value=loader,
    )
    return loader


@pytest.fixture
def mock_sql_loader_merge_only(mocker):
    loader = mocker.Mock()
    loader.query_data.return_value = (build_trade_price_merge_input_df(), None)
    mocker.patch(
        "service.pipline.pandas_trade_price_pipline.SQLLoader",
        return_value=loader,
    )
    return loader


@pytest.fixture
def parquet_merger(gcs_fs, gcs_duckdb_config):
    merger = BlobParquetMerger(gcs_fs, gcs_test_bucket(), gcs_duckdb_config)
    yield merger
    DuckDBManager.return_conn(merger.duckdb_con)
