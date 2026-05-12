# BIDALS Release Candidate Smoke Suite

This smoke suite is the repeatable release gate for BIDALS staging before a production cutover.

It validates backend-owned auction lifecycle behavior against deployed staging URLs. It does not move bid validation, winner calculation, fulfillment state, or repair decisions to the frontend. The API and scheduled jobs remain authoritative.

## Command

Run from the repository root:

```bash
cd frontend
npm run smoke:release-candidate
```

The script is API-level and uses the deployed backend API for lifecycle checks. It also checks the deployed frontend health endpoint through `RC_SMOKE_FRONTEND_URL`.

## Required Environment Variables

Do not commit these values. Set them in your shell, CI secret store, or local secure environment.

```bash
RC_SMOKE_API_BASE_URL=https://bidals.onrender.com/api
RC_SMOKE_FRONTEND_URL=https://bidals-1.onrender.com

RC_SMOKE_SELLER_USERNAME=<staging seller username>
RC_SMOKE_SELLER_PASSWORD=<staging seller password>

RC_SMOKE_BIDDER_USERNAME=<staging bidder username>
RC_SMOKE_BIDDER_PASSWORD=<staging bidder password>

RC_SMOKE_ADMIN_USERNAME=<staging admin username>
RC_SMOKE_ADMIN_PASSWORD=<staging admin password>
```

For full two-admin repair workflow validation:

```bash
RC_SMOKE_ADMIN2_USERNAME=<second staging admin username>
RC_SMOKE_ADMIN2_PASSWORD=<second staging admin password>
```

## Optional Environment Variables

```bash
RC_SMOKE_UPLOAD_IMAGE=true
RC_SMOKE_IMAGE_PATH=/absolute/path/to/test-image.png
RC_SMOKE_AUCTION_END_OFFSET_SECONDS=75
RC_SMOKE_CLOSE_WAIT_SECONDS=210
RC_SMOKE_POLL_SECONDS=10
RC_SMOKE_REPAIR_MODE=auto
RC_SMOKE_FAIL_ON_WARN=false
RC_SMOKE_SKIP_CLOSE_WAIT=false
```

Notes:

- `RC_SMOKE_UPLOAD_IMAGE=true` uploads a generated 1x1 PNG when `RC_SMOKE_IMAGE_PATH` is not set.
- `RC_SMOKE_REPAIR_MODE=auto` runs full repair create/comment/approve/apply only when a second admin is configured.
- `RC_SMOKE_REPAIR_MODE=access` checks repair access only.
- `RC_SMOKE_REPAIR_MODE=full` expects second-admin credentials and reports WARN if full repair cannot run.
- `RC_SMOKE_FAIL_ON_WARN=true` is useful for a strict release-candidate gate.

## Automated Checks

The suite produces a clear `PASS`, `WARN`, and `FAIL` report.

Automated:

- Frontend health when `RC_SMOKE_FRONTEND_URL` is configured.
- Seller login.
- Bidder login.
- Admin login.
- Optional second admin login.
- Create live auction with server-side API.
- Create lot.
- Upload lot image through multipart `FormData`.
- Public browse visibility for created auction and lot.
- Place valid bid and confirm backend accepted response.
- Place invalid bid and confirm controlled backend rejection.
- Confirm bid history includes accepted and seller-visible rejected bid records.
- Confirm admin-visible audit logs for accepted/rejected bids.
- Download admin activity CSV export.
- Wait for Render cron-backed auction close and winner calculation.
- Confirm winner uses the accepted backend bid created by this smoke run.
- Confirm fulfillment record exists and can transition through backend rules.
- Confirm bidder won-lots reflects backend-owned fulfillment state.
- Confirm notification exists, unread state is visible, and mark-read works.
- Confirm repair workflow access.
- Full repair create/comment/approve/apply when second-admin credentials are configured.

## Manual Or WARN Checks

Some checks remain WARN unless the staging environment is configured for them:

- Auction close/winner calculation becomes WARN if Render cron does not close the auction before `RC_SMOKE_CLOSE_WAIT_SECONDS`.
- Full two-admin repair workflow is WARN unless `RC_SMOKE_ADMIN2_USERNAME` and `RC_SMOKE_ADMIN2_PASSWORD` are provided.
- Image upload is WARN only when explicitly disabled with `RC_SMOKE_UPLOAD_IMAGE=false`; otherwise upload failure is a FAIL.
- Backup/restore verification is not performed by this script. Use `python manage.py verify_backup` and the provider restore runbook.

## Expected Staging Behavior

For a healthy staging release candidate:

- Core auth, auction, lot, bid, audit, and export checks should PASS.
- Scheduler-backed lifecycle should PASS once Render cron jobs are configured.
- Fulfillment, won-lots, notification unread, and mark-read should PASS after winner calculation.
- Repair access should PASS.
- Full repair workflow should PASS when two admin accounts are configured.
- Remaining WARN items should be documented before production approval.

## Safety

The suite creates uniquely named staging records prefixed with `[RC SMOKE]`.

It never:

- Bypasses the bidding service.
- Calculates winners in the script.
- Writes fulfillment state except through the backend fulfillment API.
- Changes historical bid records.
- Uses frontend state as authority.
- Prints secret values.

## Troubleshooting

If the lifecycle check times out:

1. Confirm Render cron jobs are enabled.
2. Confirm cron logs show `settings_module=bidals.settings.prod`.
3. Confirm cron logs show `database_engine=django.db.backends.postgresql`.
4. Confirm the auction end time has passed.
5. Check `/dashboard/operations` for close runs, winner calculations, and job failures.

If image upload fails:

1. Confirm `USE_S3=True` and Cloudflare R2/S3-compatible env vars are configured in the backend.
2. Confirm the seller owns the auction/lot.
3. Confirm the API response names a storage or validation issue.

If repair workflow is WARN:

1. Create or configure a second staging admin.
2. Set `RC_SMOKE_ADMIN2_USERNAME` and `RC_SMOKE_ADMIN2_PASSWORD`.
3. Re-run with `RC_SMOKE_REPAIR_MODE=full` if you want the warning to become release-blocking.
