# BIDALS Staging Environment

Staging is the release rehearsal environment for BIDALS. It should mirror production closely enough to prove operational safety, while staying clearly separated from production data and secrets.

Core rule: staging must use the same backend-owned auction, bid, winner, fulfillment, audit, and repair logic as production. Do not add staging shortcuts that bypass backend validation.

## Required Services

- Backend web service running `DJANGO_SETTINGS_MODULE=bidals.settings.prod`.
- Frontend web service built with `NEXT_PUBLIC_API_BASE_URL` pointed at the staging backend API.
- Managed PostgreSQL database dedicated to staging.
- Redis instance for shared cache, throttling, and scheduler-adjacent checks.
- Cloudflare R2 or S3-compatible object storage for persistent lot images.
- Provider scheduler or cron jobs for `close_expired_auctions`, `monitor_bid_anomalies`, and `deliver_notifications`.

## Staging URLs

Current Render staging pattern:

- Frontend: `https://bidals-frontend-staging.onrender.com`
- Backend API: `https://bidals.onrender.com/api`
- Backend health: `https://bidals.onrender.com/health/`
- Backend readiness: `https://bidals.onrender.com/health/ready/`

Do not record secrets, database URLs, Redis URLs, API tokens, or object storage keys in this document.

## Required Environment Variables

Backend staging baseline:

```text
DJANGO_SETTINGS_MODULE=bidals.settings.prod
BIDALS_ENV=staging
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<staging-secret>
DJANGO_ALLOWED_HOSTS=<backend-staging-host>
FRONTEND_URL=https://<frontend-staging-host>
CORS_ALLOWED_ORIGINS=https://bidals-frontend-staging.onrender.com
CSRF_TRUSTED_ORIGINS=https://bidals-frontend-staging.onrender.com
DATABASE_URL=<staging-postgres-url>
USE_REDIS_CACHE=True
REDIS_URL=<staging-redis-url>
USE_S3=True
AWS_ACCESS_KEY_ID=<staging-storage-key>
AWS_SECRET_ACCESS_KEY=<staging-storage-secret>
AWS_STORAGE_BUCKET_NAME=<staging-bucket>
AWS_S3_REGION_NAME=auto
AWS_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
SCHEDULED_JOBS_CONFIGURED=True
ENABLE_RATE_LIMITING=True
```

Frontend staging baseline:

```text
NEXT_PUBLIC_API_BASE_URL=https://bidals.onrender.com/api
NEXT_TELEMETRY_DISABLED=1
```

The backend also accepts the older `DJANGO_CORS_ALLOWED_ORIGINS` and `DJANGO_CSRF_TRUSTED_ORIGINS` names. If both forms are set, values are merged and de-duplicated.

On Render, configure `NEXT_PUBLIC_API_BASE_URL` as both the frontend service environment variable and Docker build argument so Next.js bakes the public backend API URL into client-side bundles. Do not use `http://localhost:8000/api` outside local development.

## Security Expectations

- HTTPS is required for backend and frontend.
- `DEBUG` must be false.
- `ALLOWED_HOSTS` must contain staging backend hosts only.
- CORS origins must contain the staging frontend origin only.
- CSRF trusted origins must contain the staging frontend origin.
- Secure cookies are enabled by production settings.
- Staging must not share production PostgreSQL, Redis, R2 buckets, or credentials.
- `seed_staging_data` and `create_staging_admin` are allowed only in staging or explicit non-production environments.

## How Staging Differs From Production

- Staging may contain fake users and records labelled for testing.
- Staging can use lower-scale infrastructure.
- Staging may use shorter HSTS values while HTTPS is being validated.
- Staging may send email to console or disabled delivery unless a staging provider is intentionally configured.
- Production must have provider-backed backup and restore evidence before launch.

## Staging Smoke Tests

Before every production release, run:

```bash
python manage.py deployment_check --production
python manage.py release_check
python manage.py backup_verify
```

Then run the deployed release candidate smoke suite from the frontend workspace:

```bash
npm run smoke:release-candidate
```

See [release-candidate-smoke.md](release-candidate-smoke.md) for environment variables and expected PASS/WARN/FAIL output.

## Staging Checklist

- Login works for admin, seller, and bidder.
- Logout works.
- Token refresh works.
- Admin access works.
- Seller access works.
- Bidder access works.
- Auction creation works.
- Lot creation works.
- Image upload works and persists after redeploy.
- Bid placement works for a valid bid.
- Invalid bids return controlled backend rejection.
- Rejected bids are audited.
- Rate limiting returns clear 429 responses without corrupting bid state.
- Audit logs are visible to admins.
- Scheduled jobs run through `/app/scripts/run_scheduled_job.sh`.
- Winner calculation uses accepted backend bid records only.
- Fulfillment dashboard is visible to seller/admin users.
- Notifications unread count works.
- Admin export works.
- Outcome repair access is admin-only.
