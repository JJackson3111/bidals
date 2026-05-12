# BIDALS Phase 17 Staging Rehearsal

Provider selected: Render

Status: PARTIAL - staging core is healthy. Backend and frontend staging services are deployed, health/browse/auth/create/bidding flows have live evidence, the Browse empty-state issue is fixed, the bid endpoint `500` regression is fixed and verified after backend redeploy commit `cb9ca78`, and Render shell readiness checks now pass health, migrations, Redis cache, object storage, and audit-related checks. Production readiness still requires scheduler jobs, backup restore evidence, and final admin workflow checks.

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
  - `./scripts/run_scheduled_job.sh close_expired_auctions`
  - `./scripts/run_scheduled_job.sh monitor_bid_anomalies --window-minutes 60`
  - `./scripts/run_scheduled_job.sh deliver_notifications`
- Readiness commands:
  - `python manage.py deployment_check --production`
  - `python manage.py verify_backup`
  - `python manage.py release_check`

## Render Staging Deployment Plan

1. Create a Render managed PostgreSQL service for staging.
2. Create a Render Redis instance for shared cache/throttling.
3. Create the backend web service from the GitHub repository. `PARTIAL PASS`: backend is reachable at `https://bidals.onrender.com`.
4. Set backend root/directory to `backend` if using Render's repository directory setting.
5. Use `backend/Dockerfile`.
6. Set health check path to `/api/health/`.
7. Set pre-deploy/release command to:

```bash
python manage.py migrate
```

8. Create the frontend web service from the same GitHub repository. `PARTIAL PASS`: frontend is reachable at `https://bidals-1.onrender.com`.
9. Use `frontend/Dockerfile.prod`.
10. Set the frontend build arg/env value:

```bash
NEXT_PUBLIC_API_BASE_URL=https://<backend-staging-host>/api
```

11. Set frontend health check path to `/api/health`.
12. Confirm both services deploy from GitHub and report healthy. `PARTIAL PASS`: backend health and frontend page load have been confirmed.

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
| Render `release_check` | PASS/WARN | Render shell check now passes health endpoint, migrations, audit logs, and admin export installation/protection. Remaining WARN items are backup, scheduled jobs, fulfillment, repair workflow, and notification unread count. |
| Render `deployment_check --production` | PASS | Render shell check now passes DEBUG, SECRET_KEY, ALLOWED_HOSTS, DATABASE, REDIS, MEDIA_STORAGE, EMAIL disabled safely, MIGRATIONS, and HEALTH. |
| Django admin access | PASS | `https://bidals.onrender.com/admin/` loads successfully and `staging_admin` can log in. Django admin shows Users, Auctions, Bids, Fulfillment records, Lots, Audit logs, Outbound notifications, Outcome repair requests/comments, and token blacklist models. |

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
- `SCHEDULED_JOBS_CONFIGURED=True` after schedulers are configured
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
- Environment variables: copy the backend web service env group/secrets, including `DJANGO_SETTINGS_MODULE=bidals.settings.prod`, `DATABASE_URL` or `DJANGO_DATABASE_URL`, Redis vars, object-storage vars, alert/email vars as needed.

| Job | Command | Suggested frequency | Result |
| --- | --- | --- | --- |
| Auction closing and winner calculation | `./scripts/run_scheduled_job.sh close_expired_auctions` | Every 1 minute, or the shortest Render-supported interval | PASS for one-off/manual run; cron evidence still needed |
| Bid anomaly monitoring | `./scripts/run_scheduled_job.sh monitor_bid_anomalies --window-minutes 60` | Every 5 minutes | OPEN - use wrapper to prevent SQLite/dev fallback |
| Notification delivery | `./scripts/run_scheduled_job.sh deliver_notifications` | Every 5 minutes if email enabled | OPEN - use wrapper to prevent SQLite/dev fallback |

Evidence to capture:

- Render scheduler name:
- Last run timestamp:
- Log excerpt showing success:
- Expected safe diagnostics:
  - `scheduled_job=<job_name>`
  - `settings_module=bidals.settings.prod`
  - `database_engine=django.db.backends.postgresql`
  - `use_redis_cache=True`
- Audit log event visible in `/dashboard/operations`:

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
| Users exist | Admin, seller, bidder users present | WARN - seller/bidder smoke users created; admin user not available through documented staging credentials |
| Auctions exist | Live/scheduled/ended auctions present | PASS - smoke auction created through backend API |
| Lots exist | Lots linked to auctions | PASS - smoke lot created through backend API |
| Bids exist | Accepted and rejected bids present | PASS for live staging smoke data - fresh lot id `4` has accepted bid id `3` and authenticated rejected bid id `4`; managed backup restore evidence is still WARN until a restore rehearsal is performed |
| Audit logs exist | Audit events readable | WARN - admin credentials unavailable, audit endpoint not verified |

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
./scripts/run_scheduled_job.sh close_expired_auctions
./scripts/run_scheduled_job.sh monitor_bid_anomalies --window-minutes 60
./scripts/run_scheduled_job.sh deliver_notifications
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

Remaining WARN checks:
[WARN] database / Backup verification
[WARN] ops / Scheduled jobs
[WARN] core_flows / Fulfillment workflow
[WARN] notifications / Unread count
[WARN] ops / Repair workflow
```

Admin access probe:

- Earlier `POST /api/auth/login/` with `staging_admin` / `ChangeMe123!` returned `401` before the staging admin setup was repaired.
- Current evidence: `https://bidals.onrender.com/admin/` loads successfully and `staging_admin` can log into Django admin.
- Django admin model visibility confirmed: Users, Auctions, Bids, Fulfillment records, Lots, Audit logs, Outbound notifications, Outcome repair requests/comments, and token blacklist models.
- API/JWT admin smoke checks still need direct validation through the frontend or API client.

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
- Scheduled jobs still need Render cron execution evidence and `SCHEDULED_JOBS_CONFIGURED=true` only after that evidence exists.
- Redis is now configured and verified in Render staging; bid throttling uses the shared cache path.
- Media storage now reports object storage enabled in Render staging; uploaded lot images are no longer dependent on Render local filesystem storage.
- Admin smoke checks now confirm audit logs, fulfillment records, outbound notifications, and repair workflow Django admin pages load. Frontend/admin export CSV and notification mark-read still need live smoke evidence.

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
| Lifecycle | Scheduler closes ended auction | WARN | Render cron/job setup evidence has not been provided. Bid endpoint is now verified; closing/winner calculation still requires scheduler execution evidence. |
| Lifecycle | Winner calculated from accepted bids only | WARN | Not verified; depends on `close_expired_auctions` execution against a lot with accepted bids. |
| Fulfillment | Seller sees fulfillment dashboard | PASS | Seller `GET /api/dashboard/fulfillment/` returned `200 OK` with empty summary/results. End-to-end fulfillment still needs a calculated winner. |
| Fulfillment | Seller updates fulfillment status | WARN | Not verified because no winner/fulfillment record exists yet. |
| Fulfillment | Bidder sees won lots | WARN | Not verified because no winning bid/winner outcome exists yet. |
| Notifications | Notification created | WARN | Not verified because winner/fulfillment flows have not run. |
| Notifications | Unread count updates | PASS | Bidder `GET /api/account/notifications/unread-count/` returned `200 OK` with `unread_count=0`. Mark-read still needs an actual notification. |
| Notifications | Mark as read works | WARN | Not verified because no notification exists yet. |
| Readiness | `release_check` core checks | PASS | Render shell `python manage.py release_check` now passes health endpoint, migrations, audit logs, and admin export installation/protection. Remaining items are WARN only. |
| Readiness | `deployment_check --production` core checks | PASS | Render shell `python manage.py deployment_check --production` now passes DEBUG, SECRET_KEY, ALLOWED_HOSTS, DATABASE, REDIS, MEDIA_STORAGE, EMAIL disabled safely, MIGRATIONS, and HEALTH. |
| Readiness | `verify_backup` | WARN | Render shell `python manage.py verify_backup` passes database connectivity and critical tables, but warns because backup timestamp and restore-test timestamp are not configured. |
| Readiness | Redis and media production readiness | PASS | Render shell `deployment_check --production` now reports REDIS pass and MEDIA_STORAGE pass: Redis cache is enabled, and object storage is enabled. |
| Admin ops | Django admin access | PASS | `https://bidals.onrender.com/admin/` loads successfully; logged in as `staging_admin`; Django admin shows core BIDALS and auth/token blacklist models. |
| Fulfillment | Fulfillment records visible | PASS | Django admin Fulfillment records page loads without errors; no entries yet. |
| Notifications | Outbound notifications visible | PASS | Django admin Outbound notifications page loads without errors; no entries yet. |
| Repair | Admin creates repair request | WARN | Outcome repair request/comment admin pages load, but creating a repair request was not tested. |
| Repair | Different admin approves repair | WARN | Not verified; requires a second admin account and a repair request. |
| Repair | Approved repair applies | WARN | Not verified; requires eligible accepted bid/outcome data and repair request approval. |
| Repair | Repair workflow access loads | PASS | Django admin Outcome repair requests and Outcome repair comments pages load without errors; no entries yet. |
| Repair | Audit logs created | WARN | Audit logs page is visible, but repair-specific audit creation still needs workflow smoke evidence. |
| Admin ops | Admin export downloads CSV | WARN | `release_check` reports admin export installed/protected, but CSV download still needs a browser/API smoke check. |
| Admin ops | Audit logs visible | PASS | Django admin Audit logs page loads and shows recent entries. |
| Admin ops | Release check UI works | WARN | Admin Django access is confirmed; release-check UI/API still needs direct smoke evidence. |
| Seller flow | Create lot single-submit protection | PASS in code / redeploy needed | Create/edit lot forms now use a synchronous in-flight guard plus disabled submit/loading state so rapid double-clicks cannot submit duplicate `POST /api/lots/` calls. |
| Seller flow | Lot image upload foundation | PASS in code / redeploy needed | Backend `LotImage` upload/delete/reorder APIs remain seller/admin protected. Upload requests use multipart `FormData` with JWT auth. Local fallback creates writable `/app/media`, and production should set `USE_S3=True` with Cloudflare R2/S3-compatible env vars so uploaded images persist across redeploys. |
| Seller flow | Auction-derived lot availability | PASS in code / redeploy needed | Backend rejects `status=open` for draft, ended, or cancelled auctions. Scheduled auctions may prepare open lots, but bidding remains rejected until server time and auction status are live. Frontend helper text now says lots only become bid-open when the auction is live. |

## Issues Found

| Severity | Issue | Steps to reproduce | Status |
| --- | --- | --- | --- |
| Critical | Staging bid endpoint returned `500` for authenticated valid bid, authenticated invalid bid, and anonymous bid probe. | Original failure reproduced on lot id `2`. After redeploy commit `cb9ca78`, fresh lot id `4` was tested with valid, invalid, and anonymous bid attempts. | FIXED AND VERIFIED - valid bid now returns `201 accepted`, invalid increment returns controlled `409 INVALID_INCREMENT`, anonymous bid returns controlled `401 UNAUTHENTICATED`, and lot state remains authoritative. |
| Medium | Frontend Browse page treated staging empty auction data as an error state. | Open `https://bidals-1.onrender.com/auctions` while `GET https://bidals.onrender.com/api/auctions/` returns `{"count":0,"next":null,"previous":null,"results":[]}`. | FIXED AND VERIFIED |
| High | Documented staging admin credentials were not available. | Earlier `POST /api/auth/login/` with `staging_admin` / `ChangeMe123!` returned `401`; staging admin setup was then repaired. | FIXED AND VERIFIED - `https://bidals.onrender.com/admin/` loads successfully and `staging_admin` can log in. |
| High | Scheduler and backup restore still need real Render execution evidence. | Attempt Phase 17 completion without Render scheduler logs and managed PostgreSQL restore proof. | OPEN - `close_expired_auctions` worked after path/env fixes, but `monitor_bid_anomalies` still hit SQLite/dev fallback. Scheduled jobs now must use `./scripts/run_scheduled_job.sh ...`; scheduler logs and restore proof remain. |
| High | Render cron jobs can fall back to SQLite/dev settings when run as raw inline commands. | `python manage.py monitor_bid_anomalies --window-minutes 60` in Render cron failed with `django.db.utils.OperationalError: unable to open database file`. | FIXED IN CODE / PENDING REDEPLOY - use `backend/scripts/run_scheduled_job.sh` for all scheduled jobs. The wrapper forces `bidals.settings.prod`, requires `DATABASE_URL` or `DJANGO_DATABASE_URL`, changes into the backend directory, and prints safe diagnostics before execution. |
| Medium | Managed backup restore cannot be fully verified on current free Render Postgres setup. | Try to provide provider-managed backup/restore evidence from free staging database. | OPEN/WARN - use supported Render plan/provider restore path or manual non-production `pg_dump` restore rehearsal. |
| Medium | `release_check` and `deployment_check --production` failed in Render shell because the health probe hit `/api/health` and received Django's trailing-slash `301` redirect. | Run `python manage.py release_check` or `python manage.py deployment_check --production` in Render shell before the readiness health-path fix. | FIXED AND VERIFIED - Render shell checks now pass the health endpoint after switching readiness checks to `/api/health/` with redirect-safe behavior. |
| High | Create lot form could create duplicate lots during demo flow. | Rapid repeat submit, or retry after a post-create image-upload failure, could send another lot create request. | FIXED IN CODE / PENDING REDEPLOY - frontend now has a synchronous in-flight submit guard, disabled submit state, and post-create image upload retry path that does not create another lot. |
| Medium | Seller lot form could imply a draft auction lot was bid-open. | Create/edit lot form allowed selecting `open` without clearly deriving availability from auction status. | FIXED IN CODE / PENDING REDEPLOY - backend rejects open lots for draft/ended/cancelled auctions; frontend disables misleading open state and explains auction-live requirement. |
| Medium | Lot image upload needed demo-readiness polish. | Seller create/edit flow had upload hooks but limited feedback/preview, and local media serving was not explicitly staging-controlled. | FIXED IN CODE / PENDING REDEPLOY - image previews added, upload retry path improved, local media serving controlled by `SERVE_LOCAL_MEDIA`, and production object storage remains required. |
| High | Edit lot image upload showed generic `Request failed`. | Save a lot from `/dashboard/lots/{id}/edit` with an uploaded image while staging local media storage is unavailable or unwritable. | FIXED IN CODE / PENDING REDEPLOY - `backend/Dockerfile` now creates writable `/app/media`, backend validates local storage availability before saving files, API errors name the image storage problem, and the edit form keeps the page usable while showing the backend error. |

## Remaining Phase 17 Manual Checks

- Optional: inspect Render backend logs for previous `POST /api/lots/{id}/bid/` 500s and confirm no new cache/Redis exceptions after commit `cb9ca78`.
- Continue monitoring Redis-backed bid throttling during live smoke tests; Redis is now configured and verified by `deployment_check --production`.
- Continue using object storage for persistent media; `deployment_check --production` now reports MEDIA_STORAGE pass. Optional follow-up: upload a lot image, redeploy/restart Render, and confirm the image still loads from object storage.
- Run `python manage.py migrate` on the staging backend and confirm no unapplied migrations.
- Configure Render scheduled jobs for auction closing, anomaly monitoring, and notification delivery using `./scripts/run_scheduled_job.sh ...`.
- Capture successful scheduler logs showing `settings_module=bidals.settings.prod` and `database_engine=django.db.backends.postgresql`; confirm related audit/operations visibility.
- Create or identify a managed PostgreSQL backup, or document the free Render Postgres limitation and run a non-production manual restore rehearsal when possible.
- Restore the backup/dump into staging or a restore-test database.
- Re-run `python manage.py verify_backup` after recording backup metadata.
- Re-run `python manage.py release_check` after scheduler, backup, fulfillment, notification, and repair workflow checks are complete.
- After redeploy, re-test seller create lot: one click creates exactly one lot, the submit button disables while saving, image upload/preview works, and draft auctions cannot create truly bid-open lots.
- Execute remaining smoke checks: admin export CSV download, scheduler close/winner calculation, fulfillment update, won-lots page, notification mark-read, repair request create/approve/apply if practical, and release-check UI.

## Final Readiness Assessment

Status: NOT READY FOR PRODUCTION FROM PHASE 17 YET

Reason: Staging core is healthy: backend/frontend health, auth, auction/lot creation, browse, bidding, migrations, Redis-backed cache readiness, object-storage readiness, audit log readability, Django admin login, audit log visibility, fulfillment/notification/repair admin page access, and admin export installation/protection have live Render evidence. Bidding smoke passes with server-authoritative accepted/rejected responses and safe lot state. Production is still blocked on scheduled job execution proof, backup restore evidence, admin export CSV verification, and final workflow checks for fulfillment updates, notification mark-read, repair request lifecycle, and release-check UI.
