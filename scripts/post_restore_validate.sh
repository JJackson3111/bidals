#!/usr/bin/env sh
set -eu

fail() {
  printf '%s\n' "ERROR: $*" >&2
  exit 1
}

MANAGE_PY_VALUE="${MANAGE_PY:-backend/manage.py}"
DATABASE_URL_VALUE="${DATABASE_URL:-${DJANGO_DATABASE_URL:-}}"
DJANGO_SETTINGS_MODULE_VALUE="${DJANGO_SETTINGS_MODULE:-bidals.settings.prod}"
API_BASE_URL_VALUE="${API_BASE_URL:-}"
RUN_RC_SMOKE_VALUE="${RUN_RC_SMOKE:-false}"

[ -f "$MANAGE_PY_VALUE" ] || fail "Could not find manage.py at $MANAGE_PY_VALUE. Set MANAGE_PY if needed."
[ -n "$DATABASE_URL_VALUE" ] || fail "Set DATABASE_URL or DJANGO_DATABASE_URL for the restored validation environment."

export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE_VALUE"

printf '%s\n' "post_restore_validation_start=pass"
printf '%s\n' "settings_module=${DJANGO_SETTINGS_MODULE}"
printf '%s\n' "database_url=configured"

python "$MANAGE_PY_VALUE" migrate --check
python "$MANAGE_PY_VALUE" check
python "$MANAGE_PY_VALUE" verify_backup
python "$MANAGE_PY_VALUE" release_check

if [ -n "$API_BASE_URL_VALUE" ]; then
  command -v curl >/dev/null 2>&1 || fail "API_BASE_URL was set, but curl is not installed."
  printf '%s\n' "health_probe=${API_BASE_URL_VALUE}/health/"
  curl --fail --silent --show-error "${API_BASE_URL_VALUE}/health/" >/dev/null
  printf '%s\n' "health_probe=pass"
else
  printf '%s\n' "health_probe=skipped_api_base_url_missing"
fi

if [ "$RUN_RC_SMOKE_VALUE" = "true" ]; then
  [ -d "frontend" ] || fail "RUN_RC_SMOKE=true but frontend directory was not found."
  npm --prefix frontend run smoke:release-candidate
else
  printf '%s\n' "release_candidate_smoke=skipped"
fi

printf '%s\n' "post_restore_validation_complete=pass"
