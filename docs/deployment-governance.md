# BIDALS Deployment Governance

This document defines the minimum release governance for BIDALS. It exists to protect backend-owned auction truth, audit history, and operational accountability.

## Release Rules

- All production changes go through a pull request.
- CI must pass before merge.
- Deploy production from `main` or an approved release tag only.
- Review migrations before deploy, especially data migrations or schema changes touching auctions, lots, bids, outcomes, fulfillment, notifications, or audit logs.
- Confirm provider backups before risky migrations.
- Know the rollback target before deployment starts.
- Run staging smoke checks before production.
- Run production smoke checks after deploy.
- Record incident notes if any step fails or is manually bypassed.

## Pre-Merge Requirements

- Backend tests pass.
- Frontend typecheck/lint/build pass when frontend changes are included.
- Docker backend and frontend images build.
- Security secret scan runs.
- Dependency audit warnings are reviewed.
- Migrations are committed and reviewed.
- Bidding tests pass if auction, lot, bid, winner, fulfillment, or permissions code changed.

## Pre-Deploy Requirements

Run in staging first:

```bash
python manage.py deployment_check --production
python manage.py release_check
python manage.py backup_verify
```

Confirm:

- No `FAIL` items remain.
- Manual `WARN` items are understood and accepted.
- Release candidate smoke suite reports `FAIL=0`.
- Render cron jobs last ran successfully.
- Redis check passes.
- R2/S3 image upload persistence has been tested.

## Production Environment Review

Check these values in the provider secret manager, not in code:

- `DJANGO_SETTINGS_MODULE=bidals.settings.prod`
- `BIDALS_ENV=production`
- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY` is strong and non-placeholder.
- `DJANGO_ALLOWED_HOSTS` contains production backend hosts only.
- `DJANGO_CORS_ALLOWED_ORIGINS` contains production frontend origins only.
- `DJANGO_CSRF_TRUSTED_ORIGINS` contains trusted production origins.
- `DATABASE_URL` points to production PostgreSQL.
- `USE_REDIS_CACHE=True` and `REDIS_URL` points to production Redis.
- `USE_S3=True` and storage values point to production media storage.
- `SCHEDULED_JOBS_CONFIGURED=True` after production cron jobs are configured.
- `BACKUP_LAST_VERIFIED_AT` and `BACKUP_LAST_RESTORE_TEST_AT` are current.

## Deployment Sequence

1. Confirm backup status and rollback target.
2. Deploy backend from the approved commit.
3. Run migrations.
4. Run `deployment_check --production`.
5. Confirm `/health/` and `/health/ready/`.
6. Deploy frontend from the approved commit.
7. Confirm frontend health.
8. Confirm scheduler jobs still run with production settings.
9. Run post-deploy smoke checks.
10. Review logs, audit records, and admin operations dashboard.

## Incident Notes

If anything fails, record:

- Timestamp.
- Commit/image.
- Operator.
- Failed check.
- Request ID or job log excerpt.
- User-visible impact.
- Rollback or forward-fix decision.
- Follow-up owner.

Do not delete audit logs or alter historical bids to hide a bad release.
