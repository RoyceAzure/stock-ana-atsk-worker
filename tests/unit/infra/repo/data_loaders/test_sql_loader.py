import pytest
from decimal import Decimal

import pandas as pd

from infra.repo.data_loaders.sql_loader import _coerce_ohlc_columns, _parse_code_list


def test_parse_code_list_from_quoted_json_strings():
    assert _parse_code_list('["1103", "1104"]') == ["1103", "1104"]


def test_parse_code_list_from_unquoted_json_numbers():
    assert _parse_code_list("[2330, 2317]") == ["2330", "2317"]


def test_parse_code_list_from_single_string():
    assert _parse_code_list("2330") == ["2330"]


def test_parse_code_list_from_python_list_with_ints():
    assert _parse_code_list([2330, 2317]) == ["2330", "2317"]


def test_parse_code_list_empty_json_array():
    assert _parse_code_list("[]") == []


def test_coerce_ohlc_columns_from_decimal():
    df = pd.DataFrame(
        {
            "open": [Decimal("100.50")],
            "high": [Decimal("101.00")],
            "low": [Decimal("99.25")],
            "close": [Decimal("100.75")],
        }
    )

    result = _coerce_ohlc_columns(df)

    assert result["open"].dtype == "float64"
    assert result["high"].dtype == "float64"
    assert result["low"].dtype == "float64"
    assert result["close"].dtype == "float64"
    assert result.loc[0, "open"] == 100.5
