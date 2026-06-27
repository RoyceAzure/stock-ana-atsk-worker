import json
from unittest.mock import MagicMock

import pytest

from infra.repo.gcp.gcp_auth import (
    GcpAuthMode,
    create_gcs_filesystem,
    create_subscriber_client,
    refresh_gcp_access_token,
    resolve_gcp_auth_mode,
    resolve_service_account_key_file,
)


class TestResolveGcpAuthMode:
    def test_default_adc(self, monkeypatch):
        monkeypatch.delenv("GCP_AUTH_MODE", raising=False)
        monkeypatch.delenv("GCP_PUBSUB_AUTH_MODE", raising=False)
        assert resolve_gcp_auth_mode() is GcpAuthMode.ADC

    def test_gcp_auth_mode_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("GCP_AUTH_MODE", "service_account_json")
        monkeypatch.setenv("GCP_PUBSUB_AUTH_MODE", "adc")
        assert resolve_gcp_auth_mode() is GcpAuthMode.SERVICE_ACCOUNT_JSON

    def test_invalid_mode_raises(self, monkeypatch):
        monkeypatch.setenv("GCP_AUTH_MODE", "hmac")
        with pytest.raises(ValueError, match="GCP_AUTH_MODE"):
            resolve_gcp_auth_mode()


class TestResolveServiceAccountKeyFile:
    def test_prefers_gcp_sa_key_file(self, monkeypatch, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text("{}", encoding="utf-8")
        other = tmp_path / "other.json"
        other.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("GCP_SA_KEY_FILE", str(key))
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(other))
        assert resolve_service_account_key_file() == str(key)


class TestCreateGcpClients:
    def test_adc_gcs_filesystem(self, mocker):
        mock_fs = mocker.patch("gcsfs.GCSFileSystem")

        create_gcs_filesystem(auth_mode=GcpAuthMode.ADC)

        mock_fs.assert_called_once_with()

    def test_service_account_json_gcs_filesystem(self, mocker, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text("{}", encoding="utf-8")
        mock_fs = mocker.patch("gcsfs.GCSFileSystem")
        mock_from_file = mocker.patch(
            "infra.repo.gcp.gcp_auth.service_account.Credentials.from_service_account_file",
            return_value="creds",
        )

        create_gcs_filesystem(
            auth_mode=GcpAuthMode.SERVICE_ACCOUNT_JSON,
            service_account_key_file=str(key),
        )

        mock_from_file.assert_called_once_with(str(key))
        mock_fs.assert_called_once_with(token="creds")

    def test_adc_subscriber_client(self, mocker):
        mock_client = mocker.patch("infra.repo.gcp.gcp_auth.pubsub_v1.SubscriberClient")

        create_subscriber_client(auth_mode=GcpAuthMode.ADC)

        mock_client.assert_called_once_with()

    def test_service_account_json_subscriber_client(self, mocker, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text(json.dumps({"type": "service_account"}), encoding="utf-8")
        mock_client = mocker.patch("infra.repo.gcp.gcp_auth.pubsub_v1.SubscriberClient")
        mock_from_file = mocker.patch(
            "infra.repo.gcp.gcp_auth.service_account.Credentials.from_service_account_file",
            return_value="creds",
        )

        create_subscriber_client(
            auth_mode=GcpAuthMode.SERVICE_ACCOUNT_JSON,
            service_account_key_file=str(key),
        )

        mock_from_file.assert_called_once_with(str(key))
        mock_client.assert_called_once_with(credentials="creds")


class TestRefreshGcpAccessToken:
    def test_adc_refreshes_default_credentials(self, mocker):
        creds = MagicMock()
        creds.token = "adc-token"
        mocker.patch(
            "infra.repo.gcp.gcp_auth.google_auth_default",
            return_value=(creds, "project"),
        )
        mock_request = mocker.patch("infra.repo.gcp.gcp_auth.google_auth_requests.Request")

        token = refresh_gcp_access_token(auth_mode=GcpAuthMode.ADC)

        assert token == "adc-token"
        creds.refresh.assert_called_once_with(mock_request.return_value)
