# BIDALS Rollback Runbook

Use this runbook when a release must be reverted. Rollback must preserve backend-owned auction truth, audit history, and repair governance.

## First Principles

- Do not edit accepted bids.
- Do not manually change winner state outside backend jobs or the admin repair workflow.
- Do not delete audit logs to hide a failed deploy.
- Do not restore a database over production without validating the restore in isolation.
- Prefer code rollback first when data is intact.

## Fast Code Rollback

Use when:

- The latest app release is broken.
- Database schema remains compatible with the previous release.
- No destructive migration needs to be reversed.

Steps:

1. Pause further deploys.
2. Identify the previous known-good GitHub commit/image.
3. Capture current health, logs, request IDs, and audit/export evidence.
4. Trigger a rollback deploy in Render or redeploy the previous commit/image.
5. Run:

```bash
python manage.py deployment_check --production
python manage.py verify_backup
python manage.py release_check
```

6. Run post-deploy smoke:
   - health
   - login
   - browse
   - valid bid
   - invalid bid
   - audit log visibility
   - admin export
7. Confirm scheduled jobs still run through `/app/scripts/run_scheduled_job.sh`.
8. Record the rollback reason and outcome.

## Migration-Aware Rollback

Use extra care when the failed release included migrations.

1. Take or verify a fresh provider backup before rollback.
2. Inspect migration direction and data impact.
3. Prefer forward-fix migrations over reversing after real bids or fulfillment updates.
4. If schema rollback is unavoidable, restore to staging first and validate.
5. Never reverse migrations that would delete accepted bids, audit logs, winner outcomes, fulfillment records, notifications, or repair workflow history without explicit operator approval and a legal/business decision.

## Database Recovery Rollback

Use only for data loss/corruption events.

1. Freeze deploys and admin repair actions.
2. Identify recovery target time.
3. Use Render PITR or logical backup to create a new recovery database.
4. Point staging at the recovery database.
5. Follow [disaster-recovery.md](disaster-recovery.md) post-restore validation.
6. Run the release candidate smoke suite against the restored environment.
7. Promote the restored database only after validation and approval.
8. Keep the old production database available until the incident review is complete when possible.

## Rollback Checklist

- Previous commit/image identified.
- Provider backup status confirmed.
- Migration risk reviewed.
- Backend health checked after rollback.
- Frontend health checked after rollback.
- Redis check passed.
- R2/object storage check passed.
- Scheduled jobs checked.
- Valid and invalid bid smoke passed.
- Audit logs readable.
- Admin export works.
- Fulfillment and won-lots still readable.
- Notification unread count works.
- Repair workflow access works.
- Incident notes updated.

## After Rollback

- Open a follow-up issue for the failed release.
- Preserve logs and smoke output.
- Re-run staging RC smoke before attempting release again.
- Review whether deployment checks should catch the failure next time.
