# BIDALS Phase 17 Staging Rehearsal

Provider selected: Render

Status: BLOCKED - provider access and staging URLs are required before the real cloud rehearsal can be completed.

This document is the Phase 17 execution record. Fill in the evidence sections during the live Render staging rehearsal. Do not record secrets, tokens, database passwords, or private keys here.

## Required Inputs

- GitHub repository URL:
- Render workspace/team:
- Backend staging URL:
- Frontend staging URL:
- Managed PostgreSQL service name:
- Managed Redis service name:
- Backup source:
- Restore target:
- Operator:
- Rehearsal date:

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
3. Create the backend web service from the GitHub repository.
4. Set backend root/directory to `backend` if using Render's repository directory setting.
5. Use `backend/Dockerfile`.
6. Set health check path to `/api/health/`.
7. Set pre-deploy/release command to:

```bash
python manage.py migrate
```

8. Create the frontend web service from the same GitHub repository.
9. Use `frontend/Dockerfile.prod`.
10. Set the frontend build arg/env value:

```bash
NEXT_PUBLIC_API_BASE_URL=https://<backend-staging-host>/api
```

11. Set frontend health check path to `/api/health`.
12. Confirm both services deploy from GitHub and report healthy.

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
- `REDIS_URL=<Render Redis URL>`
- `USE_REDIS_CACHE=True`
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
| Auction closing and winner calculation | `python manage.py close_expired_auctions` | Every 1 minute, or the shortest Render-supported interval | NOT RUN |
| Bid anomaly monitoring | `python manage.py monitor_bid_anomalies --window-minutes 60` | Every 5 minutes | NOT RUN |
| Notification delivery | `python manage.py deliver_notifications` | Every 5 minutes if email enabled | NOT RUN |

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
| Users exist | Admin, seller, bidder users present | NOT RUN |
| Auctions exist | Live/scheduled/ended auctions present | NOT RUN |
| Lots exist | Lots linked to auctions | NOT RUN |
| Bids exist | Accepted and rejected bids present | NOT RUN |
| Audit logs exist | Audit events readable | NOT RUN |

Restore evidence:

- Backup timestamp:
- Restore target:
- Restore command/provider action:
- `BACKUP_LAST_VERIFIED_AT`:
- `BACKUP_LAST_RESTORE_TEST_AT`:

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
NOT RUN - provider access and staging URLs required.
```

## Post-Deploy Smoke Checklist

| Area | Check | Result | Evidence / notes |
| --- | --- | --- | --- |
| Health | Backend `/api/health/` returns ok | NOT RUN |  |
| Health | Frontend `/api/health` returns ok | NOT RUN |  |
| Auth | Login works | NOT RUN |  |
| Auth | Register works | NOT RUN |  |
| Core | Create auction | NOT RUN |  |
| Core | Create lot | NOT RUN |  |
| Core | View auction feed | NOT RUN |  |
| Core | View lot detail | NOT RUN |  |
| Bidding | Valid bid accepted by backend | NOT RUN |  |
| Bidding | Invalid bid rejected by backend | NOT RUN |  |
| Lifecycle | Scheduler closes ended auction | NOT RUN |  |
| Lifecycle | Winner calculated from accepted bids only | NOT RUN |  |
| Fulfillment | Seller sees fulfillment dashboard | NOT RUN |  |
| Fulfillment | Seller updates fulfillment status | NOT RUN |  |
| Fulfillment | Bidder sees won lots | NOT RUN |  |
| Notifications | Notification created | NOT RUN |  |
| Notifications | Unread count updates | NOT RUN |  |
| Notifications | Mark as read works | NOT RUN |  |
| Repair | Admin creates repair request | NOT RUN |  |
| Repair | Different admin approves repair | NOT RUN |  |
| Repair | Approved repair applies | NOT RUN |  |
| Repair | Audit logs created | NOT RUN |  |
| Admin ops | Admin export downloads CSV | NOT RUN |  |
| Admin ops | Audit logs visible | NOT RUN |  |
| Admin ops | Release check UI works | NOT RUN |  |

## Issues Found

| Severity | Issue | Steps to reproduce | Status |
| --- | --- | --- | --- |
| High | Real cloud rehearsal cannot be completed from this session without Render access, staging URLs, and configured secrets. | Attempt provider deployment/backup restore from local workspace. Provider CLI and credentials are unavailable. | BLOCKED |

## Final Readiness Assessment

Status: NOT READY FOR PRODUCTION FROM PHASE 17 YET

Reason: Phase 17 requires evidence from a real cloud staging deployment, scheduler execution, managed PostgreSQL backup restore, staging `release_check`, and live smoke tests. This repository is prepared for that rehearsal, but the external provider run has not been executed in this session.
