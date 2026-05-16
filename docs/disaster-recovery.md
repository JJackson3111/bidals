# BIDALS Disaster Recovery Runbook

This runbook is the Phase 18 production-readiness path for backup, restore, and disaster recovery. It is intentionally non-destructive by default. Restore rehearsals must happen against staging or a dedicated restore-test database before any production promotion.

Core safety rules:

- Do not change bidding logic during recovery.
- Do not edit historical accepted bids.
- Do not manually calculate winners outside backend jobs/services.
- Preserve audit logs, request IDs, provider logs, and recovery timestamps.
- Restore into an isolated database first, validate it, then decide whether to promote it.

## Recovery Objectives

Recommended MVP targets:

- RPO: 24 hours until provider PITR is enabled; tighter once paid PostgreSQL PITR is available.
- RTO: 4 hours for operator-led recovery, including restore validation.
- Restore test cadence: before production launch, after major schema changes, and at least monthly.

## Render PostgreSQL Reality

Render free PostgreSQL is not production-ready for BIDALS because it does not provide managed backups, has a 1 GB limit, and expires after 30 days. Render's free-service docs state that Free Render Postgres databases do not support backups.

Production recommendation:

- Upgrade Render PostgreSQL to a paid instance before running real auctions.
- Use Render point-in-time recovery for database disaster recovery.
- Keep logical exports for longer-term retention when available.
- Continue using `pg_dump` as an operator-controlled export path for rehearsals and extra retention.

Render paid backup behavior to account for:

- Paid Render Postgres supports point-in-time recovery.
- Hobby workspaces have a shorter recovery window than Pro or higher.
- PITR creates a new recovery database instance so it can be validated before services are repointed.
- Logical exports can be created from the Render dashboard on supported plans.

References:

- [Render Postgres backups and recovery](https://render.com/docs/postgresql-backups)
- [Render free instance limitations](https://render.com/docs/free)

## Backup Procedure

Preferred production path:

1. Confirm provider-managed PostgreSQL backups are enabled.
2. Confirm the latest backup/recovery timestamp in the provider dashboard.
3. Record the timestamp in `BACKUP_LAST_VERIFIED_AT` only after an operator has confirmed it.
4. Periodically trigger a restore into staging or a restore-test database.
5. Record the successful restore timestamp in `BACKUP_LAST_RESTORE_TEST_AT`.

Manual `pg_dump` path for non-production rehearsals or extra retention, run from the repository root on an operator machine or CI runner that has PostgreSQL client tools installed:

```bash
DATABASE_URL='<postgres-url>' \
BIDALS_ENV=staging \
BACKUP_OUTPUT_DIR=backups \
sh scripts/pg_dump_backup.sh
```

The helper:

- Uses custom-format `pg_dump`.
- Does not print the database URL.
- Writes to `backups/`, which is ignored by git.
- Prints a checksum when a checksum tool is available.

Do not store production dumps in the application repo, Render container filesystem, or chat transcripts. Store them in a controlled backup location with access logging.

## Restore Rehearsal Procedure

Use a dedicated restore-test database. Never restore over the active production database. Run the helper from the repository root on an operator machine or CI runner that has PostgreSQL client tools installed.

1. Create a new Render PostgreSQL database for restore testing, or use the database produced by Render PITR.
2. Capture the target database URL as `RESTORE_DATABASE_URL`.
3. Restore the dump into the restore-test database:

```bash
BACKUP_FILE=backups/bidals-staging-YYYYMMDDTHHMMSSZ.dump \
RESTORE_DATABASE_URL='<restore-test-postgres-url>' \
RESTORE_TARGET_ENV=restore-test \
RESTORE_TARGET_CONFIRM=non-production-restore-ok \
sh scripts/restore_to_test_db.sh
```

The helper refuses to run unless:

- `BACKUP_FILE` exists.
- `RESTORE_DATABASE_URL` is set.
- `RESTORE_DATABASE_URL` differs from `DATABASE_URL` or `DJANGO_DATABASE_URL`.
- `RESTORE_TARGET_ENV` is not production.
- `RESTORE_TARGET_CONFIRM=non-production-restore-ok`.

## Post-Restore Validation

Run validation against an app instance or shell configured to use the restored database.

```bash
DJANGO_SETTINGS_MODULE=bidals.settings.prod \
DATABASE_URL='<restore-test-postgres-url>' \
API_BASE_URL=https://<restore-test-backend>/api \
sh scripts/post_restore_validate.sh
```

The helper runs:

- `python manage.py migrate --check`
- `python manage.py check`
- `python manage.py backup_verify`
- `python manage.py release_check`
- Optional health probe when `API_BASE_URL` is set.
- Optional release candidate smoke when `RUN_RC_SMOKE=true`.

For full validation, also run:

```bash
cd frontend
RC_SMOKE_API_BASE_URL=https://<restore-test-backend>/api \
RC_SMOKE_FRONTEND_URL=https://<restore-test-frontend> \
RC_SMOKE_SELLER_USERNAME=<seller> \
RC_SMOKE_SELLER_PASSWORD=<seller-password> \
RC_SMOKE_BIDDER_USERNAME=<bidder> \
RC_SMOKE_BIDDER_PASSWORD=<bidder-password> \
RC_SMOKE_ADMIN_USERNAME=<admin> \
RC_SMOKE_ADMIN_PASSWORD=<admin-password> \
npm run smoke:release-candidate
```

Post-restore acceptance checks:

- Migrations are applied.
- `/api/health/` returns ok.
- Admin login works.
- Users, auctions, lots, bids, audit logs, fulfillment records, notifications, and outcome repairs are visible to authorized users.
- Lot `current_price` matches accepted bid history.
- Rejected bid history and audit logs survived restore.
- Valid bids are still accepted by the backend only.
- Invalid bids are rejected by the backend only.
- `close_expired_auctions` remains idempotent.
- Fulfillment and won-lots views reflect backend-owned outcome state.
- Object storage image URLs still load.
- Admin CSV export works.

Only after these checks pass should an operator set:

```bash
BACKUP_LAST_VERIFIED_AT=<latest-provider-backup-iso8601>
BACKUP_LAST_RESTORE_TEST_AT=<restore-test-pass-iso8601>
```

## Disaster Recovery Checklist

1. Declare the incident and freeze deploys.
2. Preserve logs, request IDs, audit records, and provider event timelines.
3. Identify the recovery target time.
4. Prefer Render PITR on a paid database. If unavailable, use the latest logical export or `pg_dump`.
5. Restore into a new database, not the active production database.
6. Point a staging/restore-test backend at the restored database.
7. Run post-restore validation.
8. Run the release candidate smoke suite against the restored environment.
9. Compare critical counts with the last known good production snapshot where possible:
   - users
   - auctions
   - lots
   - accepted bids
   - rejected bids
   - audit logs
   - fulfillment records
   - outbound notifications
10. If validation passes, schedule promotion with a rollback window.
11. Repoint production services through provider env groups or service settings.
12. Run `deployment_check --production`, `verify_backup`, and `release_check`.
13. Run the post-deploy smoke checklist.
14. Record the recovery decision, timestamps, and validation evidence in the incident notes.

## Outage Guides

### Scheduler Outage

- Confirm Render cron jobs use `sh /app/scripts/run_scheduled_job.sh ...`.
- Check for `settings_module=bidals.settings.prod` and `database_engine=django.db.backends.postgresql`.
- Manually run:

```bash
sh /app/scripts/run_scheduled_job.sh close_expired_auctions
sh /app/scripts/run_scheduled_job.sh monitor_bid_anomalies --window-minutes 60
sh /app/scripts/run_scheduled_job.sh deliver_notifications
```

- Review `/dashboard/operations` and audit logs.
- Do not manually set winners unless using the admin outcome repair workflow.

### Redis Outage

- `deployment_check --production` must fail if `USE_REDIS_CACHE=True` and Redis is unreachable.
- Bidding validation still belongs to the database transaction; Redis is only throttling/cache infrastructure.
- If Redis is down, pause high-traffic auctions if operationally necessary, restore Redis, and rerun deployment checks.
- Do not disable throttling in production without an incident note and follow-up task.

### Object Storage Outage

- Bidding and winner calculation do not depend on media storage.
- Uploads may fail while R2/S3 is unavailable.
- Keep existing lot image URLs and metadata intact.
- Confirm `USE_S3=True` and storage credentials in provider secrets.
- After recovery, upload a test lot image in staging and verify it survives redeploy/restart.

### Database Outage

- Treat as high severity.
- Avoid admin outcome repairs until database health is restored.
- Use provider dashboard and Render status to confirm scope.
- If data loss is suspected, restore to staging first and follow this runbook.

## Secrets Separation

- Use different Render services/databases for staging and production.
- Use different Render environment groups for staging and production.
- Use different R2 buckets or prefixes for staging and production.
- Use different Redis instances for staging and production.
- Do not copy staging seed passwords into production.
- Do not run `seed_staging_data` in production.
- Do not paste database URLs, Redis URLs, R2 keys, or JWTs into docs.
