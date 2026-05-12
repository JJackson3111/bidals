#!/usr/bin/env sh
set -eu

case "$0" in
  */*)
    SCRIPT_PATH_DIR="${0%/*}"
    ;;
  *)
    SCRIPT_PATH_DIR="."
    ;;
esac

SCRIPT_DIR="$(CDPATH= cd "$SCRIPT_PATH_DIR" && pwd)"
BACKEND_DIR="$(CDPATH= cd "$SCRIPT_DIR/.." && pwd)"

cd "$BACKEND_DIR"

if [ "$#" -lt 1 ]; then
  echo "Usage: ./scripts/run_scheduled_job.sh <management-command> [args...]" >&2
  exit 64
fi

JOB_NAME="$1"
shift

case "$JOB_NAME" in
  close_expired_auctions|monitor_bid_anomalies|deliver_notifications)
    ;;
  *)
    echo "ERROR: unsupported scheduled job '$JOB_NAME'." >&2
    echo "Allowed jobs: close_expired_auctions, monitor_bid_anomalies, deliver_notifications." >&2
    exit 64
    ;;
esac

if [ -z "${DATABASE_URL:-}" ] && [ -n "${DJANGO_DATABASE_URL:-}" ]; then
  export DATABASE_URL="$DJANGO_DATABASE_URL"
fi

is_enabled() {
  case "${1:-}" in
    1|true|True|TRUE|yes|Yes|YES|on|On|ON)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

MISSING_VARS=""
if [ -z "${DJANGO_SETTINGS_MODULE:-}" ]; then
  MISSING_VARS="${MISSING_VARS} DJANGO_SETTINGS_MODULE"
fi
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
  MISSING_VARS="${MISSING_VARS} DJANGO_SECRET_KEY"
fi
if [ -z "${DJANGO_ALLOWED_HOSTS:-}" ]; then
  MISSING_VARS="${MISSING_VARS} DJANGO_ALLOWED_HOSTS"
fi
if [ -z "${DATABASE_URL:-}" ]; then
  MISSING_VARS="${MISSING_VARS} DATABASE_URL_or_DJANGO_DATABASE_URL"
fi

if [ -n "$MISSING_VARS" ]; then
  echo "ERROR: scheduled job is missing required production env vars:$MISSING_VARS" >&2
  echo "Copy the backend web service env group/secrets to every Render cron job. Secret values were not printed." >&2
  exit 78
fi

if [ "$DJANGO_SETTINGS_MODULE" != "bidals.settings.prod" ]; then
  echo "ERROR: DJANGO_SETTINGS_MODULE must be bidals.settings.prod for scheduled jobs." >&2
  echo "Current value was not printed with secrets or other env values." >&2
  exit 78
fi

export DJANGO_SETTINGS_MODULE

echo "scheduled_job=$JOB_NAME"
echo "settings_module=$DJANGO_SETTINGS_MODULE"
echo "required_env=pass"
echo "database_url_configured=yes"
echo "allowed_hosts_configured=yes"
if is_enabled "${USE_REDIS_CACHE:-}"; then
  if [ -n "${REDIS_URL:-}" ]; then
    echo "redis_env=pass"
  else
    echo "redis_env=warn_missing_REDIS_URL"
  fi
else
  echo "redis_env=not_enabled"
fi

if is_enabled "${USE_S3:-}"; then
  if [ -n "${AWS_ACCESS_KEY_ID:-}" ] \
    && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ] \
    && [ -n "${AWS_STORAGE_BUCKET_NAME:-}" ] \
    && [ -n "${AWS_S3_ENDPOINT_URL:-}" ] \
    && [ -n "${AWS_S3_REGION_NAME:-}" ]; then
    echo "s3_env=pass"
  else
    echo "s3_env=warn_missing_required_s3_env"
  fi
else
  echo "s3_env=not_enabled"
fi

if is_enabled "${EMAIL_NOTIFICATIONS_ENABLED:-}"; then
  if [ -n "${DEFAULT_FROM_EMAIL:-}" ]; then
    echo "email_env=pass"
  else
    echo "email_env=warn_missing_DEFAULT_FROM_EMAIL"
  fi
else
  echo "email_env=not_enabled"
fi

python - <<'PY'
import os

import django

django.setup()

from django.conf import settings

print(f"database_engine={settings.DATABASES['default']['ENGINE']}")
print(f"use_redis_cache={getattr(settings, 'USE_REDIS_CACHE', False)}")
print(f"redis_url_configured={'yes' if os.environ.get('REDIS_URL') else 'no'}")
PY

exec python manage.py "$JOB_NAME" "$@"
