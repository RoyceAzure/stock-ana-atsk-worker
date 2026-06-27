import json

import pytest

from infra.repo.gcp.pubsub_auth import (
    PubSubAuthMode,
    create_subscriber_client,
    resolve_pubsub_auth_mode,
    resolve_service_account_key_file,
)


class TestResolvePubSubAuthMode:
    def test_default_adc(self, monkeypatch):
        monkeypatch.delenv("GCP_PUBSUB_AUTH_MODE", raising=False)
        assert resolve_pubsub_auth_mode() is PubSubAuthMode.ADC

    def test_service_account_json(self, monkeypatch):
        monkeypatch.setenv("GCP_PUBSUB_AUTH_MODE", "service_account_json")
        assert resolve_pubsub_auth_mode() is PubSubAuthMode.SERVICE_ACCOUNT_JSON

    def test_invalid_mode_raises(self, monkeypatch):
        monkeypatch.setenv("GCP_PUBSUB_AUTH_MODE", "hmac")
        with pytest.raises(ValueError, match="GCP_PUBSUB_AUTH_MODE"):
            resolve_pubsub_auth_mode()


class TestResolveServiceAccountKeyFile:
    def test_prefers_gcp_sa_key_file(self, monkeypatch, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text("{}", encoding="utf-8")
        other = tmp_path / "other.json"
        other.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("GCP_SA_KEY_FILE", str(key))
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(other))
        assert resolve_service_account_key_file() == str(key)

    def test_falls_back_to_google_application_credentials(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GCP_SA_KEY_FILE", raising=False)
        key = tmp_path / "adc.json"
        key.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(key))
        assert resolve_service_account_key_file() == str(key)

    def test_missing_path_raises(self, monkeypatch):
        monkeypatch.delenv("GCP_SA_KEY_FILE", raising=False)
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        with pytest.raises(ValueError, match="GCP_SA_KEY_FILE"):
            resolve_service_account_key_file()


class TestCreateSubscriberClient:
    def test_adc_uses_default_client(self, mocker):
        mock_client = mocker.patch("infra.repo.gcp.pubsub_auth.pubsub_v1.SubscriberClient")

        create_subscriber_client(auth_mode=PubSubAuthMode.ADC)

        mock_client.assert_called_once_with()

    def test_service_account_json_uses_credentials(self, mocker, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text(
            json.dumps(
                {
                    "type": "service_account",
                    "project_id": "demo",
                    "private_key_id": "id",
                    "private_key": (
                        "-----BEGIN PRIVATE KEY-----\n"
                        "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7\n"
                        "-----END PRIVATE KEY-----\n"
                    ),
                    "client_email": "demo@demo.iam.gserviceaccount.com",
                    "client_id": "123",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            ),
            encoding="utf-8",
        )
        mock_client = mocker.patch("infra.repo.gcp.pubsub_auth.pubsub_v1.SubscriberClient")
        mock_from_file = mocker.patch(
            "infra.repo.gcp.pubsub_auth.service_account.Credentials.from_service_account_file",
            return_value="creds",
        )

        create_subscriber_client(
            auth_mode=PubSubAuthMode.SERVICE_ACCOUNT_JSON,
            service_account_key_file=str(key),
        )

        mock_from_file.assert_called_once_with(str(key))
        mock_client.assert_called_once_with(credentials="creds")
