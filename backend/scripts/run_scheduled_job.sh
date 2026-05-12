#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd "$(dirname "$0")" && pwd)"
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

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL or DJANGO_DATABASE_URL must be set for scheduled jobs." >&2
  exit 78
fi

if [ "${DJANGO_SETTINGS_MODULE:-}" != "bidals.settings.prod" ]; then
  echo "INFO: forcing DJANGO_SETTINGS_MODULE=bidals.settings.prod for scheduled job."
fi
export DJANGO_SETTINGS_MODULE="bidals.settings.prod"

echo "scheduled_job=$JOB_NAME"
echo "settings_module=$DJANGO_SETTINGS_MODULE"

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
