# BIDALS Phase 17 Staging Rehearsal

Provider selected: Render

Status: PARTIAL - backend and frontend staging services are deployed, health/browse/auth/create/bidding flows have live evidence, the Browse empty-state issue is fixed, and the bid endpoint `500` regression is fixed and verified after backend redeploy commit `cb9ca78`. Remaining Phase 17 work is focused on admin credentials, scheduler proof, backup/restore evidence, and `release_check`.

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
- Scheduler commands:
  - `python manage.py close_expired_auctions`
  - `python manage.py monitor_bid_anomalies --window-minutes 60`
  - `python manage.py deliver_notifications`
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
- `REDIS_URL=<Render Redis URL>` if `USE_REDIS_CACHE=True`
- `USE_REDIS_CACHE=True` with a reachable Redis service; use `USE_REDIS_CACHE=False` only for staging without Redis, understanding rate-limit counters become per-process local memory
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
- `USE_S3=True` only if object storage is configured for staging
- `BACKUP_PROVIDER=render`
- `BACKUP_LAST_VERIFIED_AT=<ISO-8601 timestamp after backup is verified>`
- `BACKUP_LAST_RESTORE_TEST_AT=<ISO-8601 timestamp after restore test passes>`

Frontend:

- `NEXT_PUBLIC_API_BASE_URL=https://<backend-staging-host>/api`
- `NEXT_TELEMETRY_DISABLED=1`

## Scheduler Configuration

Configure Render Cron Jobs or scheduled backend jobs using the same backend image and environment as the web service.

| Job | Command | Suggested frequency | Result |
| --- | --- | --- | --- |
| Auction closing and winner calculation | `python manage.py close_expired_auctions` | Every 1 minute, or the shortest Render-supported interval | WARN - setup evidence not provided |
| Bid anomaly monitoring | `python manage.py monitor_bid_anomalies --window-minutes 60` | Every 5 minutes | WARN - setup evidence not provided |
| Notification delivery | `python manage.py deliver_notifications` | Every 5 minutes if email enabled | WARN - setup evidence not provided |

Evidence to capture:

- Render scheduler name:
- Last run timestamp:
- Log excerpt showing success:
- Audit log event visible in `/dashboard/operations`:

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
python manage.py seed_staging_data
python manage.py deployment_check --production
python manage.py verify_backup
python manage.py release_check
python manage.py close_expired_auctions
python manage.py monitor_bid_anomalies --window-minutes 60
python manage.py deliver_notifications
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
RENDER SHELL RESULT BEFORE HEALTH-PATH FIX

Command:
python manage.py release_check

Result:
FAIL - the only reported failure was the health endpoint check returning 301 because the command checked /api/health instead of /api/health/.

Relevant sanitized output:
[FAIL] system / Health endpoint: Health endpoint returned status 301.

Fix applied in code:
release_check now checks /api/health/ and follows redirects safely. Local verification after the fix shows:
[PASS] system / Health endpoint: Backend health endpoint /api/health/ responds with a request id.

Expected after redeploy:
No release_check failure from the health endpoint. Remaining WARN items are operational/manual readiness items listed below.
```

Admin API probe:

- `POST /api/auth/login/` with `staging_admin` / `ChangeMe123!` returned `401` with `No active account found with the given credentials`.
- `GET /api/admin/release-check/` was not executed because no admin token was available.

## deployment_check Output

Paste sanitized staging output here:

```text
RENDER SHELL RESULT BEFORE HEALTH-PATH FIX

Command:
python manage.py deployment_check --production

Result:
FAIL - the only reported failure was the health endpoint check returning 301 because the command checked /api/health instead of /api/health/.

Relevant sanitized output:
[FAIL] HEALTH: Health endpoint returned status 301.

Fix applied in code:
deployment_check now checks /api/health/ and follows redirects safely. Local verification after the fix shows:
[PASS] HEALTH: Backend health endpoint /api/health/ responds with a request id.

Expected after redeploy:
No deployment_check failure from the health endpoint.
```

## verify_backup Output

Paste sanitized staging output here:

```text
Command:
python manage.py verify_backup

Observed/expected output shape for current Render staging:
[PASS] database / Connectivity: Database connection is usable.
[PASS] database / Critical tables: Critical BIDALS tables are present.
[WARN] backup / Backup timestamp: No BACKUP_LAST_VERIFIED_AT value is configured; verify backups in the cloud provider.
[WARN] backup / Restore test: No BACKUP_LAST_RESTORE_TEST_AT value is configured; perform a restore test in staging.
Backup verification completed.
```

Remaining readiness warnings after the health-path fix:

- Backup verification remains WARN until `BACKUP_LAST_VERIFIED_AT` is configured from real provider evidence.
- Restore verification remains WARN until `BACKUP_LAST_RESTORE_TEST_AT` is configured after a non-production restore rehearsal.
- Render free PostgreSQL still limits managed backup/restore proof; use a supported plan/provider path or a manual `pg_dump`/restore rehearsal.
- Scheduled jobs still need Render cron execution evidence and `SCHEDULED_JOBS_CONFIGURED=true` only after that evidence exists.
- Admin-only release UI/export/repair/audit checks still need a valid staging admin account.
- Release check still contains manual WARN items for winner calculation, fulfillment, notifications mark-read, and repair workflow until those smoke checks are performed.

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
| Bidding | Valid bid accepted by backend | PASS | After redeploy commit `cb9ca78`, fresh `POST /api/lots/4/bid/` with bidder token and amount `15.00` returned `201` with `{"status":"accepted","bid_id":3,"current_price":"15.00"}`. |
| Bidding | Invalid bid rejected by backend | PASS | Fresh `POST /api/lots/4/bid/` with bidder token and amount `16.00` returned controlled `409` response with `{"status":"rejected","reason":"INVALID_INCREMENT","current_price":"15.00"}`. Anonymous `POST /api/lots/4/bid/` with amount `20.00` returned controlled `401` response with `{"status":"rejected","reason":"UNAUTHENTICATED","current_price":"15.00"}`. |
| Bidding | Failed bid attempts do not corrupt lot state | PASS | Lot id `4` current price was `10.00` before bidding, `15.00` after the valid bid, and stayed `15.00` after both invalid and anonymous rejected attempts. |
| Bidding | Bid history correct | PASS | Public `GET /api/lots/4/bids/` returned one accepted bid id `3`. Seller-authenticated `GET /api/lots/4/bids/` returned rejected bid id `4` (`INVALID_INCREMENT`) plus accepted bid id `3`. The anonymous unauthenticated rejection returned a controlled response and did not create a bidder-linked bid record. |
| Lifecycle | Scheduler closes ended auction | WARN | Render cron/job setup evidence has not been provided. Bid endpoint is now verified; closing/winner calculation still requires scheduler execution evidence. |
| Lifecycle | Winner calculated from accepted bids only | WARN | Not verified; depends on `close_expired_auctions` execution against a lot with accepted bids. |
| Fulfillment | Seller sees fulfillment dashboard | PASS | Seller `GET /api/dashboard/fulfillment/` returned `200 OK` with empty summary/results. End-to-end fulfillment still needs a calculated winner. |
| Fulfillment | Seller updates fulfillment status | WARN | Not verified because no winner/fulfillment record exists yet. |
| Fulfillment | Bidder sees won lots | WARN | Not verified because no winning bid/winner outcome exists yet. |
| Notifications | Notification created | WARN | Not verified because winner/fulfillment flows have not run. |
| Notifications | Unread count updates | PASS | Bidder `GET /api/account/notifications/unread-count/` returned `200 OK` with `unread_count=0`. Mark-read still needs an actual notification. |
| Notifications | Mark as read works | WARN | Not verified because no notification exists yet. |
| Repair | Admin creates repair request | WARN | Blocked: staging admin login failed with `401`. |
| Repair | Different admin approves repair | WARN | Blocked: admin credentials unavailable. |
| Repair | Approved repair applies | WARN | Blocked: admin credentials unavailable and no winning bid exists. |
| Repair | Audit logs created | WARN | Blocked: admin credentials unavailable; audit endpoint not verified. |
| Admin ops | Admin export downloads CSV | WARN | Blocked: staging admin login failed with `401`. |
| Admin ops | Audit logs visible | WARN | Blocked: staging admin login failed with `401`. |
| Admin ops | Release check UI works | WARN | Admin release-check API/UI not verified because no admin token was available. |

## Issues Found

| Severity | Issue | Steps to reproduce | Status |
| --- | --- | --- | --- |
| Critical | Staging bid endpoint returned `500` for authenticated valid bid, authenticated invalid bid, and anonymous bid probe. | Original failure reproduced on lot id `2`. After redeploy commit `cb9ca78`, fresh lot id `4` was tested with valid, invalid, and anonymous bid attempts. | FIXED AND VERIFIED - valid bid now returns `201 accepted`, invalid increment returns controlled `409 INVALID_INCREMENT`, anonymous bid returns controlled `401 UNAUTHENTICATED`, and lot state remains authoritative. |
| Medium | Frontend Browse page treated staging empty auction data as an error state. | Open `https://bidals-1.onrender.com/auctions` while `GET https://bidals.onrender.com/api/auctions/` returns `{"count":0,"next":null,"previous":null,"results":[]}`. | FIXED AND VERIFIED |
| High | Documented staging admin credentials are not available. | `POST /api/auth/login/` with `staging_admin` / `ChangeMe123!` returned `401`. | OPEN - run `seed_staging_data` or create staging admin securely. |
| High | Scheduler, backup restore, and `release_check` still need real Render execution evidence. | Attempt Phase 17 completion without Render shell/job logs and managed PostgreSQL restore proof. | OPEN |
| Medium | Managed backup restore cannot be fully verified on current free Render Postgres setup. | Try to provide provider-managed backup/restore evidence from free staging database. | OPEN/WARN - use supported Render plan/provider restore path or manual non-production `pg_dump` restore rehearsal. |
| Medium | `release_check` and `deployment_check --production` failed in Render shell because the health probe hit `/api/health` and received Django's trailing-slash `301` redirect. | Run `python manage.py release_check` or `python manage.py deployment_check --production` in Render shell before the readiness health-path fix. | FIXED IN CODE / PENDING REDEPLOY - readiness checks now use `/api/health/` explicitly and follow redirects safely without disabling `APPEND_SLASH`. |

## Remaining Phase 17 Manual Checks

- Optional: inspect Render backend logs for previous `POST /api/lots/{id}/bid/` 500s and confirm no new cache/Redis exceptions after commit `cb9ca78`.
- Redeploy the backend with the readiness health-path fix for `release_check` and `deployment_check`.
- Re-run `python manage.py deployment_check --production` in Render shell and confirm the health check is `PASS` for `/api/health/`.
- Re-run `python manage.py release_check` in Render shell and confirm there is no health endpoint `FAIL`; record remaining WARN items only.
- Confirm Redis/cache settings for staging bid throttling: `REDIS_URL`, `USE_REDIS_CACHE`, and Redis service connectivity. If no Redis is provisioned for staging, set `USE_REDIS_CACHE=False` and document that throttling is local-process only.
- Run `python manage.py migrate` on the staging backend and confirm no unapplied migrations.
- Run `python manage.py seed_staging_data` or otherwise create at least one staging admin user for admin-only checks.
- Configure Render scheduled jobs for auction closing, anomaly monitoring, and notification delivery.
- Capture successful scheduler logs and confirm related audit/operations visibility.
- Create or identify a managed PostgreSQL backup, or document the free Render Postgres limitation and run a non-production manual restore rehearsal when possible.
- Restore the backup/dump into staging or a restore-test database.
- Run `python manage.py verify_backup` after recording backup metadata.
- Run `python manage.py release_check` and paste sanitized output above.
- Execute remaining smoke checks: scheduler close/winner calculation, fulfillment update, won-lots page, notification mark-read, repair workflow, admin export, audit visibility, and release-check UI.

## Final Readiness Assessment

Status: NOT READY FOR PRODUCTION FROM PHASE 17 YET

Reason: Initial Render deployment evidence exists and core health/auth/create/browse/bidding flows now pass after redeploy commit `cb9ca78`. `release_check` and `deployment_check` were run in Render shell and failed only because the commands hit `/api/health` and received a `301`; this is fixed in code and needs redeploy/re-run evidence. Admin access is unavailable, scheduler execution has not been proven, managed backup restore is limited by the current free Render Postgres setup, and final `release_check` output after the health-path fix has not been captured yet.
