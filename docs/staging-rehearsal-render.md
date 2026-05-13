# BIDALS Phase 17 Staging Rehearsal

Provider selected: Render

Status: RELEASE CANDIDATE SMOKE PASS - backend and frontend staging services are deployed, health/browse/auth/create/bidding flows have live evidence, the Browse empty-state issue is fixed, the bid endpoint `500` regression is fixed and verified after backend redeploy commit `cb9ca78`, Render shell readiness checks pass health, migrations, Redis cache, object storage, and audit-related checks, all Render cron jobs execute through the hardened scheduled-job runner, and the release candidate smoke gate now reports `PASS=19`, `WARN=2`, `FAIL=0`. Core backend-owned auction lifecycle is verified in staging. The remaining production blocker is backup/restore proof. Full two-admin repair create/approve/apply remains a `WARN` until `RC_SMOKE_ADMIN2_USERNAME` and `RC_SMOKE_ADMIN2_PASSWORD` are configured.

This document is the Phase 17 execution record. Fill in the evidence sections during the live Render staging rehearsal. Do not record secrets, tokens, database passwords, or private keys here.

## Required Inputs

- GitHub repository URL:
- Render workspace/team:
- Backend staging URL: `https://bidals.onrender.com`
- Frontend staging URL: `https://bidals-1.onrender.com`
- Managed PostgreSQL service name:
- Managed Redis service name:
- Backup source:
- Restore target:
- Operator:
- Rehearsal date: 2026-05-05

## Existing BIDALS Deployment Readiness

- Backend Docker image: `backend/Dockerfile`
- Backend production settings: `bidals.settings.prod`
- Backend health path: `/api/health/`
- Frontend production Docker image: `frontend/Dockerfile.prod`
- Frontend health path: `/api/health`
- Required database: managed PostgreSQL via `DATABASE_URL`
- Redis cache/throttling: `REDIS_URL` with `USE_REDIS_CACHE=True`
- Redis verification: `deployment_check --production` now performs a cache set/get/delete round-trip when `USE_REDIS_CACHE=True`
- Scheduler commands:
  - `sh /app/scripts/run_scheduled_job.sh close_expired_auctions`
  - `sh /app/scripts/run_scheduled_job.sh monitor_bid_anomalies --window-minutes 60`
  - `sh /app/scripts/run_scheduled_job.sh deliver_notifications`
- Readiness commands:
  - `python manage.py deployment_check --production`
  - `python manage.py verify_backup`
  - `python manage.py release_check`

## Render Staging Deployment Plan

1. Create a Render managed PostgreSQL service for staging.
2. Create a Render Redis instance for shared cache/throttling.
3. Create the backend web service from the GitHub repository. `PASS`: backend is reachable at `https://bidals.onrender.com`.
4. Set backend root/directory to `backend` if using Render's repository directory setting.
5. Use `backend/Dockerfile`.
6. Set health check path to `/api/health/`.
7. Set pre-deploy/release command to:

```bash
python manage.py migrate
```

8. Create the frontend web service from the same GitHub repository. `PASS`: frontend is reachable at `https://bidals-1.onrender.com`.
9. Use `frontend/Dockerfile.prod`.
10. Set the frontend build arg/env value:

```bash
NEXT_PUBLIC_API_BASE_URL=https://<backend-staging-host>/api
```

11. Set frontend health check path to `/api/health`.
12. Confirm both services deploy from GitHub and report healthy. `PASS`: backend health, frontend health, and RC smoke have been confirmed.

Confirmed staging evidence so far:

| Check | Result | Evidence |
| --- | --- | --- |
| Backend health | PASS | `GET https://bidals.onrender.com/api/health/` returns `200 OK` with `{"status":"ok","service":"bidals-backend"}` |
| Backend auction list | PASS | Initially returned `200 OK` with `{"count":0,"next":null,"previous":null,"results":[]}`. After smoke setup, returned `count=2` with Phase 17 smoke auctions. |
| Frontend load | PASS | `https://bidals-1.onrender.com` loads successfully |
| Frontend health | PASS | `GET https://bidals-1.onrender.com/api/health` returns `200 OK` with `{"status":"ok","service":"bidals-frontend"}` |
| Frontend browse route | PASS | `GET https://bidals-1.onrender.com/auctions` returns `200 OK`; operator confirmed Browse now shows empty states for no auctions/lots. |
| Frontend browse empty state | PASS | Browse page no longer treats a valid empty DRF paginated response as an error. |
| Bid endpoint after `cb9ca78` redeploy | PASS | Fresh smoke lot id `4`: valid bid `15.00` returned `201 accepted`, invalid bid `16.00` returned `409 INVALID_INCREMENT`, anonymous bid `20.00` returned `401 UNAUTHENTICATED`, and `current_price` moved only from `10.00` to `15.00`. |
| Render `release_check` | PASS/WARN | Render shell check passes health endpoint, migrations, audit logs, and admin export installation/protection. Scheduler execution is now independently verified; rerun `release_check` after setting `SCHEDULED_JOBS_CONFIGURED=True` to clear the earlier scheduled-jobs WARN. Final RC smoke now verifies fulfillment, notifications, admin export CSV, and auction lifecycle. Remaining production blocker is backup/restore proof. |
| Render `deployment_check --production` | PASS | Render shell check now passes DEBUG, SECRET_KEY, ALLOWED_HOSTS, DATABASE, REDIS, MEDIA_STORAGE, EMAIL disabled safely, MIGRATIONS, and HEALTH. |
| Django admin access | PASS | `https://bidals.onrender.com/admin/` loads successfully and `staging_admin` can log in. Django admin shows Users, Auctions, Bids, Fulfillment records, Lots, Audit logs, Outbound notifications, Outcome repair requests/comments, and token blacklist models. |
| Render scheduled jobs | PASS | `close_expired_auctions`, `monitor_bid_anomalies --window-minutes 60`, and `deliver_notifications` now execute successfully through `sh /app/scripts/run_scheduled_job.sh ...`. Confirmed diagnostics include `settings_module=bidals.settings.prod`, `database_engine=django.db.backends.postgresql`, `required_env=pass`, `redis_env=pass`, and `s3_env=pass`. Notification delivery completed successfully. |
| Release candidate smoke gate | PASS/WARN | Final Render staging rerun reports `PASS=19`, `WARN=2`, `FAIL=0`. Valid bid, invalid bid rejection, bid history, lot audit via `GET /api/lots/{lot_id}/audit/`, admin export CSV, close/winner calculation, fulfillment update, bidder won-lots, notification unread/mark-read, and repair access all pass. WARNs are limited to missing second-admin credentials and skipped full two-admin repair create/approve/apply. |

## Staging Environment Variables

Record values as configured, but never record secret values.

Backend:

- `DJANGO_SETTINGS_MODULE=bidals.settings.prod`
- `BIDALS_ENV=staging`
- `DJANGO_SECRET_KEY=<configured in Render secret manager>`
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=<backend staging host>`
- `DJANGO_CORS_ALLOWED_ORIGINS=<frontend staging origin>`
- `DJANGO_CSRF_TRUSTED_ORIGINS=<frontend staging origin>`
- `DJANGO_SECURE_SSL_REDIRECT=True`
- `DJANGO_SECURE_HSTS_SECONDS=0` for first staging HTTPS validation, then raise if desired
- `DATABASE_URL=<Render PostgreSQL internal/external URL>`
- `REDIS_URL=<Render Redis URL>` from the Render Redis service; keep the exact `redis://` or `rediss://` provider URL in backend secrets
- `USE_REDIS_CACHE=True` with a reachable Redis service; use `USE_REDIS_CACHE=False` only for staging without Redis, understanding rate-limit counters become per-process local memory
- `REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS=2`
- `REDIS_SOCKET_TIMEOUT_SECONDS=2`
- `REDIS_CACHE_KEY_PREFIX=bidals-staging`
- `FRONTEND_URL=<frontend staging origin>`
- `LOG_LEVEL=INFO`
- `ENABLE_STRUCTURED_LOGGING=True`
- `SENTRY_DSN=<blank or staging DSN>`
- `SENTRY_ENVIRONMENT=staging`
- `BID_RATE_LIMIT_AUTHENTICATED_ATTEMPTS=10`
- `BID_RATE_LIMIT_ANONYMOUS_ATTEMPTS=2`
- `BID_RATE_LIMIT_WINDOW_SECONDS=60`
- `BID_ANOMALY_REJECT_THRESHOLD=5`
- `BID_ANOMALY_RATE_LIMIT_THRESHOLD=3`
- `SCHEDULED_JOBS_CONFIGURED=True` after schedulers are configured and verified
- `EMAIL_NOTIFICATIONS_ENABLED=False` unless staging email is deliberately configured
- `DEFAULT_FROM_EMAIL=<staging sender if email enabled>`
- `MEDIA_URL=/media/`
- `MEDIA_ROOT=<staging media path>`
- `LOT_IMAGE_MAX_UPLOAD_SIZE_MB=5`
- `SERVE_LOCAL_MEDIA=True` only for staging/local demos when `USE_S3=False`; keep disabled for production
- `USE_S3=True` after Cloudflare R2/S3-compatible object storage is configured for staging or production
- `AWS_ACCESS_KEY_ID=<Render secret: R2 access key>`
- `AWS_SECRET_ACCESS_KEY=<Render secret: R2 secret key>`
- `AWS_STORAGE_BUCKET_NAME=<R2 bucket name>`
- `AWS_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com`
- `AWS_S3_REGION_NAME=auto`
- `AWS_S3_CUSTOM_DOMAIN=<optional media domain>`
- `AWS_QUERYSTRING_AUTH=True` for a private bucket with signed URLs, or `False` when using a public custom media domain
- `AWS_S3_ADDRESSING_STYLE=path`
- `AWS_S3_SIGNATURE_VERSION=s3v4`
- `AWS_S3_CACHE_CONTROL=max-age=86400`
- `BACKUP_PROVIDER=render`
- `BACKUP_LAST_VERIFIED_AT=<ISO-8601 timestamp after backup is verified>`
- `BACKUP_LAST_RESTORE_TEST_AT=<ISO-8601 timestamp after restore test passes>`
- `STAGING_ADMIN_PASSWORD=<set only in a one-off Render shell/session when running create_staging_admin>`

Frontend:

- `NEXT_PUBLIC_API_BASE_URL=https://<backend-staging-host>/api`
- `NEXT_TELEMETRY_DISABLED=1`

## Scheduler Configuration

Configure Render Cron Jobs or scheduled backend jobs using the same backend image and environment as the web service.

Render cron service values:

- Root Directory: leave blank/unset
- Runtime: Docker
- Dockerfile Path: `backend/Dockerfile`
- Docker Build Context Directory: `backend`
- Environment variables: copy the backend web service env group/secrets to every cron job. Do not rely on inline command env vars.

Required env vars for every Render cron job:

- `DJANGO_SETTINGS_MODULE=bidals.settings.prod`
- `DJANGO_SECRET_KEY=<same backend secret>`
- `DJANGO_ALLOWED_HOSTS=<backend staging host>`
- `DATABASE_URL=<Render PostgreSQL URL>` or `DJANGO_DATABASE_URL=<Render PostgreSQL URL>`

These required vars apply to `close_expired_auctions`, `monitor_bid_anomalies`, and `deliver_notifications`. Email-specific vars are additional only when notification delivery is enabled.

Copy these from the backend web service when enabled/configured:

- Frontend/origin parity: `FRONTEND_URL`, `DJANGO_CORS_ALLOWED_ORIGINS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- Redis: `USE_REDIS_CACHE`, `REDIS_URL`, `REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS`, `REDIS_SOCKET_TIMEOUT_SECONDS`, `REDIS_CACHE_KEY_PREFIX`
- Object storage: `USE_S3`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`, `AWS_S3_CUSTOM_DOMAIN`, `AWS_QUERYSTRING_AUTH`, `AWS_S3_ADDRESSING_STYLE`, `AWS_S3_SIGNATURE_VERSION`, `AWS_S3_CACHE_CONTROL`
- Email/notifications: `EMAIL_NOTIFICATIONS_ENABLED`, `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`
- Alerts: `ALERT_WEBHOOK_URL`, `ALERT_WEBHOOK_TIMEOUT_SECONDS`

The runner validates required vars before `django.setup()`. If several required vars are missing, it reports them together in one message and does not print secret values.

| Job | Command | Suggested frequency | Result |
| --- | --- | --- | --- |
| Auction closing and winner calculation | `sh /app/scripts/run_scheduled_job.sh close_expired_auctions` | Every 1 minute, or the shortest Render-supported interval | PASS - Render cron executes through the hardened runner with production settings and PostgreSQL |
| Bid anomaly monitoring | `sh /app/scripts/run_scheduled_job.sh monitor_bid_anomalies --window-minutes 60` | Every 5 minutes | PASS - Render cron executes through the hardened runner with production settings and PostgreSQL |
| Notification delivery | `sh /app/scripts/run_scheduled_job.sh deliver_notifications` | Every 5 minutes if email enabled | PASS - Render cron executes through the hardened runner; notification delivery run completed successfully |

Evidence to capture:

- Render scheduler name: configured in Render Cron Jobs for auction closing, anomaly monitoring, and notification delivery.
- Last run timestamp: available in Render cron logs.
- Log excerpt showing success: confirmed safe diagnostics include `settings_module=bidals.settings.prod`, `database_engine=django.db.backends.postgresql`, `required_env=pass`, `redis_env=pass`, and `s3_env=pass`.
- Notification delivery evidence: delivery run completed successfully.
- Audit log event visible in `/dashboard/operations`: still useful to verify during the next admin operations smoke pass.

If Render cannot find the runner, temporarily set the cron command to:

```bash
sh -c 'pwd && ls -l /app/scripts/run_scheduled_job.sh /usr/local/bin/bidals-scheduled-job'
```

The production Docker build now fails if `/app/scripts/run_scheduled_job.sh` is missing, and also creates `/usr/local/bin/bidals-scheduled-job` as a stable symlink.

## Safe Staging Admin Setup

Use this path when staging needs an admin account but you do not want to load the full staging data seed.

Safety properties:

- Refuses to run unless `BIDALS_ENV=staging`.
- Can run outside staging only with explicit `--force`; do not use `--force` against production data.
- Reads the password from an environment variable only.
- Does not print the password.
- Creates or updates a role `admin`, staff, superuser account.
- Writes an `admin_action` audit log with non-secret metadata.

Render backend shell command:

```bash
export STAGING_ADMIN_PASSWORD='<strong-temporary-password>'
python manage.py create_staging_admin \
  --username staging_admin \
  --email admin@bidals.staging.test
unset STAGING_ADMIN_PASSWORD
```

Alternative full staging seed command:

```bash
python manage.py seed_staging_data
```

The full seed command also refuses production unless `--force`, but it creates demo auctions, lots, bids, fulfillment records, and notifications in addition to the staging users.

## Backup Restore Verification

Do not overwrite production data. Restore into staging or a separate restore-test database.

1. Confirm Render PostgreSQL backup exists.
2. Restore the backup into a staging/restore-test database.
3. Point the staging backend at the restored database if using a separate restore target.
4. Run migrations:

```bash
python manage.py migrate
```

5. Run backup verification:

```bash
python manage.py verify_backup
```

6. Validate critical data:

| Data check | Expected | Result |
| --- | --- | --- |
| Users exist | Admin, seller, bidder users present | PASS for live staging smoke data - seller, bidder, and `staging_admin` access are confirmed. Managed backup restore evidence is still WARN until a restore rehearsal is performed. |
| Auctions exist | Live/scheduled/ended auctions present | PASS - smoke auction created through backend API |
| Lots exist | Lots linked to auctions | PASS - smoke lot created through backend API |
| Bids exist | Accepted and rejected bids present | PASS for live staging smoke data - fresh lot id `4` has accepted bid id `3` and authenticated rejected bid id `4`; managed backup restore evidence is still WARN until a restore rehearsal is performed |
| Audit logs exist | Audit events readable | PASS for live staging smoke data - Django admin Audit logs page loads and RC smoke verifies bid audit records through `GET /api/lots/{lot_id}/audit/`. Managed backup restore evidence is still WARN until a restore rehearsal is performed. |

Restore evidence:

- Backup timestamp: not available
- Restore target: not available
- Restore command/provider action: not executed
- `BACKUP_LAST_VERIFIED_AT`: not set/verified
- `BACKUP_LAST_RESTORE_TEST_AT`: not set/verified
- Limitation: Render free PostgreSQL does not provide enough managed backup/restore evidence for this Phase 17 acceptance item. Treat this as `WARN` until staging uses a plan/provider path that supports restore proof, or until a manual `pg_dump`/restore rehearsal is completed against a non-production database.

## Commands To Run In Staging

```bash
python manage.py migrate
STAGING_ADMIN_PASSWORD='<strong-temporary-password>' python manage.py create_staging_admin --username staging_admin --email admin@bidals.staging.test
python manage.py seed_staging_data
python manage.py deployment_check --production
python manage.py verify_backup
python manage.py release_check
sh /app/scripts/run_scheduled_job.sh close_expired_auctions
sh /app/scripts/run_scheduled_job.sh monitor_bid_anomalies --window-minutes 60
sh /app/scripts/run_scheduled_job.sh deliver_notifications
```

Optional Playwright smoke against staging:

```bash
cd frontend
E2E_BASE_URL=https://<frontend-staging-host> \
E2E_SKIP_WEB_SERVER=1 \
E2E_SELLER_USERNAME=staging_seller \
E2E_BIDDER_USERNAME=staging_bidder \
E2E_ADMIN_USERNAME=staging_admin \
E2E_DEMO_PASSWORD=ChangeMe123! \
npm run test:e2e:ci
```

## release_check Output

Paste sanitized staging output here:

```text
RENDER SHELL RESULT AFTER HEALTH-PATH FIX

Command:
python manage.py release_check

Result:
PASS/WARN - no health endpoint failure remains.

Confirmed PASS checks:
[PASS] system / Health endpoint
[PASS] database / Migrations
[PASS] ops / Audit logs
[PASS] ops / Admin export

Remaining WARN checks from the earlier shell run:
[WARN] database / Backup verification
[WARN] ops / Scheduled jobs
[WARN] core_flows / Fulfillment workflow
[WARN] notifications / Unread count
[WARN] ops / Repair workflow

Follow-up evidence:
[PASS] ops / Scheduled jobs: Render cron jobs now execute through the hardened runner with `settings_module=bidals.settings.prod`, `database_engine=django.db.backends.postgresql`, `required_env=pass`, `redis_env=pass`, and `s3_env=pass`.
[PASS] core_flows / Fulfillment workflow: Final RC smoke confirms fulfillment update.
[PASS] notifications / Unread count: Final RC smoke confirms notification unread and mark-read behavior.
[PASS/WARN] ops / Repair workflow: Final RC smoke confirms repair workflow access; full two-admin create/approve/apply remains WARN until second-admin credentials are configured.

Next release-check action:
Set `SCHEDULED_JOBS_CONFIGURED=True` in the backend environment if not already set, record backup/restore timestamps after a restore rehearsal, and rerun `python manage.py release_check` so command output reflects the final go/no-go state.
```

Admin access probe:

- Earlier `POST /api/auth/login/` with `staging_admin` / `ChangeMe123!` returned `401` before the staging admin setup was repaired.
- Current evidence: `https://bidals.onrender.com/admin/` loads successfully and `staging_admin` can log into Django admin.
- Django admin model visibility confirmed: Users, Auctions, Bids, Fulfillment records, Lots, Audit logs, Outbound notifications, Outcome repair requests/comments, and token blacklist models.
- API/JWT admin login and admin export are now covered by the final RC smoke suite.

## deployment_check Output

Paste sanitized staging output here:

```text
RENDER SHELL RESULT AFTER REDIS AND OBJECT STORAGE CONFIGURATION

Command:
python manage.py deployment_check --production

Result:
PASS - all deployment checks listed below pass.

Confirmed PASS checks:
[PASS] DEBUG
[PASS] SECRET_KEY
[PASS] ALLOWED_HOSTS
[PASS] DATABASE
[PASS] REDIS: Redis cache is enabled
[PASS] MEDIA_STORAGE: Object storage is enabled
[PASS] EMAIL: Email notification delivery is disabled
[PASS] MIGRATIONS
[PASS] HEALTH
```

Redis reconnect implementation and verification:

- Backend settings now pass Redis socket timeouts and a cache key prefix into Django's Redis cache backend.
- `deployment_check --production` now fails if `USE_REDIS_CACHE=True` but Redis cannot complete a cache round-trip.
- Local regression tests cover Redis PASS and Redis connectivity failure paths.
- Render staging evidence now confirms Redis is configured and reachable.
- Required Render backend env:
  - `USE_REDIS_CACHE=True`
  - `REDIS_URL=<Render Redis URL>`
  - `REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS=2`
  - `REDIS_SOCKET_TIMEOUT_SECONDS=2`
  - `REDIS_CACHE_KEY_PREFIX=bidals-staging`

## verify_backup Output

Paste sanitized staging output here:

```text
Command:
python manage.py verify_backup

Render staging output:
[PASS] database / Connectivity: Database connection is usable.
[PASS] database / Critical tables: Critical BIDALS tables are present.
[WARN] backup / Backup timestamp: No BACKUP_LAST_VERIFIED_AT value is configured; verify backups in the cloud provider.
[WARN] backup / Restore test: No BACKUP_LAST_RESTORE_TEST_AT value is configured; perform a restore test in staging.
Backup verification completed.
```

Remaining readiness warnings:

- Backup verification remains WARN until `BACKUP_LAST_VERIFIED_AT` is configured from real provider evidence.
- Restore verification remains WARN until `BACKUP_LAST_RESTORE_TEST_AT` is configured after a non-production restore rehearsal.
- Render free PostgreSQL still limits managed backup/restore proof; use a supported plan/provider path or a manual `pg_dump`/restore rehearsal.
- Scheduled jobs now have Render execution evidence through the hardened runner. Set `SCHEDULED_JOBS_CONFIGURED=True` once the staging/prod env reflects this configuration.
- Redis is now configured and verified in Render staging; bid throttling uses the shared cache path.
- Media storage now reports object storage enabled in Render staging; uploaded lot images are no longer dependent on Render local filesystem storage.
- Admin smoke checks confirm audit logs, fulfillment records, outbound notifications, and repair workflow Django admin pages load. Final RC smoke confirms admin export CSV, notification unread count, and mark-read behavior.

## Post-Deploy Smoke Checklist

| Area | Check | Result | Evidence / notes |
| --- | --- | --- | --- |
| Health | Backend `/api/health/` returns ok | PASS | `https://bidals.onrender.com/api/health/` returned 200 OK with backend service payload. |
| Health | Frontend `/api/health` returns ok | PASS | `https://bidals-1.onrender.com/api/health` returned 200 OK with frontend service payload. |
| Auth | Register works | PASS | Created `phase17_seller_1777996033` and `phase17_bidder_1777996033` through `POST /api/auth/register/`. |
| Auth | Login works | PASS | Seller and bidder received JWT login responses through `POST /api/auth/login/`. |
| Core | Create auction | PASS | Seller created auction `PHASE17 SMOKE AUCTION 1777996033`, id `2`, status `live`. |
| Core | Create lot | PASS | Seller created lot `PHASE17 SMOKE LOT 1777996033`, id `2`, status `open`, starting/current price `10.00`, increment `5.00`. |
| Core | View auction feed | PASS | `GET /api/auctions/` returned `200 OK`, `count=2`, including Phase 17 smoke auction. Frontend Browse empty state is confirmed fixed for empty data. |
| Core | View lot detail | PASS | `GET /api/lots/2/` returned `200 OK`, lot status `open`, current price `10.00`. |
| Bidding | Valid bid accepted by backend | PASS | After redeploy commit `cb9ca78`, fresh `POST /api/lots/4/bid/` with bidder token and amount `15.00` returned `201` with `{"status":"accepted","bid_id":3,"current_price":"15.00"}`. Redis reconnect smoke rerun also passed on lot id `9`: valid bid amount `15.00` returned `201 accepted`, bid id `6`, current price `15.00`. |
| Bidding | Invalid bid rejected by backend | PASS | Fresh `POST /api/lots/4/bid/` with bidder token and amount `16.00` returned controlled `409` response with `{"status":"rejected","reason":"INVALID_INCREMENT","current_price":"15.00"}`. Redis reconnect smoke rerun on lot id `9` returned controlled `409 INVALID_INCREMENT`, bid id `7`, current price still `15.00`; anonymous bid amount `20.00` returned controlled `401 UNAUTHENTICATED`. |
| Bidding | Failed bid attempts do not corrupt lot state | PASS | Lot id `4` current price was `10.00` before bidding, `15.00` after the valid bid, and stayed `15.00` after both invalid and anonymous rejected attempts. Redis reconnect smoke rerun lot id `9` followed the same pattern: `10.00` before bid, `15.00` after accepted bid, and still `15.00` after rejected/anonymous attempts. |
| Bidding | Bid history correct | PASS | Public `GET /api/lots/4/bids/` returned one accepted bid id `3`. Seller-authenticated `GET /api/lots/4/bids/` returned rejected bid id `4` (`INVALID_INCREMENT`) plus accepted bid id `3`. Redis reconnect smoke rerun lot id `9`: public bid history returned accepted bid id `6`; seller bid history returned rejected bid id `7` (`INVALID_INCREMENT`) plus accepted bid id `6`. |
| Bidding | Bid audit logs created | PASS | Final RC smoke confirmed bid audit records through `GET /api/lots/{lot_id}/audit/`, including `bid_accepted` and `bid_rejected`. |
| Lifecycle | Scheduler jobs execute with production settings | PASS | Render cron jobs now run through `sh /app/scripts/run_scheduled_job.sh ...` and show `settings_module=bidals.settings.prod`, `database_engine=django.db.backends.postgresql`, `required_env=pass`, `redis_env=pass`, and `s3_env=pass`. |
| Lifecycle | Scheduler closes ended auction | PASS | Final RC smoke confirmed auction closing and winner calculation against Render staging after cron execution was verified. |
| Lifecycle | Winner calculated from accepted bids only | PASS | Final RC smoke confirmed the winner/outcome was calculated from the accepted backend bid created by the smoke run. |
| Fulfillment | Seller sees fulfillment dashboard | PASS | Seller `GET /api/dashboard/fulfillment/` returned `200 OK` during earlier smoke, and final RC smoke verified fulfillment update after winner calculation. |
| Fulfillment | Seller updates fulfillment status | PASS | Final RC smoke confirmed fulfillment update through backend-owned fulfillment state. |
| Fulfillment | Bidder sees won lots | PASS | Final RC smoke confirmed bidder won-lots reflects backend-owned winner/fulfillment state. |
| Notifications | Notification created | PASS | Final RC smoke confirmed a notification was created during the backend-owned lifecycle flow. |
| Notifications | Unread count updates | PASS | Final RC smoke confirmed unread count increments for the bidder notification. |
| Notifications | Mark as read works | PASS | Final RC smoke confirmed mark-read behavior. |
| Readiness | `release_check` core checks | PASS | Render shell `python manage.py release_check` now passes health endpoint, migrations, audit logs, and admin export installation/protection. Remaining items are WARN only. |
| Readiness | `deployment_check --production` core checks | PASS | Render shell `python manage.py deployment_check --production` now passes DEBUG, SECRET_KEY, ALLOWED_HOSTS, DATABASE, REDIS, MEDIA_STORAGE, EMAIL disabled safely, MIGRATIONS, and HEALTH. |
| Readiness | `verify_backup` | WARN | Render shell `python manage.py verify_backup` passes database connectivity and critical tables, but warns because backup timestamp and restore-test timestamp are not configured. |
| Readiness | Redis and media production readiness | PASS | Render shell `deployment_check --production` now reports REDIS pass and MEDIA_STORAGE pass: Redis cache is enabled, and object storage is enabled. |
| Admin ops | Django admin access | PASS | `https://bidals.onrender.com/admin/` loads successfully; logged in as `staging_admin`; Django admin shows core BIDALS and auth/token blacklist models. |
| Fulfillment | Fulfillment records visible | PASS | Django admin Fulfillment records page loads without errors; no entries yet. |
| Notifications | Outbound notifications visible | PASS | Django admin Outbound notifications page loads without errors; no entries yet. |
| Repair | Admin creates repair request | WARN | Repair workflow access passed. Full repair create/approve/apply was skipped because `RC_SMOKE_ADMIN2_USERNAME` and `RC_SMOKE_ADMIN2_PASSWORD` are not configured. |
| Repair | Different admin approves repair | WARN | Full two-admin repair flow remains untested until a second staging admin is configured. |
| Repair | Approved repair applies | WARN | Full two-admin repair flow remains untested until a second staging admin is configured. |
| Repair | Repair workflow access loads | PASS | Django admin Outcome repair requests and Outcome repair comments pages load without errors; no entries yet. |
| Repair | Audit logs created | WARN | Audit logs page is visible, but repair-specific audit creation still needs workflow smoke evidence. |
| Admin ops | Admin export downloads CSV | PASS | Final RC smoke confirmed admin export CSV works. |
| Admin ops | Audit logs visible | PASS | Django admin Audit logs page loads and shows recent entries. |
| Admin ops | Release check UI works | WARN | Admin Django access is confirmed; release-check UI/API still needs direct smoke evidence. |
| Seller flow | Create lot single-submit protection | PASS | Final RC smoke confirms normal create-lot flow creates the expected lot. Create/edit lot forms also include a synchronous in-flight guard plus disabled submit/loading state so rapid double-clicks cannot submit duplicate `POST /api/lots/` calls. |
| Seller flow | Lot image upload foundation | PASS | Final RC smoke confirms lot image upload works. Backend `LotImage` upload/delete/reorder APIs remain seller/admin protected, uploads use multipart `FormData` with JWT auth, and Render staging uses object storage for persistence. |
| Seller flow | Auction-derived lot availability | PASS | Backend rejects `status=open` for draft, ended, or cancelled auctions. Scheduled auctions may prepare open lots, but bidding remains rejected until server time and auction status are live. Frontend helper text says lots only become bid-open when the auction is live. |

## Issues Found

| Severity | Issue | Steps to reproduce | Status |
| --- | --- | --- | --- |
| Critical | Staging bid endpoint returned `500` for authenticated valid bid, authenticated invalid bid, and anonymous bid probe. | Original failure reproduced on lot id `2`. After redeploy commit `cb9ca78`, fresh lot id `4` was tested with valid, invalid, and anonymous bid attempts. | FIXED AND VERIFIED - valid bid now returns `201 accepted`, invalid increment returns controlled `409 INVALID_INCREMENT`, anonymous bid returns controlled `401 UNAUTHENTICATED`, and lot state remains authoritative. |
| Medium | Frontend Browse page treated staging empty auction data as an error state. | Open `https://bidals-1.onrender.com/auctions` while `GET https://bidals.onrender.com/api/auctions/` returns `{"count":0,"next":null,"previous":null,"results":[]}`. | FIXED AND VERIFIED |
| High | Documented staging admin credentials were not available. | Earlier `POST /api/auth/login/` with `staging_admin` / `ChangeMe123!` returned `401`; staging admin setup was then repaired. | FIXED AND VERIFIED - `https://bidals.onrender.com/admin/` loads successfully and `staging_admin` can log in. |
| High | Backup restore still needs real evidence. | Attempt Phase 17 completion without managed PostgreSQL restore proof. | OPEN/WARN - scheduler execution is verified for all cron jobs through the hardened runner; backup/restore proof remains open. |
| High | Render cron jobs can fall back to SQLite/dev settings when run as raw inline commands. | `python manage.py monitor_bid_anomalies --window-minutes 60` in Render cron failed with `django.db.utils.OperationalError: unable to open database file`. A later relative wrapper command failed with `sh: 0: cannot open scripts/run_scheduled_job.sh: No such file`. | FIXED AND VERIFIED - all cron jobs now use `sh /app/scripts/run_scheduled_job.sh ...` and show production settings plus PostgreSQL diagnostics. |
| Medium | Managed backup restore cannot be fully verified on current free Render Postgres setup. | Try to provide provider-managed backup/restore evidence from free staging database. | OPEN/WARN - use supported Render plan/provider restore path or manual non-production `pg_dump` restore rehearsal. |
| Medium | `release_check` and `deployment_check --production` failed in Render shell because the health probe hit `/api/health` and received Django's trailing-slash `301` redirect. | Run `python manage.py release_check` or `python manage.py deployment_check --production` in Render shell before the readiness health-path fix. | FIXED AND VERIFIED - Render shell checks now pass the health endpoint after switching readiness checks to `/api/health/` with redirect-safe behavior. |
| High | Create lot form could create duplicate lots during demo flow. | Rapid repeat submit, or retry after a post-create image-upload failure, could send another lot create request. | FIXED - frontend has a synchronous in-flight submit guard, disabled submit state, and post-create image upload retry path that does not create another lot. Final RC smoke confirms normal create-lot flow. |
| Medium | Seller lot form could imply a draft auction lot was bid-open. | Create/edit lot form allowed selecting `open` without clearly deriving availability from auction status. | FIXED - backend rejects open lots for draft/ended/cancelled auctions; frontend disables misleading open state and explains auction-live requirement. |
| Medium | Lot image upload needed demo-readiness polish. | Seller create/edit flow had upload hooks but limited feedback/preview, and local media serving was not explicitly staging-controlled. | FIXED AND VERIFIED - final RC smoke confirms upload lot image passes; Render staging now uses object storage instead of ephemeral local media. |
| High | Edit lot image upload showed generic `Request failed`. | Save a lot from `/dashboard/lots/{id}/edit` with an uploaded image while staging local media storage is unavailable or unwritable. | FIXED - `backend/Dockerfile` creates writable `/app/media` for local fallback, backend validates local storage availability before saving files, API errors name the image storage problem, and staging object storage now avoids ephemeral local media. |

## Remaining Phase 17 Manual Checks

- Complete backup/restore proof: create or identify a managed PostgreSQL backup, restore into staging or a restore-test database, and record `BACKUP_LAST_VERIFIED_AT` plus `BACKUP_LAST_RESTORE_TEST_AT`.
- Re-run `python manage.py verify_backup` after backup metadata is configured.
- Re-run `python manage.py release_check` after backup/restore proof is recorded so the command output reflects the final go/no-go state.
- Configure `RC_SMOKE_ADMIN2_USERNAME` and `RC_SMOKE_ADMIN2_PASSWORD` for a second staging admin, then rerun the release candidate smoke suite if the full two-admin repair create/approve/apply flow should be cleared from `WARN`.
- Optional: upload a lot image, redeploy/restart Render, and confirm the image still loads from object storage as a persistence spot check.
- Optional: keep monitoring Redis-backed bid throttling and scheduled job logs during normal staging use.

Phase 18 adds the repeatable path for the first three bullets:

- [`disaster-recovery.md`](disaster-recovery.md) documents Render PostgreSQL backup/restore rehearsal, `pg_dump`, restore-test validation, and disaster recovery.
- [`production-release-checklist.md`](production-release-checklist.md) documents the production go/no-go gate.
- [`rollback-runbook.md`](rollback-runbook.md) documents code rollback, migration-aware rollback, and database recovery rollback.
- Helper scripts are available at `scripts/pg_dump_backup.sh`, `scripts/restore_to_test_db.sh`, and `scripts/post_restore_validate.sh`.

## Production Go/No-Go

Must-have before production:

- Backup/restore proof: complete a non-production restore rehearsal or move staging to a provider/plan where restore evidence can be captured, then set `BACKUP_LAST_VERIFIED_AT` and `BACKUP_LAST_RESTORE_TEST_AT`.

Completed release gates:

- Release candidate smoke: final Render staging rerun reports `PASS=19`, `WARN=2`, `FAIL=0`. See [`release-candidate-smoke.md`](release-candidate-smoke.md).
- Core backend-owned lifecycle: auth, auction creation, lot creation, lot image upload, browse, valid bid acceptance, invalid bid rejection, bid history, bid audit logs, admin export CSV, auction closing, winner calculation, fulfillment update, bidder won-lots, notification unread/mark-read, and repair workflow access are verified in staging.

Nice-to-have operational improvements:

- Add exact Render cron job names and last-run timestamps to this document.
- Add the release candidate smoke suite to CI or a manual release checklist once staging credentials are available in a secure secret store.
- Add dashboard evidence screenshots for operations, fulfillment, notifications, and repair pages.
- Add provider-managed backup screenshots or links to provider runbook entries once the database plan supports them.
- Enable staging Sentry DSN for non-secret exception capture before production cutover.
- Configure a second staging admin and rerun `RC_SMOKE_REPAIR_MODE=full` so the full two-admin repair create/approve/apply path moves from `WARN` to `PASS`.

## Release Candidate Smoke Gate

Run this before production approval:

```bash
cd frontend
npm run smoke:release-candidate
```

Required environment variables are documented in [`release-candidate-smoke.md`](release-candidate-smoke.md). The gate is API-level and validates backend-owned state against deployed staging URLs. It does not trigger frontend-side bid validation or script-side winner calculation.

Attach the generated `PASS/WARN/FAIL` summary here after each run:

```text
Release candidate smoke summary, final Render rerun after audit endpoint fix:
PASS=19
WARN=2
FAIL=0

WARN:
- Second admin login was not configured.
- Full two-admin repair create/approve/apply was skipped because RC_SMOKE_ADMIN2_USERNAME/PASSWORD were not configured.

Confirmed PASS checks:
- Frontend health
- Seller login
- Bidder login
- Admin login
- Create live auction
- Create lot
- Upload lot image
- Browse created auction and lot
- Valid bid accepted by backend
- Invalid bid controlled rejection
- Bid history
- Bid audit log check through GET /api/lots/{lot_id}/audit/
- Admin export CSV
- Auction closing and winner calculation
- Fulfillment update
- Bidder won-lots reflects backend state
- Notification unread and mark-read
- Repair workflow access

Audit endpoint note:
- The first RC smoke run failed the audit check because it queried the global audit endpoint with direct lot entity filters.
- The corrected smoke suite uses GET /api/lots/{lot_id}/audit/, which includes bid audit records linked by metadata.lot_id.
- The final rerun confirms bid_accepted and bid_rejected audit evidence.
```

## Final Readiness Assessment

Status: RELEASE CANDIDATE SMOKE PASS / PRODUCTION GO-NO-GO PENDING BACKUP RESTORE PROOF

Reason: The release candidate smoke gate passes with `PASS=19`, `WARN=2`, `FAIL=0`. Core backend-owned auction lifecycle is verified in Render staging: auth, auction/lot creation, image upload, browse, server-authoritative valid and invalid bidding, bid history, bid audit logs, admin export CSV, scheduler-backed auction close, winner calculation from accepted backend bid records, fulfillment update, bidder won-lots, notification unread/mark-read, and repair workflow access. Production go/no-go is still pending backup/restore proof. Full two-admin repair create/approve/apply remains a `WARN` until a second staging admin is configured.
