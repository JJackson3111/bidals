# BIDALS Production Release Checklist

Use this checklist before each production release. It assumes the release candidate smoke suite already passed in staging with `FAIL=0`.

## Release Approval Gate

Required approvers:

- Product/operator owner.
- Backend/release owner.
- Admin/governance owner if repair workflows are exposed.

Required evidence:

- Staging RC smoke result attached: `PASS=19`, `WARN=2`, `FAIL=0` or better.
- Remaining `WARN` items accepted in writing.
- Backup/restore proof recorded in `BACKUP_LAST_VERIFIED_AT` and `BACKUP_LAST_RESTORE_TEST_AT`.
- Rollback target commit/image identified.
- Render cron job last-run evidence captured.
- Redis and object storage checks pass.

## Environment Verification

Backend production env:

- `DJANGO_SETTINGS_MODULE=bidals.settings.prod`
- `BIDALS_ENV=production`
- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY` configured with a non-placeholder value.
- `DJANGO_ALLOWED_HOSTS` contains production backend domains only.
- `DJANGO_CORS_ALLOWED_ORIGINS` or `CORS_ALLOWED_ORIGINS` contains production frontend origins only.
- `DJANGO_CSRF_TRUSTED_ORIGINS` or `CSRF_TRUSTED_ORIGINS` contains production frontend/backend origins.
- `DATABASE_URL` points to paid/production PostgreSQL.
- `USE_REDIS_CACHE=True`
- `REDIS_URL` points to production Redis.
- `USE_S3=True`
- R2/S3 env vars point to production bucket or production prefix.
- `SERVE_LOCAL_MEDIA=False`
- `SCHEDULED_JOBS_CONFIGURED=True`
- `BACKUP_PROVIDER=render`
- `BACKUP_LAST_VERIFIED_AT` set from real provider evidence.
- `BACKUP_LAST_RESTORE_TEST_AT` set from a completed restore rehearsal.

Frontend production env:

- `NEXT_PUBLIC_API_BASE_URL=https://<production-backend>/api`
- No staging API URL.
- No secrets stored in frontend env.

## Pre-Deploy Commands

Run in production backend shell or release job:

```bash
python manage.py deployment_check --production
python manage.py backup_verify --fail-on-warn
python manage.py release_check
```

Expected:

- `deployment_check --production` has no failures.
- `backup_verify --fail-on-warn` passes only after backup and restore timestamps are fresh.
- `release_check` has no unexpected failures. Manual `WARN` items must map to accepted release evidence.

## Deployment Steps

1. Confirm no active critical auction window if the deploy might restart services.
2. Confirm database backup status in Render.
3. Deploy backend from the approved GitHub commit.
4. Run migrations:

```bash
python manage.py migrate
```

5. Confirm backend health:

```bash
curl --fail https://<production-backend>/api/health/
```

6. Deploy frontend from the approved GitHub commit.
7. Confirm frontend health.
8. Confirm cron jobs still use:

```bash
sh /app/scripts/run_scheduled_job.sh close_expired_auctions
sh /app/scripts/run_scheduled_job.sh monitor_bid_anomalies --window-minutes 60
sh /app/scripts/run_scheduled_job.sh deliver_notifications
```

9. Confirm cron logs include:
   - `settings_module=bidals.settings.prod`
   - `database_engine=django.db.backends.postgresql`
   - `required_env=pass`
   - `redis_env=pass`
   - `s3_env=pass`

## Post-Deploy Smoke

Run at minimum:

- Backend `/api/health/`.
- Frontend health.
- Admin login.
- Seller login.
- Create auction.
- Create lot.
- Upload lot image.
- Browse auction and lot.
- Place valid bid.
- Place invalid bid.
- Confirm bid history.
- Confirm bid audit logs through `GET /api/lots/{lot_id}/audit/`.
- Confirm admin export CSV.
- Confirm cron close/winner job on safe test data or staging mirror.
- Confirm fulfillment update on test data.
- Confirm notification unread and mark-read.
- Confirm repair workflow access.

Do not use frontend state as acceptance evidence for bids or winners. Use backend API responses, audit logs, and admin views.

## Render Cron Verification

For each cron job:

- Root Directory: blank/unset.
- Runtime: Docker.
- Dockerfile Path: `backend/Dockerfile`.
- Docker Build Context Directory: `backend`.
- Command uses `/app/scripts/run_scheduled_job.sh`.
- Env vars copied from backend production env group.
- Last run succeeded after deploy.

## Redis And R2 Verification

Redis:

```bash
python manage.py deployment_check --production
```

Expected Redis check:

- `PASS REDIS: Redis cache is enabled and reachable.`

R2/S3:

- `USE_S3=True`.
- Upload a test lot image in staging or production-safe test data.
- Redeploy/restart.
- Confirm the image still loads.
- Confirm R2 credentials are not exposed to frontend.

## Release Decision

Go only when:

- Backup/restore proof is current.
- Deployment checks pass.
- RC smoke has `FAIL=0`.
- Known `WARN` items are accepted.
- Rollback owner and rollback target are known.

No-go when:

- Backup or restore proof is missing.
- Bidding endpoint returns uncontrolled errors.
- Audit logs are unreadable.
- Redis is required but unreachable.
- Object storage is required but disabled or misconfigured.
- Scheduler jobs cannot run with production settings.
