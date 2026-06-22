#!/bin/bash
# 由 db-backup.sh / db-restore.sh source；載入 script/.env 並正規化變數。

_load_env_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_load_env_file="${_load_env_script_dir}/.env"

if [ -f "$_load_env_file" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$_load_env_file"
    set +a
    echo "[INFO] Loaded env from ${_load_env_file}"
else
    echo "[WARN] Env file not found: ${_load_env_file} (using existing environment)"
fi

# PostgreSQL（支援 PG_DB 或 PG_DATABASE）
PG_DB="${PG_DB:-${PG_DATABASE:-}}"
PGPASSWORD="${PGPASSWORD:-${PG_PASSWORD:-}}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-postgres}"

# GCS S3 互通：若未設 AWS 金鑰，可沿用 GCS HMAC
if [ -n "${GCS_HMAC_ACCESS_KEY:-}" ] && [ -z "${AWS_ACCESS_KEY_ID:-}" ]; then
    AWS_ACCESS_KEY_ID="$GCS_HMAC_ACCESS_KEY"
fi
if [ -n "${GCS_HMAC_SECRET_KEY:-}" ] && [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    AWS_SECRET_ACCESS_KEY="$GCS_HMAC_SECRET_KEY"
fi
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-auto}"

export PG_DB PGPASSWORD PG_PORT PG_USER AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION

# 選填：GCS / MinIO 等非 AWS S3 時設定 S3_ENDPOINT
AWS_S3_OPTS=()
if [ -n "${S3_ENDPOINT:-}" ]; then
    AWS_S3_OPTS=(--endpoint-url "$S3_ENDPOINT")
fi

validate_db_script_env() {
    local missing=0
    for var in PG_HOST PG_USER PG_DB S3_BUCKET PROJECT_NAME APP_ENV TARGET_TABLE; do
        if [ -z "${!var:-}" ]; then
            echo "Error: ${var} is missing (set in script/.env or environment)"
            missing=1
        fi
    done
    if [ -z "${PGPASSWORD:-}" ]; then
        echo "Error: PGPASSWORD (or PG_PASSWORD) is missing"
        missing=1
    fi
    if [ "$missing" -ne 0 ]; then
        exit 1
    fi
}
