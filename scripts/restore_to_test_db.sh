#!/usr/bin/env sh
set -eu

fail() {
  printf '%s\n' "ERROR: $*" >&2
  exit 1
}

BACKUP_FILE_VALUE="${BACKUP_FILE:-}"
RESTORE_DATABASE_URL_VALUE="${RESTORE_DATABASE_URL:-}"
PRIMARY_DATABASE_URL_VALUE="${DATABASE_URL:-${DJANGO_DATABASE_URL:-}}"
RESTORE_TARGET_ENV_VALUE="${RESTORE_TARGET_ENV:-restore-test}"
RESTORE_TARGET_CONFIRM_VALUE="${RESTORE_TARGET_CONFIRM:-}"

[ -n "$BACKUP_FILE_VALUE" ] || fail "Set BACKUP_FILE to the pg_dump custom-format file to restore."
[ -f "$BACKUP_FILE_VALUE" ] || fail "BACKUP_FILE does not exist: $BACKUP_FILE_VALUE"
[ -n "$RESTORE_DATABASE_URL_VALUE" ] || fail "Set RESTORE_DATABASE_URL to a dedicated non-production restore-test database."
[ "$RESTORE_TARGET_CONFIRM_VALUE" = "non-production-restore-ok" ] || fail "Set RESTORE_TARGET_CONFIRM=non-production-restore-ok to acknowledge the restore-test target will be overwritten."

if [ -n "$PRIMARY_DATABASE_URL_VALUE" ] && [ "$RESTORE_DATABASE_URL_VALUE" = "$PRIMARY_DATABASE_URL_VALUE" ]; then
  fail "RESTORE_DATABASE_URL must not equal DATABASE_URL/DJANGO_DATABASE_URL."
fi

case "$RESTORE_TARGET_ENV_VALUE" in
  production|prod)
    fail "RESTORE_TARGET_ENV must not be production."
    ;;
esac

command -v pg_restore >/dev/null 2>&1 || fail "pg_restore is not installed in this shell/image."

printf '%s\n' "restore_start=pass"
printf '%s\n' "target_environment=${RESTORE_TARGET_ENV_VALUE}"
printf '%s\n' "backup_file=${BACKUP_FILE_VALUE}"
printf '%s\n' "restore_database_url=configured"
printf '%s\n' "destructive_restore_scope=restore_test_database_only"

pg_restore "$BACKUP_FILE_VALUE" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --dbname="$RESTORE_DATABASE_URL_VALUE"

printf '%s\n' "restore_complete=pass"
