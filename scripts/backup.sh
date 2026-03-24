#!/usr/bin/env bash
set -euo pipefail

# Pre-deploy safety net:
# run this script manually before every production deploy (in addition to
# automated backups) so rollback always has a fresh, operator-verified dump.

: "${POSTGRES_HOST:?POSTGRES_HOST is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
OUT_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

export PGPASSWORD="${POSTGRES_PASSWORD}"

pg_dump \
  --host="${POSTGRES_HOST}" \
  --port="${POSTGRES_PORT}" \
  --username="${POSTGRES_USER}" \
  --dbname="${POSTGRES_DB}" \
  --format=custom \
  --blobs \
  --verbose \
  --no-owner \
  --no-privileges \
  --file="${OUT_FILE}"

if [ ! -s "${OUT_FILE}" ]; then
  echo "ERROR: backup file was created but is empty: ${OUT_FILE}" >&2
  exit 1
fi

SIZE_BYTES="$(stat -c%s "${OUT_FILE}")"
SIZE_HUMAN="$(du -h "${OUT_FILE}" | awk '{print $1}')"
echo "Backup completed: ${OUT_FILE} (${SIZE_HUMAN}, ${SIZE_BYTES} bytes)"
