#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=load-env.sh
source "${SCRIPT_DIR}/load-env.sh"
validate_db_script_env

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="${TARGET_TABLE}_${TIMESTAMP}.sql.gz"
S3_PREFIX="${PROJECT_NAME}/${APP_ENV}/db-backup/${TARGET_TABLE}"
S3_PATH="s3://${S3_BUCKET}/${S3_PREFIX}/${FILENAME}"

echo "[START] Backing up table: ${TARGET_TABLE} from postgres..."
echo "[UPLOAD] Streaming backup directly to ${S3_PATH}..."

pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t "$TARGET_TABLE" -a | \
gzip | \
aws s3 cp - "$S3_PATH" "${AWS_S3_OPTS[@]}"

echo "[SUCCESS] Backup completed and uploaded to S3."
