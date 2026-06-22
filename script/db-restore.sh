#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=load-env.sh
source "${SCRIPT_DIR}/load-env.sh"
validate_db_script_env

S3_PREFIX="${PROJECT_NAME}/${APP_ENV}/db-backup/${TARGET_TABLE}"
S3_SEARCH_PATH="s3://${S3_BUCKET}/${S3_PREFIX}/"

echo "[INFO] Searching for backups in: ${S3_SEARCH_PATH}"

LATEST_FILE=$(aws s3 ls "$S3_SEARCH_PATH" "${AWS_S3_OPTS[@]}" | sort | tail -n 1 | awk '{print $4}')

if [ -z "$LATEST_FILE" ]; then
    echo "[ERROR] No backup files found in ${S3_SEARCH_PATH}"
    echo "Please check if S3 path exists or TARGET_TABLE name is correct."
    exit 1
fi

echo "[START] Found latest backup: ${LATEST_FILE}"
echo "[START] Restoring into table: ${TARGET_TABLE}..."

export PGPASSWORD="$PGPASSWORD"

echo "[START] Truncating table..."
psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "TRUNCATE TABLE ${TARGET_TABLE};"

echo "[START] Importing data from SQL dump..."
aws s3 cp "${S3_SEARCH_PATH}${LATEST_FILE}" - "${AWS_S3_OPTS[@]}" | \
gzip -d | \
psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB"

echo "[SUCCESS] Restore completed for table: ${TARGET_TABLE}"
