from unittest.mock import MagicMock

import pytest

from infra.repo.duckdb.gcs_auth_retry import is_gcs_auth_error, with_gcs_auth_retry


class TestIsGcsAuthError:
    @pytest.mark.parametrize(
        "message",
        [
            "Unauthorized (HTTP code 401)",
            "HTTP 403 Forbidden",
            "invalid access token",
            "Authentication failed",
        ],
    )
    def test_detects_auth_errors(self, message):
        assert is_gcs_auth_error(RuntimeError(message)) is True

    def test_ignores_non_auth_errors(self):
        assert is_gcs_auth_error(RuntimeError("integer cast error")) is False


class TestWithGcsAuthRetry:
    def test_returns_result_without_retry_on_success(self, mocker):
        refresh = mocker.patch(
            "infra.repo.duckdb.gcs_auth_retry.DuckDBManager.refresh_gcs_auth"
        )
        conn = MagicMock()
        result = with_gcs_auth_retry(conn, lambda: "ok")
        assert result == "ok"
        refresh.assert_not_called()

    def test_refreshes_once_on_auth_error_then_succeeds(self, mocker):
        refresh = mocker.patch(
            "infra.repo.duckdb.gcs_auth_retry.DuckDBManager.refresh_gcs_auth"
        )
        conn = MagicMock()
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("Unauthorized (HTTP code 401)")
            return "ok"

        result = with_gcs_auth_retry(conn, flaky)
        assert result == "ok"
        refresh.assert_called_once_with(conn)

    def test_raises_after_auth_retry_still_fails(self, mocker):
        mocker.patch(
            "infra.repo.duckdb.gcs_auth_retry.DuckDBManager.refresh_gcs_auth"
        )
        conn = MagicMock()

        def always_fail():
            raise RuntimeError("Unauthorized (HTTP code 401)")

        with pytest.raises(RuntimeError, match="Unauthorized"):
            with_gcs_auth_retry(conn, always_fail)

    def test_does_not_retry_non_auth_errors(self, mocker):
        refresh = mocker.patch(
            "infra.repo.duckdb.gcs_auth_retry.DuckDBManager.refresh_gcs_auth"
        )
        conn = MagicMock()

        with pytest.raises(ValueError, match="boom"):
            with_gcs_auth_retry(conn, lambda: (_ for _ in ()).throw(ValueError("boom")))

        refresh.assert_not_called()
