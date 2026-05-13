#!/usr/bin/env sh
set -eu

fail() {
  printf '%s\n' "ERROR: $*" >&2
  exit 1
}

DATABASE_URL_VALUE="${DATABASE_URL:-${DJANGO_DATABASE_URL:-}}"
BACKUP_OUTPUT_DIR_VALUE="${BACKUP_OUTPUT_DIR:-backups}"
BACKUP_LABEL_VALUE="${BACKUP_LABEL:-bidals}"
BIDALS_ENV_VALUE="${BIDALS_ENV:-unknown}"

[ -n "$DATABASE_URL_VALUE" ] || fail "Set DATABASE_URL or DJANGO_DATABASE_URL before running pg_dump backup."
command -v pg_dump >/dev/null 2>&1 || fail "pg_dump is not installed in this shell/image."

mkdir -p "$BACKUP_OUTPUT_DIR_VALUE"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_OUTPUT_DIR_VALUE}/${BACKUP_LABEL_VALUE}-${BIDALS_ENV_VALUE}-${TIMESTAMP}.dump"

printf '%s\n' "backup_start=pass"
printf '%s\n' "environment=${BIDALS_ENV_VALUE}"
printf '%s\n' "format=custom"
printf '%s\n' "output_file=${BACKUP_FILE}"
printf '%s\n' "database_url=configured"

pg_dump "$DATABASE_URL_VALUE" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="$BACKUP_FILE"

if command -v sha256sum >/dev/null 2>&1; then
  SHA256="$(sha256sum "$BACKUP_FILE" | awk '{print $1}')"
  printf '%s\n' "sha256=${SHA256}"
elif command -v shasum >/dev/null 2>&1; then
  SHA256="$(shasum -a 256 "$BACKUP_FILE" | awk '{print $1}')"
  printf '%s\n' "sha256=${SHA256}"
else
  printf '%s\n' "sha256=warn_checksum_tool_missing"
fi

printf '%s\n' "backup_complete=pass"
