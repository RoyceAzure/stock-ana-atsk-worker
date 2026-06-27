"""向後相容：請改用 infra.repo.gcp.gcp_auth。"""

from infra.repo.gcp.gcp_auth import (  # noqa: F401
    GcpAuthMode,
    PubSubAuthMode,
    create_subscriber_client,
    gcp_auth_mode_from_env,
    gcp_service_account_key_file_from_env,
    pubsub_auth_mode_from_env,
    pubsub_service_account_key_file_from_env,
    resolve_gcp_auth_mode,
    resolve_pubsub_auth_mode,
    resolve_service_account_key_file,
)
