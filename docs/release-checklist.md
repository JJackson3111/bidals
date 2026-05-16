# BIDALS Release Checklist

Use this checklist for every staging-to-production release.

## Approval

- GitHub PR approved.
- Release owner assigned.
- Rollback owner assigned.
- Rollback commit/image identified.
- Incident notes location ready.

## CI And Build

- Backend tests passed.
- Frontend checks passed when frontend changed.
- Docker backend build passed.
- Docker frontend build passed.
- Security checks passed or warnings accepted.
- Dependency audit warnings reviewed.
- `git diff --check` clean.

## Database And Migrations

- Migrations reviewed.
- No unexpected destructive migration.
- Production backup confirmed.
- Restore test timestamp current.
- `python manage.py migrate` plan understood.

## Environment

- Production env vars reviewed.
- No staging URLs in production frontend env.
- No production secrets in staging.
- `DJANGO_ALLOWED_HOSTS` is not wildcarded.
- CORS origins are not wildcarded.
- CSRF trusted origins are configured.
- Redis is enabled for production throttling.
- Object storage is enabled for production media.

## Staging Gate

- `python manage.py deployment_check --production` passed.
- `python manage.py release_check` reviewed.
- `python manage.py backup_verify` reviewed.
- Release candidate smoke suite completed with `FAIL=0`.
- Scheduled jobs passed in staging.
- Admin export tested.
- Audit logs checked.

## Production Deploy

- Backend deployed from approved commit.
- Migrations run.
- `/health/` returns ok.
- `/health/ready/` returns ok.
- Frontend deployed from approved commit.
- Cron jobs verified after deploy.

## Production Smoke

- Admin login.
- Seller login.
- Bidder login.
- Auction creation.
- Lot creation.
- Lot image upload.
- Browse auction and lot.
- Valid bid accepted by backend.
- Invalid bid rejected by backend.
- Bid history correct.
- Audit log created.
- Admin export downloads CSV.
- Operations dashboard loads.
- Notification unread count works.
- Repair workflow access is admin-only.

## Monitoring

- Provider health checks green.
- Logs show request IDs.
- No unexpected 5xx spike.
- No login abuse spike.
- No bid anomaly spike.
- Sentry or equivalent error tracking checked if configured.

## Decision

Release is ready only when critical checks pass and any `WARN` items have a named owner and acceptance note.
