# BIDALS

BIDALS is a secure, cloud-ready digital auction platform. The backend is designed to be server-authoritative from day one: bids, permissions, auction timing, reserve state, lot state, and winner decisions belong to the API, not the frontend.

## Architecture

- `backend`: Django, Django REST Framework, PostgreSQL, JWT auth, audit logging, and a transactional bidding service.
- `frontend`: Next.js mobile-first application connected to the Django API.
- `docker-compose.yml`: Local PostgreSQL, Redis, and Django API.
- `.github/workflows`: CI/CD scaffolding for GitHub-based deployment.

## Phase 2 Features

- Auction CRUD API with seller/admin creation and owner/admin edits.
- Lot CRUD API with seller/admin creation and owner/admin edits.
- Strict server-authoritative bidding service in `apps/auctions/services/bidding.py`.
- `select_for_update()` row locking on lots during bid validation.
- Accepted and rejected bid records for authenticated bidders.
- Audit logs for auction creation/update, lot creation/update, bid accepted, and bid rejected.
- Backend bidding tests, including concurrent bidding.

## Phase 3 Features

- Mobile-first Next.js frontend.
- Landing, login, register, auction feed, auction detail, lot detail, seller dashboard, create auction, create lot, and audit pages.
- Typed API client in `frontend/src/lib/api.ts`.
- JWT auth storage for browser sessions.
- Live bidding UI that only renders the backend bid decision.
- Lot detail polling and refresh after bid attempts.

## Phase 4 Features

- Production-ready backend Docker image with Gunicorn, collectstatic, and non-root runtime user.
- Production frontend Docker image using Next.js standalone output.
- Expanded GitHub Actions for backend tests, frontend checks, and Docker builds.
- Hardened production settings driven by environment variables.
- Cloud deployment guidance for Render, Railway, and Fly.io.

## Phase 5 Features

- Polished mobile-first dashboard, audit, lot detail, and bid feedback screens.
- Seller dashboard metrics for auctions, lots, bids, and recent activity.
- Admin-only audit log view with action and entity filters.
- `seed_demo` command for realistic demo users, auctions, lots, bids, and audit activity.
- First-pass bid endpoint rate limiting around `POST /api/lots/{id}/bid/`.
- Backend logging for accepted, rejected, and rate-limited bid attempts.

## Phase 6 Features

- Seller/admin edit screens for auctions and lots.
- Dashboard edit links plus lot management shortcuts.
- Redis-backed Django cache configuration for production bid throttling.
- `LotImage` upload foundation with local media support and object-storage-ready settings.
- Lot cards and lot detail pages display uploaded or external image URLs.
- Playwright smoke suite for login, create/edit auction, create/edit lot, bidding feedback, and audit review.

## Phase 7 Features

- Seller/admin lot image delete and reorder controls.
- Audited backend endpoints for image deletion and ordering.
- Richer seller dashboard filters for auction status, lot status, title search, dates, and sorting.
- Richer admin audit filters for action, actor, entity, bid status, date range, and metadata text.
- CI-ready Playwright smoke workflow in GitHub Actions.
- Cloudflare R2-focused validation for S3-compatible media storage settings.

## Phase 8 Features

- Structured API request logging with request IDs, status codes, duration, and safe user identifiers.
- Structured bid operation logs for accepted, rejected, and rate-limited bid attempts.
- Environment-ready Sentry integration that is enabled only when `SENTRY_DSN` is configured.
- Admin-only operations endpoint and dashboard page for bid, audit, error, and repeated-failure signals.
- Backup, restore, and incident-response runbooks for production operations.

## Phase 9 Features

- Idempotent `close_expired_auctions` management command for server-time auction ending.
- Server-side winner calculation from accepted bids only, with no-bid and reserve-not-met outcomes.
- Persisted lot winner fields for winner status, winning bid, winner user, and calculation timestamp.
- Lightweight bid anomaly detection with configurable rejected-bid and rate-limit thresholds.
- Environment-ready alert webhook hook plus notification event placeholders for future delivery.
- Admin operations dashboard signals for close runs, winner calculations, anomalies, alert hooks, and job failures.

## Phase 10 Features

- Production scheduler guidance for Render, Railway, and Fly.io worker/cron-style jobs.
- Seller/admin winner review UX at `/dashboard/winners` and `/dashboard/auctions/{id}/results`.
- Permission-safe winner review API backed by persisted backend winner state.
- Email-ready outbound notification records with pending, sent, skipped, and failed statuses.
- `deliver_notifications` management command for optional email delivery through Django email backends.
- Operations dashboard visibility for outbound notification status and failed delivery attempts.

## Phase 11 Features

- Lightweight fulfillment records for lots with assigned winners.
- Seller/admin fulfillment workflow at `/dashboard/fulfillment`.
- Winner confirmation, seller notes, admin notes, and winner-visible follow-up messages.
- Read-only bidder won-lots page at `/account/won-lots`.
- Permission-safe fulfillment APIs with private seller/admin notes excluded from bidder responses.
- Audit logs for fulfillment creation, status changes, note updates, completion, cancellation, and disputes.

## Phase 12 Features

- `backfill_winner_outcomes` repair command for legacy ended lots missing backend-owned winner outcomes or fulfillment records.
- Safe dry-run support plus auction/lot scoping for repair runs.
- Explicit fulfillment transition rules enforced by the backend service.
- Audit logs for backfilled winner outcomes and rejected fulfillment transitions.
- Bidder-visible account notifications at `/account/notifications`.
- Fulfillment status notifications for winner confirmed, seller contacted, awaiting handoff, completed, cancelled, and disputed.

## Phase 13 Features

- Fulfillment history/timeline endpoints backed by audit logs.
- Seller/admin timeline visibility for owned fulfillment records, plus bidder-safe won-lot timelines.
- Notification read/unread state with mark-one and mark-all-read account endpoints.
- Admin-only reviewed outcome repair workflow for exceptional finalized corrections.
- Repair request, approve, reject, and apply steps with audit logs for each step.
- Outcome repairs update backend-owned outcome and fulfillment records without altering historical bid records.

## Phase 14 Features

- Outcome repairs now require two distinct admins: the requester cannot approve their own repair.
- Approval notes are stored on repair requests and returned to the admin repair UI.
- Admin-only repair comments provide an audit-safe discussion thread for each repair request.
- Notification unread count endpoint powers the global mobile navigation Alerts badge.
- Notification UI highlights unread items and refreshes the global count after mark-read actions.

## Phase 15 Features

- Admin-only CSV activity export for operational review from the operations dashboard.
- Safe metadata redaction for exported audit metadata and repair audit timelines.
- Admin-only repair audit detail endpoint and UI timeline for request, comment, approval, apply, and fulfillment events.
- Centralized admin permission helper plus frontend use of the backend-owned `is_platform_admin` flag.
- `deployment_check` management command for staging/production rollout gates.
- Staging, production, post-deploy smoke, and rollback checklists.

## Phase 16 Features

- `seed_staging_data` command for explicit non-production staging data with fake users, auctions, lots, bids, fulfillment, and notifications.
- Production guardrails prevent staging seeds from running in `BIDALS_ENV=production` unless an operator deliberately passes `--force`.
- `verify_backup` command for non-destructive backup-readiness checks.
- `release_check` command plus admin-only `/dashboard/admin/release-check` UI for release readiness reporting.
- Release checks cover system hardening, migrations, backup verification, manual core-flow gates, scheduled jobs, audit logs, notifications, and repair workflow access.
- Runbook documentation now separates startup, daily operations, incident response, recovery, backup verification, and release review.

## Phase 17 Staging Rehearsal

Phase 17 is a real cloud validation phase, not a feature phase. The selected staging provider is Render. The execution record lives in [`docs/staging-rehearsal-render.md`](docs/staging-rehearsal-render.md).

Current rehearsal status: staging core is operationally healthy on Render. Backend/frontend health, auth, auction/lot creation, browsing, bidding, Redis-backed throttling, S3/R2 object storage, admin access, scheduled jobs, and the release candidate smoke suite have live evidence. Production go/no-go still depends on backup/restore proof and disaster recovery validation.

Phase 17 evidence must include:

- Backend and frontend staging URLs.
- Render scheduler configuration and successful job logs.
- Managed PostgreSQL backup restore notes.
- Sanitized `python manage.py release_check` output.
- PASS/WARN/FAIL smoke checklist results against live staging URLs.
- Any issues found, fixes applied, and final production-readiness recommendation.

Release candidate gate:

```bash
cd frontend
npm run smoke:release-candidate
```

See [`docs/release-candidate-smoke.md`](docs/release-candidate-smoke.md) for required environment variables and the PASS/WARN/FAIL report format.

## Phase 18 Production Readiness

Phase 18 closes the remaining production blocker by making backup/restore and disaster recovery testable.

New operational docs:

- [`docs/disaster-recovery.md`](docs/disaster-recovery.md): Render PostgreSQL backup/restore rehearsal, `pg_dump`/`pg_restore` helpers, post-restore validation, outage guides, and secrets separation.
- [`docs/production-release-checklist.md`](docs/production-release-checklist.md): release approval gate, env checks, cron checks, Redis/R2 checks, and go/no-go criteria.
- [`docs/rollback-runbook.md`](docs/rollback-runbook.md): code rollback, migration-aware rollback, and database recovery rollback.

Safe helper scripts, run from a repo checkout on an operator machine or CI runner with PostgreSQL client tools installed:

- `sh scripts/pg_dump_backup.sh`: creates a custom-format PostgreSQL dump without printing secrets.
- `sh scripts/restore_to_test_db.sh`: restores only to an explicitly confirmed non-production restore-test database.
- `sh scripts/post_restore_validate.sh`: runs migrations/readiness checks and optional RC smoke against the restored environment.

## Phase Plan

1. Backend foundation, models, authentication, and Docker.
2. Auction/lot CRUD, strict bidding engine, audit trails, and backend tests.
3. Mobile-first Next.js frontend connected to the API.
4. GitHub Actions, deployment notes, and cloud host preparation.
5. UI polish, demo data, and dashboard improvements.
6. Edit flows, Redis-backed throttling, image upload foundations, and E2E smoke tests.
7. Image management, CI E2E, richer filters, and Cloudflare R2 validation.
8. Structured logging, error-reporting readiness, admin operations, and backup runbooks.
9. Scheduled auction ending, winner calculation, anomaly hooks, alert foundations, and operational jobs.
10. Scheduled worker deployment guidance, winner review UX, and email-ready notification delivery.
11. Lightweight settlement/fulfillment workflow without payments.
12. Winner/fulfillment backfill repair, stricter fulfillment transitions, and bidder-visible notifications.
13. Fulfillment timelines, notification read state, and admin-only reviewed outcome repair workflow.
14. Two-admin repair approval, audit-safe repair comments, and global notification unread count.
15. Admin exports, repair audit detail, deployment checks, and rollout governance.
16. Staging seed strategy, backup verification, release checklist UI/reporting, and production runbook tightening.
17. Real cloud staging rehearsal with scheduler, backup restore, release check, and live smoke validation.
18. Production readiness with documented backup/restore rehearsal, disaster recovery, release approval, rollback, and restore validation helpers.

## Local Development

1. Copy `.env.example` to `.env`.
2. Start services:

```bash
docker compose up --build
```

3. Create an admin user:

```bash
docker compose exec backend python manage.py createsuperuser
```

The API will be available at `http://localhost:8000/api/`.
The frontend will be available at `http://localhost:3000/`.

Run migrations manually when needed:

```bash
docker compose exec backend python manage.py migrate
```

Seed demo data:

```bash
docker compose exec backend python manage.py seed_demo
```

Demo credentials:

- Admin: `admin@bidals.demo` / `ChangeMe123!`
- Seller: `seller@bidals.demo` / `ChangeMe123!`
- Bidder: `bidder@bidals.demo` / `ChangeMe123!`

These accounts are for local demos only. Do not use them in production.

Seed staging-only data in a non-production environment:

```bash
docker compose exec backend python manage.py seed_staging_data
```

Staging credentials:

- Admin: `admin@bidals.staging.test` / `ChangeMe123!`
- Seller: `seller@bidals.staging.test` / `ChangeMe123!`
- Bidder: `bidder@bidals.staging.test` / `ChangeMe123!`

The staging seed creates obvious fake records labelled `[STAGING TEST AUCTION]` and `[DEMO LOT]`. It refuses to run when `BIDALS_ENV=production` unless `--force` is supplied; do not use `--force` against production data.

Create or repair a staging admin account without seeding demo data:

```bash
STAGING_ADMIN_PASSWORD='<strong-temporary-password>' \
python manage.py create_staging_admin \
  --username staging_admin \
  --email admin@bidals.staging.test
```

Run that command in the Render backend shell with `BIDALS_ENV=staging`. The command refuses to run outside staging unless `--force` is supplied, reads the password only from the named environment variable, does not print the password, and creates an audit log. Do not set `STAGING_ADMIN_PASSWORD` on production services.

Run backend tests:

```bash
docker compose run --rm backend pytest
```

Close expired auctions and calculate winners:

```bash
docker compose exec backend python manage.py close_expired_auctions
```

Check bid anomaly thresholds:

```bash
docker compose exec backend python manage.py monitor_bid_anomalies --window-minutes 60
```

Deliver pending email-ready notifications:

```bash
docker compose exec backend python manage.py deliver_notifications
```

Repair missing legacy winner outcomes and fulfillment records:

```bash
docker compose exec backend python manage.py backfill_winner_outcomes --dry-run
docker compose exec backend python manage.py backfill_winner_outcomes
```

Verify backup readiness and generate release readiness reports:

```bash
docker compose exec backend python manage.py verify_backup
docker compose exec backend python manage.py release_check
```

Admins can also open `/dashboard/admin/release-check` for the same release checklist in the product UI.

Run the frontend locally without Docker:

```bash
cd frontend
npm install
npm run dev
```

Run frontend quality checks:

```bash
cd frontend
npm run typecheck
npm run build
```

Run E2E smoke tests after starting Docker and seeding demo data:

```bash
cd frontend
npm run test:e2e
```

CI-style local command:

```bash
cd frontend
npm run test:e2e:ci
```

If the frontend is already running, set:

```bash
E2E_SKIP_WEB_SERVER=1
```

The frontend expects:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

Production-like Docker run:

```bash
docker compose -f docker-compose.prod.yml up --build
```

## API Endpoints

Authentication:

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`

Auctions:

- `GET /api/auctions/`
- `POST /api/auctions/`
- `GET /api/auctions/{id}/`
- `PATCH /api/auctions/{id}/`
- `DELETE /api/auctions/{id}/`
- `GET /api/auctions/{id}/results/` seller/admin winner review for one auction.

Lots:

- `GET /api/lots/`
- `POST /api/lots/`
- `GET /api/lots/{id}/`
- `PATCH /api/lots/{id}/`
- `DELETE /api/lots/{id}/`
- `POST /api/lots/{id}/bid/`
- `GET /api/lots/{id}/bids/`
- `GET /api/lots/{id}/audit/`
- `POST /api/lots/{id}/images/`
- `DELETE /api/lots/{lot_id}/images/{image_id}/`
- `PATCH /api/lots/{lot_id}/images/reorder/`

Audit:

- `GET /api/audit/`
- `GET /api/audit/{id}/`

Operations:

- `GET /api/admin/activity/export/` admin-only CSV activity export.
- `GET /api/admin/release-check/` admin-only release readiness report.
- `GET /api/operations/?window_minutes=60` admin-only operational summary.
- `GET /api/dashboard/winners/` seller/admin winner review list.
- `GET /api/dashboard/fulfillment/` seller/admin fulfillment records.
- `PATCH /api/dashboard/fulfillment/{id}/` seller/admin fulfillment updates.
- `GET /api/dashboard/fulfillment/{id}/timeline/` seller/admin fulfillment timeline.
- `GET /api/admin/outcome-repairs/` admin-only outcome repair list.
- `POST /api/admin/outcome-repairs/` admin-only repair request creation.
- `GET /api/admin/outcome-repairs/{id}/` admin-only repair detail.
- `GET /api/admin/outcome-repairs/{id}/audit/` admin-only repair audit timeline.
- `GET /api/admin/outcome-repairs/{id}/comments/` admin-only repair comments.
- `POST /api/admin/outcome-repairs/{id}/comments/` admin-only repair comment creation.
- `POST /api/admin/outcome-repairs/{id}/approve/` admin-only repair approval.
- `POST /api/admin/outcome-repairs/{id}/reject/` admin-only repair rejection.
- `POST /api/admin/outcome-repairs/{id}/apply/` admin-only repair application.
- `GET /api/account/won-lots/` read-only won lots for the authenticated winner.
- `GET /api/account/won-lots/{id}/timeline/` bidder-safe public timeline for a won lot.
- `GET /api/account/notifications/` read-only notifications for the authenticated recipient.
- `GET /api/account/notifications/unread-count/` unread notification count for the authenticated recipient.
- `PATCH /api/account/notifications/{id}/read/` mark one owned notification read.
- `POST /api/account/notifications/mark-all-read/` mark all owned notifications read.

## Bid Example

Request:

```json
{
  "amount": "100.00"
}
```

## Testing Bids From The UI

1. Start the stack with `docker compose up --build`.
2. Register a seller at `http://localhost:3000/register`.
3. Create an auction from `http://localhost:3000/dashboard/auctions/new`.
4. Create an open lot from `http://localhost:3000/dashboard/lots/new`.
5. Register or login as another bidder.
6. Open the lot page and place a bid.

The bid panel waits for `POST /api/lots/{id}/bid/` and displays the backend response. It does not locally approve bids.

Accepted response:

```json
{
  "status": "accepted",
  "lot_id": 1,
  "bid_id": 10,
  "current_price": "100.00",
  "server_timestamp": "2026-04-26T12:00:00Z"
}
```

Rejected response:

```json
{
  "status": "rejected",
  "lot_id": 1,
  "reason": "BID_TOO_LOW",
  "current_price": "120.00",
  "server_timestamp": "2026-04-26T12:00:03Z"
}
```

Rate-limited response:

```json
{
  "status": "rejected",
  "lot_id": 1,
  "reason": "RATE_LIMITED",
  "message": "Too many bid attempts. Please wait before bidding again.",
  "current_price": "120.00",
  "server_timestamp": "2026-04-26T12:00:04Z",
  "retry_after": 35
}
```

## Core Security Rules

- The backend validates every bid inside a database transaction.
- Auction timing is checked against server time only.
- Lot rows are locked before bid acceptance decisions.
- Accepted and rejected bids are recorded.
- Critical actions create audit log entries.
- Frontend state is never trusted for bid acceptance, winner calculation, or permissions.
- Rate limiting is an abuse-prevention layer only; it does not replace bid validation.

## Auction Ending And Winner Calculation

Expired auctions are finalized by a backend management command:

```bash
python manage.py close_expired_auctions
```

The command:

- uses server time only
- transitions expired `live` auctions to `ended`
- locks auction and lot rows while processing
- calculates winners from accepted bids only
- records no-bid and reserve-not-met outcomes
- creates `auction_ended`, `winner_calculated`, notification placeholder, and job-run audit logs
- is safe to rerun without duplicating winners or winner audit records

Winner state is persisted on each lot:

- `winner_status`: `pending`, `winner_assigned`, `no_bids`, or `reserve_not_met`
- `winner`: winning user when a winner is assigned
- `winning_bid`: accepted bid that won the lot
- `winner_calculated_at`: server timestamp for the calculation

Payments are not implemented yet. Lightweight fulfillment follow-up for backend-calculated winners is documented in the Fulfillment Workflow section below.

## Bid Anomalies And Alert Hooks

Run lightweight anomaly detection manually or from a scheduler:

```bash
python manage.py monitor_bid_anomalies --window-minutes 60
```

The MVP detects:

- repeated rejected bids by the same bidder and rejection reason
- repeated rate-limit hits from bid rejection audit logs

When a threshold is crossed, BIDALS creates a `bid_anomaly_detected` audit log, emits a structured log, and calls the alert hook if `ALERT_WEBHOOK_URL` is configured. If no webhook is configured, an `alert_triggered` audit log is still recorded with `delivery_status=not_configured`.

Notifications are delivery-ready but optional. Winner notification events create `OutboundNotification` records and `notification_event` audit logs with backend-owned status. They are informational and never determine winner state.

## Winner Review UX And API

Seller/admin winner review pages:

- `/dashboard/winners`: all calculated outcomes visible to the current seller or admin.
- `/dashboard/auctions/{id}/results`: outcomes for one auction.

Winner review API:

```http
GET /api/dashboard/winners/
GET /api/dashboard/winners/?outcome_status=winner_assigned
GET /api/auctions/{id}/results/
```

Returned outcomes include auction title/status/end time, lot title/status, `outcome_status`, winning bidder summary, winning bid id/amount, reserve price, reserve-met flag, and calculation timestamp.

Permissions:

- Admins can review all calculated outcomes.
- Sellers can review only outcomes for their own auctions.
- Bidders and anonymous users cannot access winner management APIs or pages.

The frontend only displays backend-owned fields. It does not calculate winners.

## Email-Ready Notifications

Winner and auction-ended notification events create `OutboundNotification` records. Delivery is optional and handled by:

```bash
python manage.py deliver_notifications
```

Delivery statuses:

- `pending`: queued by backend events.
- `sent`: Django email backend accepted the message.
- `skipped`: email delivery is disabled or configuration is incomplete.
- `failed`: delivery raised an error.

Local development can use Django's console email backend. Production should use a transactional email provider through SMTP or a future provider-specific adapter. Emails are informational only and never determine auction or winner state.

Development console email example:

```bash
EMAIL_NOTIFICATIONS_ENABLED=True
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=notifications@bidals.local
```

Production SMTP checklist:

- Use provider secret management for `EMAIL_HOST_PASSWORD`.
- Set `DEFAULT_FROM_EMAIL` to a verified sender domain.
- Test delivery in staging before enabling production.
- Monitor `/dashboard/operations` for failed notifications.
- Keep winner review and audit logs as the source of truth when email delivery is delayed or skipped.

## Fulfillment Workflow

Payments are not implemented yet. Fulfillment is an operational follow-up workflow for lots that already have backend-calculated winners.

Fulfillment records are created when a lot receives `winner_status=winner_assigned`. Each record links to the authoritative lot, auction, winning bid, and winner.

Statuses:

- `pending_confirmation`: winner exists, follow-up has not been confirmed.
- `winner_confirmed`: seller/admin has manually confirmed the winner.
- `seller_contacted`: seller has contacted the winner.
- `awaiting_collection_or_delivery`: collection or delivery is being arranged.
- `completed`: fulfillment is complete.
- `cancelled`: fulfillment was cancelled.
- `disputed`: fulfillment needs review.

Seller/admin workflow:

- Open `/dashboard/fulfillment`.
- Filter by status or search auction, lot, or winner.
- Update status, confirmation notes, seller notes, admin notes, and the winner-visible message.
- Every change is audited.

Bidder won-lots visibility:

- Open `/account/won-lots`.
- Bidders see only lots they won.
- Bidders see auction title, lot title, winning bid amount, outcome status, fulfillment status, public message, and date won.
- Bidders cannot edit fulfillment and cannot see seller/admin private notes.

Fulfillment APIs:

```http
GET /api/dashboard/fulfillment/
PATCH /api/dashboard/fulfillment/{id}/
GET /api/account/won-lots/
```

Fulfillment notifications are informational only. Status changes such as `winner_confirmed`, `seller_contacted`, `completed`, and `disputed` can queue notification events, but notifications never determine fulfillment or winner state.

Allowed fulfillment transitions:

- `pending_confirmation` -> `winner_confirmed`, `seller_contacted`, `cancelled`, `disputed`
- `winner_confirmed` -> `seller_contacted`, `awaiting_collection_or_delivery`, `cancelled`, `disputed`
- `seller_contacted` -> `awaiting_collection_or_delivery`, `completed`, `cancelled`, `disputed`
- `awaiting_collection_or_delivery` -> `completed`, `cancelled`, `disputed`
- `disputed` -> `completed`, `cancelled`, `seller_contacted`
- `completed` and `cancelled` are final for status changes in the MVP.

Invalid transitions are rejected by the backend and create a `fulfillment_invalid_transition` audit log. Notes can still be maintained on fulfillment records, but the frontend cannot bypass status rules.

### Fulfillment Timelines

Fulfillment timelines are derived from server-owned audit logs rather than frontend state.

Seller/admin timeline:

```http
GET /api/dashboard/fulfillment/{id}/timeline/
```

Bidder-safe timeline:

```http
GET /api/account/won-lots/{id}/timeline/
```

Seller/admin timelines include status changes, note-update event types, notification events, winner calculations, backfills, and outcome repair events when relevant. Bidders only see safe public events for their own won lots. Private seller notes, admin notes, raw audit metadata, repair reasons, webhook payloads, and internal errors are not exposed to bidder timelines.

## Backfill Winner Outcomes

Use this command after deploying Phase 12 or when repairing legacy ended auctions that predate winner/fulfillment records:

```bash
python manage.py backfill_winner_outcomes --dry-run
python manage.py backfill_winner_outcomes
```

Scoped examples:

```bash
python manage.py backfill_winner_outcomes --dry-run --auction-id 12
python manage.py backfill_winner_outcomes --lot-id 99
```

The command:

- only reads accepted backend bid records
- does not modify accepted bid history
- calculates missing outcomes for ended, non-cancelled lots
- handles no-bid and reserve-not-met outcomes
- creates missing fulfillment records for winner-assigned lots
- is idempotent and safe to rerun
- skips already-finalized outcomes unless only the fulfillment record is missing
- writes `winner_outcome_backfilled` and `fulfillment_created` audit logs for repairs

No `--force` recalculation mode is included in the MVP. If an already-finalized outcome is wrong, repair it only after an admin review of bid and audit history.

## Account Notifications

Bidders can open `/account/notifications` or call:

```http
GET /api/account/notifications/
```

The endpoint returns only notifications where the authenticated user is the recipient. It does not expose recipient email, delivery error details, seller notes, admin notes, audit metadata, webhook payloads, or secrets. Notification delivery remains optional; account notifications are informational and never determine winner or fulfillment state.

Notification read-state endpoints:

```http
GET /api/account/notifications/unread-count/
PATCH /api/account/notifications/{id}/read/
POST /api/account/notifications/mark-all-read/
```

Users can mark only their own notifications read. Marking notifications read creates `notification_marked_read` or `notifications_marked_read` audit logs.
The frontend uses the unread-count endpoint to show the Alerts badge in the global navigation. A zero count hides the badge.

## Admin Activity Export

Admins can export audit activity from `/dashboard/operations` or call:

```http
GET /api/admin/activity/export/?date_from=2026-05-01T00:00:00Z&date_to=2026-05-03T23:59:59Z&action_type=outcome_repair_applied&entity_type=outcome_repair
```

Supported filters:

- `date_from`
- `date_to`
- `actor`
- `action_type`
- `entity_type`
- `entity_id`

The export is CSV and includes audit id, admin user id, admin username, action, entity, timestamp, request id when present, IP when present, and a redacted metadata summary. Passwords, secrets, tokens, authorization headers, and credential-like metadata keys are redacted. Generating an export creates an `admin_activity_exported` audit log.

## Admin Outcome Repair Workflow

Outcome repairs are for rare finalized outcome corrections after admin review. They are not normal winner calculation, and they never alter accepted bid history.

Admin route:

```text
/dashboard/admin/outcome-repairs
```

Workflow:

1. Admin creates a repair request with lot id, accepted bid id, and reason.
2. Request enters `pending_review`.
3. A different admin approves or rejects the request.
4. Only approved repairs can be applied.
5. Applying a repair updates the lot winner, winning bid, winner status, lot status, and fulfillment record.
6. Bid records are never modified.
7. Every step creates an audit log.
8. Admins can add immutable repair comments for audit-safe discussion.
9. Admins can open the repair audit timeline to review the full correction chain.

Validation rules:

- Admin-only.
- Reason is required.
- Requested winning bid must belong to the lot.
- Requested winning bid must have `status=accepted`.
- The admin who requested a repair cannot approve it.
- Repairs cannot be applied before approval.
- Rejected repairs cannot be applied.
- Applied repairs cannot be applied twice.
- Comments are admin-only and ordered chronologically.
- Repair audit detail is admin-only and uses redacted metadata.

The MVP requires two admins for request and approval. Applying an approved repair can be performed by the approver or another admin; a mandatory third-admin apply step is intentionally deferred.

Repair audit endpoint:

```http
GET /api/admin/outcome-repairs/{id}/audit/
```

The response is chronological and includes repair request, comment, approval, rejection, apply, and repair-linked fulfillment events. Viewing repair audit detail creates an `outcome_repair_audit_viewed` audit log, but that view event is excluded from the returned timeline to avoid noisy self-referential timelines.

## Deployment Check

Run deployment safety checks before staging and production deploys:

```bash
python manage.py deployment_check
python manage.py deployment_check --production
```

The command prints `PASS`, `WARN`, and `FAIL` checks without printing secrets. Production mode fails non-zero for critical hardening issues.

Checks include:

- `DEBUG` disabled for production.
- Secret key is present and not the development placeholder.
- `ALLOWED_HOSTS` is configured for deployed hosts.
- Database engine is production-appropriate.
- Redis cache is enabled/configured for production throttling.
- Object storage is enabled when production media uploads require it.
- Email delivery settings are complete when notification delivery is enabled.
- Migrations are applied.
- Health endpoint responds with a request id.

Running the command creates a `deployment_check_run` audit log when the audit table is available.

## Backup Verification

Run a non-destructive backup readiness check before releases:

```bash
python manage.py verify_backup
```

The command checks database connectivity, critical BIDALS tables, optional `BACKUP_LAST_VERIFIED_AT`, and optional `BACKUP_LAST_RESTORE_TEST_AT`. It prints `PASS`, `WARN`, and `FAIL` without inspecting or restoring production backups directly. Use `--fail-on-warn` when you want staging or CI to stop on stale backup metadata.

Suggested backup metadata env vars:

- `BACKUP_PROVIDER`: `render`, `railway`, `fly`, `rds`, or another provider label.
- `BACKUP_LAST_VERIFIED_AT`: ISO-8601 timestamp for the most recent provider backup verification.
- `BACKUP_LAST_RESTORE_TEST_AT`: ISO-8601 timestamp for the most recent restore test.

Provider-specific verification:

- Render: confirm the managed PostgreSQL backup schedule in the dashboard, note the latest backup timestamp, and update `BACKUP_LAST_VERIFIED_AT` after a successful staging restore test.
- Railway: confirm backups or snapshots for the PostgreSQL service, export a backup when required by plan, and run a restore into staging before updating restore metadata.
- Fly.io: verify the Postgres app snapshot/backup mechanism, test restore into a non-production Postgres app, and update restore metadata only after BIDALS post-restore checks pass.
- Generic PostgreSQL: use provider-native backups or `pg_dump`, keep dumps outside app containers, and test restores against a staging database.

Do not run destructive restore operations from `verify_backup`; restore tests belong in staging or provider tooling.

Phase 18 helper scripts for non-production rehearsals, run from the repository root:

```bash
DATABASE_URL='<postgres-url>' BIDALS_ENV=staging sh scripts/pg_dump_backup.sh

BACKUP_FILE=backups/<dump-file>.dump \
RESTORE_DATABASE_URL='<restore-test-postgres-url>' \
RESTORE_TARGET_ENV=restore-test \
RESTORE_TARGET_CONFIRM=non-production-restore-ok \
sh scripts/restore_to_test_db.sh

DJANGO_SETTINGS_MODULE=bidals.settings.prod \
DATABASE_URL='<restore-test-postgres-url>' \
API_BASE_URL=https://<restore-test-backend>/api \
sh scripts/post_restore_validate.sh
```

`restore_to_test_db.sh` refuses to run unless the target database is explicitly confirmed as non-production and differs from the active `DATABASE_URL`. The full procedure lives in [`docs/disaster-recovery.md`](docs/disaster-recovery.md).

## Release Readiness

Generate a release readiness report from the backend:

```bash
python manage.py release_check
```

Admins can also review the same report at `/dashboard/admin/release-check` or call:

```http
GET /api/admin/release-check/
```

The report groups checks into `system`, `database`, `backup`, `core_flows`, `ops`, and `notifications`. Automated checks cover hardening, migrations, the health endpoint, backup readiness, audit log readability, configured anomaly thresholds, and notification delivery safety. Manual checks deliberately remain `WARN` until an operator verifies real deployed flows such as login, auction creation, accepted/rejected bidding, winner calculation, fulfillment, unread count, and repair workflow access.

## Rollout Checklists

Detailed production release and rollback runbooks live in [`docs/production-release-checklist.md`](docs/production-release-checklist.md) and [`docs/rollback-runbook.md`](docs/rollback-runbook.md).

Staging rollout:

- Deploy from a GitHub branch or tagged release candidate.
- Configure staging env vars with non-production secrets.
- Run `python manage.py migrate`.
- Run `python manage.py deployment_check`.
- Run `python manage.py seed_staging_data`.
- Run `python manage.py verify_backup`.
- Run `python manage.py release_check`.
- Open `/dashboard/admin/release-check` as an admin.
- Test health, login, admin access, auction creation, lot creation, accepted bid, rejected bid, audit logs, notification unread count, admin export, release check, and repair audit access.

Production rollout:

- Confirm database backup is enabled before deploy.
- Confirm `BACKUP_LAST_VERIFIED_AT` and `BACKUP_LAST_RESTORE_TEST_AT` reflect real provider/staging validation.
- Confirm rollback target image/commit is known.
- Confirm production env vars are set and secrets are not committed.
- Run `python manage.py migrate`.
- Run `python manage.py deployment_check --production`.
- Run `python manage.py verify_backup`.
- Run `python manage.py release_check`.
- Run scheduled job commands once manually if needed: `close_expired_auctions`, `monitor_bid_anomalies`, and `deliver_notifications` if email delivery is enabled.

Post-deploy smoke:

- `GET /api/health/`
- Login as bidder and admin.
- Create auction and lot as seller/admin.
- Place a valid bid and verify backend accepted response.
- Place an invalid bid and verify backend rejected response.
- Confirm audit log creation.
- Run or verify winner calculation job.
- Open fulfillment page.
- Verify notification unread count.
- Export admin activity CSV.
- Open the release readiness page.
- Open repair workflow and repair audit detail as admin.

Rollback notes:

- Prefer reverting to the previous GitHub commit/image.
- Do not roll back database migrations casually after bids, fulfillment, or repairs exist.
- If rollback is required after migrations, take a database backup first and verify audit logs remain readable.
- Re-run `deployment_check` and the post-deploy smoke checklist after rollback.

## Environment Variables

Backend:

- `DJANGO_SETTINGS_MODULE`: use `bidals.settings.prod` in production.
- `BIDALS_ENV`: runtime environment label such as `development`, `staging`, or `production`.
- `DJANGO_SECRET_KEY`: required in production; generate a long random value.
- `DJANGO_DEBUG`: must be `False` in production.
- `DJANGO_ALLOWED_HOSTS`: comma-separated backend hostnames.
- `DJANGO_CORS_ALLOWED_ORIGINS`: comma-separated frontend origins.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: comma-separated trusted frontend origins.
- `DJANGO_SECURE_SSL_REDIRECT`: usually `True` in production.
- `DJANGO_SECURE_HSTS_SECONDS`: use `31536000` after HTTPS is confirmed.
- `DATABASE_URL`: managed PostgreSQL URL.
- `DATABASE_CONN_MAX_AGE`: persistent DB connection age, default `60`.
- `REDIS_URL`: managed Redis URL when Redis-backed features are enabled. Render Redis may provide a `rediss://...` URL; keep the exact provider URL in backend secrets.
- `USE_REDIS_CACHE`: set `True` in production/staging rehearsal so bid throttling uses shared Redis.
- `REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS`: Redis connection timeout, default `2`.
- `REDIS_SOCKET_TIMEOUT_SECONDS`: Redis socket timeout, default `2`.
- `REDIS_CACHE_KEY_PREFIX`: cache key prefix, default `bidals`.
- `FRONTEND_URL`: deployed frontend origin.
- `LOG_LEVEL`: backend log level, usually `INFO` in production.
- `ENABLE_STRUCTURED_LOGGING`: set `True` for JSON logs suitable for cloud log drains.
- `SENTRY_DSN`: optional Sentry DSN. Error reporting is disabled when blank.
- `SENTRY_ENVIRONMENT`: Sentry environment name, for example `production`.
- `SENTRY_TRACES_SAMPLE_RATE`: optional Sentry tracing sample rate, default `0.0`.
- `BID_RATE_LIMIT_AUTHENTICATED_ATTEMPTS`: bid attempts per authenticated user per window, default `10`.
- `BID_RATE_LIMIT_ANONYMOUS_ATTEMPTS`: bid attempts per anonymous IP per window, default `2`.
- `BID_RATE_LIMIT_WINDOW_SECONDS`: bid rate-limit window length, default `60`.
- `BID_ANOMALY_REJECT_THRESHOLD`: rejected bids by one bidder/reason before anomaly logging, default `5`.
- `BID_ANOMALY_RATE_LIMIT_THRESHOLD`: rate-limit hits by one bidder/IP bucket before anomaly logging, default `3`.
- `ALERT_WEBHOOK_URL`: optional operations webhook URL for anomaly and job-failure alerts.
- `ALERT_WEBHOOK_TIMEOUT_SECONDS`: alert webhook timeout, default `3`.
- `SCHEDULED_JOBS_CONFIGURED`: set `True` after production schedulers are configured.
- `EMAIL_NOTIFICATIONS_ENABLED`: set `True` to deliver pending outbound notifications.
- `EMAIL_BACKEND`: Django email backend, for example SMTP or console.
- `EMAIL_HOST`: SMTP host when using SMTP.
- `EMAIL_PORT`: SMTP port, default `587`.
- `EMAIL_HOST_USER`: SMTP username.
- `EMAIL_HOST_PASSWORD`: SMTP password or provider token.
- `EMAIL_USE_TLS`: whether SMTP TLS is enabled.
- `DEFAULT_FROM_EMAIL`: sender email address for outbound notifications.
- `MEDIA_URL`: local or object-storage media URL prefix.
- `MEDIA_ROOT`: local development upload directory.
- `LOT_IMAGE_MAX_UPLOAD_SIZE_MB`: upload size limit for lot images.
- `USE_S3`: set `True` to use django-storages S3-compatible media storage.
- `AWS_ACCESS_KEY_ID`: object storage access key.
- `AWS_SECRET_ACCESS_KEY`: object storage secret key.
- `AWS_STORAGE_BUCKET_NAME`: object storage bucket name.
- `AWS_S3_REGION_NAME`: object storage region.
- `AWS_S3_ENDPOINT_URL`: S3-compatible endpoint for R2, Spaces, or similar.
- `AWS_S3_CUSTOM_DOMAIN`: optional public media/custom domain, without secrets.
- `AWS_QUERYSTRING_AUTH`: `True` for private buckets with signed image URLs, or `False` when using a public media domain.
- `AWS_S3_ADDRESSING_STYLE`: S3 request addressing style, default `path` for S3-compatible providers such as R2.
- `AWS_S3_SIGNATURE_VERSION`: S3 signature version, default `s3v4`.
- `AWS_S3_CACHE_CONTROL`: cache-control header for uploaded lot images, default `max-age=86400`.
- `BACKUP_PROVIDER`: provider label used in backup verification output.
- `BACKUP_LAST_VERIFIED_AT`: ISO-8601 timestamp for the most recently verified backup.
- `BACKUP_LAST_RESTORE_TEST_AT`: ISO-8601 timestamp for the most recent successful restore test.
- `PORT`: backend container port when provided by the host.
- `WEB_CONCURRENCY`: Gunicorn worker count.

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`: full backend API base, for example `https://api.example.com/api`.
- `NEXT_TELEMETRY_DISABLED`: set to `1` if desired.
- `PORT`: frontend container port when provided by the host.
- `HOSTNAME`: use `0.0.0.0` in containers.

E2E smoke tests:

- `E2E_BASE_URL`: frontend URL, default `http://127.0.0.1:3000`.
- `E2E_SKIP_WEB_SERVER`: set `1` when Docker or another dev server is already serving the frontend.
- `E2E_SELLER_USERNAME`, `E2E_BIDDER_USERNAME`, `E2E_ADMIN_USERNAME`: seeded demo usernames.
- `E2E_DEMO_PASSWORD`: seeded demo password.
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`: optional browser path when using a system Chromium install.

Storage validation:

- When `USE_S3=True`, the backend fails fast unless `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, and `AWS_S3_REGION_NAME` are set.
- `AWS_S3_ENDPOINT_URL` must be a full HTTPS endpoint.
- `AWS_S3_CUSTOM_DOMAIN`, when provided, is normalized to a hostname/path for generated media URLs.

## Production Commands

Backend build:

```bash
docker build -t bidals-backend ./backend
```

Frontend build:

```bash
docker build \
  -f frontend/Dockerfile.prod \
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api \
  -t bidals-frontend \
  ./frontend
```

Backend start command:

```bash
gunicorn bidals.wsgi:application --bind 0.0.0.0:${PORT:-8000}
```

Migration command:

```bash
python manage.py migrate
```

Operational job commands:

```bash
python manage.py close_expired_auctions
python manage.py monitor_bid_anomalies --window-minutes 60
python manage.py deliver_notifications
```

Schedule `close_expired_auctions` every minute, or at the shortest interval your provider supports. Schedule `monitor_bid_anomalies` every few minutes. Schedule `deliver_notifications` every few minutes if email delivery is enabled. These commands are idempotent and use backend server time and persisted backend state; they do not trust frontend countdowns.

Static files:

```bash
python manage.py collectstatic --noinput
```

The backend Docker image already runs `collectstatic` during build. Do not skip migrations in production.

## Scheduler Setup

BIDALS does not require Celery yet. Use the scheduler provided by your cloud host, cron, or a one-off worker process to run:

```bash
python manage.py close_expired_auctions
```

Recommended cadence: every minute for live auction correctness. The command is idempotent and will skip auctions that are not expired or already finalized.

For anomaly monitoring, run:

```bash
python manage.py monitor_bid_anomalies --window-minutes 60
```

Recommended cadence: every 5 minutes for the MVP. Alert delivery is optional and controlled by `ALERT_WEBHOOK_URL`.

For notification delivery, run:

```bash
python manage.py deliver_notifications
```

Recommended cadence: every 5 minutes when `EMAIL_NOTIFICATIONS_ENABLED=True`. If email is disabled or incomplete, pending notifications are marked `skipped` rather than crashing the worker.

### Render Scheduled Workers

Use GitHub as the source for the backend image. Add Render Cron Jobs or background worker jobs that run against the same backend image and environment as the web service.

Use the scheduled-job wrapper instead of inline `python manage.py ...` commands. The wrapper changes into the backend directory, requires `DJANGO_SETTINGS_MODULE=bidals.settings.prod`, maps `DJANGO_DATABASE_URL` to `DATABASE_URL` when needed, validates the minimum production env vars before importing Django, and prints only safe diagnostics before running the command.

Render cron service settings:

- Root Directory: leave blank/unset
- Runtime: Docker
- Dockerfile Path: `backend/Dockerfile`
- Docker Build Context Directory: `backend`
- Environment: copy the same backend staging/production env group/secrets used by the web service. Do not put secrets inline in the command field.

Required env vars for every Render cron job:

- `DJANGO_SETTINGS_MODULE=bidals.settings.prod`
- `DJANGO_SECRET_KEY=<secret>`
- `DJANGO_ALLOWED_HOSTS=<backend host>`
- `DATABASE_URL=<managed PostgreSQL URL>` or `DJANGO_DATABASE_URL=<managed PostgreSQL URL>`

These required vars apply to all three scheduled jobs, including `deliver_notifications`. Email-specific vars are additional only when notification delivery is enabled.

Recommended to copy from the backend web service for parity:

- `FRONTEND_URL`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SECURE_HSTS_SECONDS`
- `DATABASE_CONN_MAX_AGE`
- `USE_REDIS_CACHE=True`
- `REDIS_URL=<managed Redis URL>`
- `REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS`
- `REDIS_SOCKET_TIMEOUT_SECONDS`
- `REDIS_CACHE_KEY_PREFIX`
- `USE_S3`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_STORAGE_BUCKET_NAME`
- `AWS_S3_ENDPOINT_URL`
- `AWS_S3_REGION_NAME`
- `AWS_S3_CUSTOM_DOMAIN`
- `AWS_QUERYSTRING_AUTH`
- `AWS_S3_ADDRESSING_STYLE`
- `AWS_S3_SIGNATURE_VERSION`
- `AWS_S3_CACHE_CONTROL`
- `EMAIL_NOTIFICATIONS_ENABLED`
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`
- `DEFAULT_FROM_EMAIL`
- `ALERT_WEBHOOK_URL`
- `ALERT_WEBHOOK_TIMEOUT_SECONDS`

The runner fails once with a combined missing-var list for the required vars above. Redis, S3, and email settings are reported as safe `pass`, `warn_*`, or `not_enabled` diagnostics without printing secret values.

Commands:

- Auction closer: `sh /app/scripts/run_scheduled_job.sh close_expired_auctions`
- Anomaly monitor: `sh /app/scripts/run_scheduled_job.sh monitor_bid_anomalies --window-minutes 60`
- Notification delivery: `sh /app/scripts/run_scheduled_job.sh deliver_notifications`

The image also exposes `/usr/local/bin/bidals-scheduled-job` as a symlink to the same runner. Either form is acceptable, but the `/app/scripts/...` command makes the copied file path explicit.

Temporary diagnostic command if Render cannot find the runner:

```bash
sh -c 'pwd && ls -l /app/scripts/run_scheduled_job.sh /usr/local/bin/bidals-scheduled-job'
```

The older raw commands below are safe for local/manual runs from inside the backend directory, but should not be used as Render cron commands:

- Auction closer: `python manage.py close_expired_auctions`
- Anomaly monitor: `python manage.py monitor_bid_anomalies --window-minutes 60`
- Notification delivery: `python manage.py deliver_notifications`

The jobs need the same `DATABASE_URL`, Redis/cache settings, email env vars if delivery is enabled, `ALERT_WEBHOOK_URL` if alert hooks are enabled, and Django settings as the backend web service. Configure logs to go to the same log stream as the web service. Do not put secrets inline in the command field.

### Railway Scheduled Workers

Use Railway service cron or a separate backend service with a scheduled start command. The worker should use the backend code/image and the same PostgreSQL, Redis, alert, and email variables as the API service.

Safe manual reruns:

```bash
railway run python manage.py close_expired_auctions
railway run python manage.py monitor_bid_anomalies --window-minutes 60
railway run python manage.py deliver_notifications
```

These jobs are idempotent. Rerunning the auction closer will not duplicate winners or critical winner audit records.

### Fly.io Scheduled Workers

For Fly.io, use a small machine/process group, Fly cron, or an external scheduler that runs one-off commands against the backend app.

Examples:

```bash
fly ssh console -C "python manage.py close_expired_auctions"
fly ssh console -C "python manage.py monitor_bid_anomalies --window-minutes 60"
fly ssh console -C "python manage.py deliver_notifications"
```

Workers need network access to the production PostgreSQL database and Redis if Redis-backed throttling/cache is enabled. Keep job logs structured and review `/dashboard/operations` after failures.

## Health Checks

- Backend: `GET /api/health/`
- Frontend: `GET /api/health`

Backend response:

```json
{
  "status": "ok",
  "service": "bidals-backend"
}
```

## GitHub Actions

The CI workflow runs on pushes and pull requests to `main`.

- Backend: install Python dependencies, check migrations, run Django checks, run pytest.
- Frontend: `npm ci`, typecheck, lint, production build.
- Docker: build backend image and frontend production image.

Deployment secrets should be configured in the cloud provider or GitHub repository settings. Do not commit real secrets.

## Cloud Deployment Targets

The project is being prepared for GitHub-based deployment to Render, Railway, Fly.io, DigitalOcean App Platform, and later AWS. Production deployments should provide managed PostgreSQL, managed Redis if live features/background jobs are enabled, and environment variables matching `.env.example`.

### Render

Use GitHub as the source. Render supports build, pre-deploy, and start commands; health checks can be configured with a path.

Services:

- PostgreSQL managed database.
- Redis managed instance if Redis-backed jobs/live features are enabled.
- Backend web service from `backend/Dockerfile`.
- Frontend web service from `frontend/Dockerfile.prod`, or a static/web service if you later export the app.

Backend settings:

- Dockerfile path: `backend/Dockerfile`
- Health check path: `/api/health/`
- Start command: use the Dockerfile `CMD`, or `gunicorn bidals.wsgi:application --bind 0.0.0.0:$PORT`
- Pre-deploy command if available: `python manage.py migrate`
- Required env vars: all backend variables listed above.

Frontend settings:

- Dockerfile path: `frontend/Dockerfile.prod`
- Build arg: `NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com/api`
- Health check path: `/api/health`
- Required env vars: `NEXT_PUBLIC_API_BASE_URL`, `NEXT_TELEMETRY_DISABLED=1`

Common Render issues:

- `DJANGO_ALLOWED_HOSTS` must include the Render backend hostname and any custom API domain.
- `DJANGO_CORS_ALLOWED_ORIGINS` and `DJANGO_CSRF_TRUSTED_ORIGINS` must include the frontend URL.
- Run migrations before serving new code.
- Keep `DJANGO_SECURE_SSL_REDIRECT=True` once HTTPS is working.

Useful docs: [Render deploys](https://render.com/docs/deploys/), [Render health checks](https://render.com/docs/health-checks/), [Render environment variables](https://render.com/docs/configure-environment-variables/).

### Railway

Use GitHub as the source and create separate services for backend and frontend.

Services:

- PostgreSQL plugin/service.
- Redis plugin/service if needed.
- Backend service using `backend/Dockerfile`.
- Frontend service using `frontend/Dockerfile.prod`.

Backend settings:

- Dockerfile path: `backend/Dockerfile`
- Start command: Dockerfile `CMD` is enough. If overriding, wrap shell variable expansion, for example `sh -c 'gunicorn bidals.wsgi:application --bind 0.0.0.0:$PORT'`.
- Migration command: run `python manage.py migrate` manually with Railway CLI or as a release/deploy step if your workflow supports it.
- Required env vars: all backend variables listed above.

Frontend settings:

- Dockerfile path: `frontend/Dockerfile.prod`
- Build variable: `NEXT_PUBLIC_API_BASE_URL=https://your-backend.up.railway.app/api`
- Runtime variables: `PORT`, `HOSTNAME=0.0.0.0`, `NEXT_TELEMETRY_DISABLED=1`

Common Railway issues:

- Railway service variables are scoped per service; define backend secrets only on the backend service.
- `NEXT_PUBLIC_API_BASE_URL` must be available during the frontend build.
- If overriding a Docker start command and using env vars, run it through `sh -c`.

Useful docs: [Railway start commands](https://docs.railway.com/deployments/start-command), [Railway variables](https://docs.railway.com/variables).

### Fly.io

Use GitHub as the source or deploy from the Fly CLI. The Dockerfiles are provider-ready.

Services:

- Backend Fly app.
- Frontend Fly app.
- Fly Postgres or external managed PostgreSQL.
- Redis provider if Redis-backed features are enabled.

Backend settings:

- Dockerfile: `backend/Dockerfile`
- Internal port: `8000`, or map Fly's service port to the app `PORT`.
- Release command in `fly.toml`: `python manage.py migrate`
- Health check path: `/api/health/`
- Secrets: set backend env vars with `fly secrets set`.

Frontend settings:

- Dockerfile: `frontend/Dockerfile.prod`
- Build arg: `NEXT_PUBLIC_API_BASE_URL=https://your-backend.fly.dev/api`
- Health check path: `/api/health`

Common Fly.io issues:

- `DJANGO_ALLOWED_HOSTS` must include the `.fly.dev` backend hostname.
- Configure `release_command` so migrations run before new machines serve traffic.
- Use Fly volumes only for intentional persistent storage; do not use container disk for important uploaded lot images.

Useful docs: [Fly Dockerfile deploys](https://fly.io/docs/languages-and-frameworks/dockerfile/), [Fly app configuration and release_command](https://fly.io/docs/reference/configuration/).

## Static And Media Files

Django static files are collected into the backend image and served by WhiteNoise.

Lot images can be represented as external JSON URLs or uploaded through the `LotImage` model at `POST /api/lots/{id}/images/`. Local development/staging fallback stores uploaded files under `MEDIA_ROOT` and serves them from `MEDIA_URL` only when `SERVE_LOCAL_MEDIA=True` and `USE_S3=False`. Production should set `USE_S3=True` and provide S3-compatible object storage credentials for S3, Cloudflare R2, DigitalOcean Spaces, or similar. Do not store important uploaded media only inside ephemeral container storage.

Image management endpoints:

```http
DELETE /api/lots/{lot_id}/images/{image_id}/
PATCH /api/lots/{lot_id}/images/reorder/
```

Reorder payload:

```json
{
  "image_order": [
    { "id": 3, "sort_order": 1 },
    { "id": 1, "sort_order": 2 }
  ]
}
```

Only the lot's seller or an admin can upload, delete, or reorder lot images. Public users can view image URLs on visible lots.

### Cloudflare R2 Media Setup

Use R2 as S3-compatible storage so uploaded lot images persist across Render redeploys/restarts:

1. Create an R2 bucket for BIDALS media.
2. Create an R2 S3 API token with object read/write access scoped to that bucket.
3. Copy the R2 S3 API endpoint in the form `https://<account-id>.r2.cloudflarestorage.com`.
4. Use region `auto`.
5. Decide media URL strategy:
   - Private bucket: set `AWS_QUERYSTRING_AUTH=True`. The backend returns signed image URLs; storage secrets stay server-side.
   - Public/custom domain: configure an R2 custom/public domain, set `AWS_S3_CUSTOM_DOMAIN=<media-domain>`, and set `AWS_QUERYSTRING_AUTH=False`.
6. Configure backend env vars in Render:

```bash
USE_S3=True
SERVE_LOCAL_MEDIA=False
AWS_ACCESS_KEY_ID=<r2-access-key>
AWS_SECRET_ACCESS_KEY=<r2-secret-key>
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
AWS_S3_REGION_NAME=auto
AWS_S3_CUSTOM_DOMAIN=<optional-public-media-domain>
AWS_QUERYSTRING_AUTH=True
AWS_S3_ADDRESSING_STYLE=path
AWS_S3_SIGNATURE_VERSION=s3v4
AWS_S3_CACHE_CONTROL=max-age=86400
```

Never expose R2 credentials to the frontend. The frontend uses only image URLs returned by the backend. If using a public/custom media domain, ensure the bucket/domain policy allows browser reads for visible lot images. If using signed URLs, reloading the lot/feed fetches fresh URLs from the backend.

Render persistence test:

1. Deploy the backend with `USE_S3=True` and the R2 env vars above.
2. Log in as seller/admin and upload a lot image from `/dashboard/lots/{id}/edit`.
3. Confirm the lot detail/feed renders the uploaded image.
4. Redeploy or restart the Render backend service.
5. Reload the lot detail/feed. The image should still load because the file is stored in R2, not the Render container filesystem.

## Edit Flows

Seller/admin auction editing:

- Open `http://localhost:3000/dashboard`.
- Choose `Edit` on an auction, or open `/dashboard/auctions/{id}/edit`.
- Save title, description, start/end times, and status.
- The backend enforces owner/admin permissions and validates `end_time > start_time`.

Seller/admin lot editing:

- Open `http://localhost:3000/dashboard`.
- Choose `Edit` on a lot, or open `/dashboard/lots/{id}/edit`.
- Save title, description, reserve price, status, external image URL, and optional uploaded image.
- `starting_price` and `bid_increment` are locked in the UI after accepted bids and also blocked by backend validation.

## E2E Smoke Tests

The Playwright smoke suite is intentionally small. It assumes the stack is running and `seed_demo` has been run.

```bash
docker compose up --build
docker compose exec backend python manage.py seed_demo
cd frontend
npx playwright install chromium
E2E_SKIP_WEB_SERVER=1 npm run test:e2e
```

Run the smoke suite from a host Node environment or a Playwright-compatible container. The default frontend development image uses Alpine Linux for a compact Next.js dev container; Playwright's bundled browser is glibc-based, so in-container E2E runs need either a system Chromium path via `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` or an official Playwright image.

The suite covers:

- seller login
- auction creation and edit
- lot creation and edit
- bidder accepted and rejected bid feedback
- admin audit log visibility

GitHub Actions includes an `e2e` job that starts PostgreSQL and Redis services, migrates the backend, seeds demo data, starts Django, installs Playwright Chromium, and runs `npm run test:e2e:ci`. On failure, it uploads the Playwright report artifact when available.

## Release Candidate Smoke Suite

Use this suite before production releases to validate the full backend-owned auction lifecycle against deployed staging URLs.

```bash
cd frontend
RC_SMOKE_API_BASE_URL=https://bidals.onrender.com/api \
RC_SMOKE_FRONTEND_URL=https://bidals-1.onrender.com \
RC_SMOKE_SELLER_USERNAME=<seller> \
RC_SMOKE_SELLER_PASSWORD=<seller-password> \
RC_SMOKE_BIDDER_USERNAME=<bidder> \
RC_SMOKE_BIDDER_PASSWORD=<bidder-password> \
RC_SMOKE_ADMIN_USERNAME=<admin> \
RC_SMOKE_ADMIN_PASSWORD=<admin-password> \
npm run smoke:release-candidate
```

For the full two-admin repair smoke, also set:

```bash
RC_SMOKE_ADMIN2_USERNAME=<second-admin>
RC_SMOKE_ADMIN2_PASSWORD=<second-admin-password>
```

The runner creates uniquely named `[RC SMOKE]` staging records, waits for the deployed cron-backed auction close path, and reports `PASS`, `WARN`, and `FAIL`. It validates seller/bidder/admin login, auction and lot creation, optional image upload, accepted and rejected bid responses, bid history, audit logs, admin CSV export, winner outcome calculation, fulfillment, won-lots, notifications, mark-read, and repair workflow access. Full repair request/approve/apply runs when second-admin credentials are configured.

Current Render staging evidence: the release candidate smoke suite passes with `PASS=19`, `WARN=2`, `FAIL=0`. Remaining `WARN` items are second-admin credentials and the skipped full two-admin repair create/approve/apply path. Backup/restore proof is a separate production go/no-go requirement.

The runner does not calculate winners, bypass bid rules, alter historical bids, or use frontend state as authority. Details live in [`docs/release-candidate-smoke.md`](docs/release-candidate-smoke.md).

## Dashboard Filtering

Seller dashboard filters:

- auction status
- lot status
- auction title search
- lot title search
- auction date range
- newest, oldest, and ending-soon sorting

Admin audit filters:

- action type
- actor username, email, or id
- entity type
- entity id
- accepted/rejected bid event
- date range
- metadata text search

## Observability And Operations

Backend API responses include an `X-Request-ID` header. If a request arrives with `X-Request-ID`, BIDALS preserves it; otherwise the backend generates one. When `ENABLE_STRUCTURED_LOGGING=True`, logs are emitted as JSON and include safe operational fields such as `event`, `request_id`, `method`, `path`, `status_code`, `duration_ms`, and `user_id` when available.

Bid logs use explicit event names:

- `event=bid_accepted` with `auction_id`, `lot_id`, `bidder_id`, `amount`, `previous_price`, `new_price`, and `server_timestamp`.
- `event=bid_rejected` with `auction_id`, `lot_id`, `bidder_id`, `attempted_amount`, `current_price`, `rejection_reason`, and `server_timestamp`.

Do not log passwords, auth tokens, secrets, or unnecessary personal data. Cloud providers such as Render, Railway, Fly.io, and DigitalOcean can forward JSON logs to their native log drains or external log tools.

### Admin Operations View

Admins can open `http://localhost:3000/dashboard/operations`.

The page is backed by:

```http
GET /api/operations/?window_minutes=60
```

The endpoint is admin-only and summarizes:

- total accepted/rejected bids
- recent accepted and rejected bids
- rejected bids by reason
- repeated bidder failures in the selected time window
- recent auction close runs
- recent winner calculations
- recent anomaly signals
- recent alert hook events
- recent notification placeholders
- outbound notification queue status
- failed notification delivery attempts
- fulfillment status totals and recent fulfillment updates
- recent job failures
- recent audit events
- recent server-side bid errors if tracked as `SERVER_ERROR`

### Sentry Setup

Sentry is optional. Leave `SENTRY_DSN` blank for local development. To enable it in production:

1. Create a Sentry project for the Django backend.
2. Set `SENTRY_DSN` in the backend service environment.
3. Set `SENTRY_ENVIRONMENT=production`.
4. Keep `SENTRY_TRACES_SAMPLE_RATE=0.0` initially unless you intentionally want tracing.
5. Redeploy and trigger a harmless test exception in a non-production environment first.

The configuration uses `send_default_pii=False`; do not add custom Sentry context containing passwords, tokens, or secrets.

## Production Runbook

Startup:

1. Deploy backend and frontend from GitHub using the reviewed release branch or tag.
2. Confirm environment variables are set in the provider secret manager.
3. Run `python manage.py migrate` before sending traffic to the new backend.
4. Run `python manage.py deployment_check --production`.
5. Run `python manage.py verify_backup`.
6. Run `python manage.py release_check` and review remaining manual `WARN` items.
7. Configure schedulers for `close_expired_auctions`, `monitor_bid_anomalies`, and `deliver_notifications` if email delivery is enabled.
8. Confirm `/api/health/` and `/dashboard/admin/release-check` are reachable.

Daily operations:

1. Check `/api/health/`.
2. Open `/dashboard/operations` and review rejected bid spikes, anomalies, job failures, and failed notifications.
3. Review repair workflow items and comments in `/dashboard/admin/outcome-repairs`.
4. Check admin exports and audit logs for unusual admin activity.
5. Confirm provider backup jobs completed.
6. Review release-check warnings before planned deploys.

Incident response:

- Bidding failures: check health, database connectivity, Redis/throttling, structured bid logs, and recent deploys before changing any auction or lot state.
- Job failures: rerun `close_expired_auctions` or `monitor_bid_anomalies` manually; the commands are idempotent and create audit logs.
- Notification failures: run `deliver_notifications`, inspect failed outbound notifications, and confirm email env vars before retrying.
- Database connectivity: pause deploys, inspect provider status, avoid manual winner/fulfillment changes, and preserve logs/request IDs.

Recovery:

1. Restart backend/frontend services from the cloud provider dashboard when the failure is process-level.
2. Rerun scheduled jobs manually after service recovery; they are designed to be safe to rerun.
3. If database recovery is needed, restore to staging first and run the restore checklist below.
4. Run `deployment_check`, `verify_backup`, and `release_check` after recovery.
5. Confirm login, bidding, audit logs, winner review, fulfillment, notifications, and repair workflow access.

## Backup Runbook

Use provider-managed PostgreSQL backups for production. Recommended baseline:

- Daily automated backups for MVP.
- Point-in-time recovery if the provider supports it.
- Retention of at least 7 days for MVP, longer for regulated or high-value auctions.
- Backup monitoring enabled in the cloud provider.
- Periodic restore tests to a staging database.

Manual backup example when you have direct PostgreSQL access:

```bash
DATABASE_URL='<postgres-url>' BIDALS_ENV=staging sh scripts/pg_dump_backup.sh
```

Do not rely on container filesystem snapshots for PostgreSQL backups. Uploaded production media should live in object storage such as Cloudflare R2, S3, or Spaces and should have its own lifecycle/backup policy.

Backup verification checklist:

- Backup exists in the provider dashboard.
- Backup frequency matches the release risk profile.
- Latest backup timestamp is recorded in `BACKUP_LAST_VERIFIED_AT`.
- Restore was tested recently and recorded in `BACKUP_LAST_RESTORE_TEST_AT`.
- Restored staging database contains `accounts_user`, `auctions_auction`, `auctions_lot`, `auctions_bid`, and `audit_auditlog`.
- BIDALS post-restore checks pass before the backup is considered verified.

## Restore Runbook

Restore to staging first whenever possible:

1. Pause deploys and identify the target restore point.
2. Restore the managed PostgreSQL backup to a new database or staging database.
3. Point a staging backend at the restored database.
4. Run `python manage.py migrate` if the code version requires pending migrations.
5. Validate users, auctions, lots, bids, and audit logs.
6. Test login, auction browsing, accepted bid, rejected bid, and audit visibility.
7. Validate object storage media URLs for lot images.
8. Promote the restored database only after validation.

Guarded restore-test helper:

```bash
BACKUP_FILE=backups/<dump-file>.dump \
RESTORE_DATABASE_URL='<restore-test-postgres-url>' \
RESTORE_TARGET_ENV=restore-test \
RESTORE_TARGET_CONFIRM=non-production-restore-ok \
sh scripts/restore_to_test_db.sh
```

Post-restore validation helper:

```bash
DJANGO_SETTINGS_MODULE=bidals.settings.prod \
DATABASE_URL='<restore-test-postgres-url>' \
API_BASE_URL=https://<restore-test-backend>/api \
sh scripts/post_restore_validate.sh
```

BIDALS-specific post-restore checks:

- Verify user roles for admin, seller, and bidder accounts.
- Verify auction start/end times and statuses.
- Verify lot `current_price` values match accepted bid history.
- Verify rejected bid and audit logs are present.
- Verify `POST /api/lots/{id}/bid/` still rejects invalid bids server-side.
- Verify `GET /api/operations/` works for admins only.

## Incident Checklist

If bidding errors or rejections spike:

1. Check `GET /api/health/`.
2. Open `/dashboard/operations` and inspect rejected bid reasons.
3. Check structured logs by `request_id` and `event=bid_rejected`.
4. Confirm PostgreSQL connectivity and migration status.
5. Confirm Redis connectivity if bid throttling looks abnormal.
6. Check recent deploys and environment variable changes.
7. Review audit logs before taking admin actions.
8. Preserve logs and request IDs for follow-up.

If auction closing or winner calculation fails:

1. Open `/dashboard/operations` and inspect job failures, close runs, and winner calculations.
2. Check structured logs for `event=job_failed`, `event=auction_ended`, and `event=winner_calculated`.
3. Confirm `python manage.py migrate` has run.
4. Run `python manage.py close_expired_auctions --limit 1` in a safe shell and inspect the output.
5. Verify accepted bids exist only in backend `Bid` records and that lot winner fields are not manually edited.
6. Check alert hook delivery status in `alert_triggered` audit logs.

## Production Security Notes

- Set `DJANGO_DEBUG=False`.
- Use a real `DJANGO_SECRET_KEY` from the provider's secret manager.
- Production settings fail fast unless `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, database URL, and frontend/CORS/CSRF origins are configured.
- Keep `SENTRY_DSN`, database URLs, Redis URLs, and object storage secrets in provider secret management.
- Restrict `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS`, and `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Keep HTTPS enabled and set secure cookies in production: `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, and SameSite `Lax` or stricter where safe.
- Keep `DJANGO_SECURE_HSTS_SECONDS`, `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`, and `DJANGO_SECURE_HSTS_PRELOAD` aligned with the deployed HTTPS posture.
- Use `DJANGO_PERMISSIONS_POLICY` and staged `DJANGO_CONTENT_SECURITY_POLICY` / `DJANGO_CONTENT_SECURITY_POLICY_REPORT_ONLY` for secure headers.
- JWT lifetimes are configurable through `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` and `JWT_REFRESH_TOKEN_LIFETIME_DAYS`; refresh rotation and blacklist remain enabled by default.
- Security audit events include login success/failure, logout, token refresh, permission denied, rate-limit triggered, and bid rejection classification events.
- Configure `ENABLE_RATE_LIMITING=True`, `RATE_LIMIT_LOGIN`, `RATE_LIMIT_REGISTRATION`, `RATE_LIMIT_BID_CREATE`, `RATE_LIMIT_PASSWORD_RESET`, and `RATE_LIMIT_ADMIN_ACTIONS`.
- Leave `RATE_LIMIT_BID_CREATE` blank to keep using `BID_RATE_LIMIT_AUTHENTICATED_ATTEMPTS`, `BID_RATE_LIMIT_ANONYMOUS_ATTEMPTS`, and `BID_RATE_LIMIT_WINDOW_SECONDS`; set it only if you want one unified bid-create rate such as `10/minute`.
- Run `python scripts/security_secrets_check.py` before releases to catch obvious committed secrets.
- Do not commit `.env` or cloud secrets to GitHub.
- Keep bid endpoint rate limits enabled and tune them for real auction traffic.
- Enable automated database backups.
- Retain audit logs according to business and legal requirements.
- Use separate staging and production environments.
- See `docs/security-phase-1.md` and `docs/security-runbook.md` for the Secure Startup Platform baseline.

## Operational Notes

- Use `python manage.py seed_demo` only in local or throwaway demo environments.
- Use `python manage.py seed_staging_data` only in staging or explicit non-production environments.
- Use `python manage.py create_staging_admin` in staging when you need an admin account without loading all staging seed data; set `STAGING_ADMIN_PASSWORD` only for that shell/session.
- Keep `BIDALS_ENV=production` on production services so staging seed data cannot be loaded accidentally.
- Review bid logs for repeated `RATE_LIMITED`, `USER_NOT_ALLOWED`, and `UNAUTHENTICATED` events.
- Tune `BID_RATE_LIMIT_AUTHENTICATED_ATTEMPTS` carefully for high-velocity live auctions.
- Schedule `close_expired_auctions` so expired live auctions are finalized promptly.
- Schedule `monitor_bid_anomalies` and tune anomaly thresholds after observing real traffic.
- Schedule `deliver_notifications` only after email settings are configured and tested.
- Treat notification delivery as informational; winner review pages and audit logs remain authoritative.
- Run `backfill_winner_outcomes --dry-run` after deploying Phase 12 to identify legacy winner records needing repair.
- Use `/dashboard/admin/outcome-repairs` only for exceptional finalized outcome corrections after audit review.
- Use `/dashboard/admin/release-check` before releases and after significant incident recovery.
- Run `verify_backup` after provider backup changes and before production releases.
- Keep database backups enabled before running real auctions.
- Use `SERVE_LOCAL_MEDIA=True` only for local/staging image demos when `USE_S3=False`; keep it disabled in production.
- Future uploaded lot media should use object storage, not container disk.

## MVP Limitations

- Image uploads are MVP foundations; production should use object storage and a proper media lifecycle policy.
- Live updates use refresh/polling. WebSockets are intentionally deferred.
- The operations dashboard is intentionally lightweight; full analytics, alert routing, and notification delivery are deferred.
- Auction ending uses management commands suitable for cron/provider schedulers; Celery Beat is still deferred.
- Rate limiting uses Django cache; production should set `USE_REDIS_CACHE=True` so all instances share Redis-backed counters. `deployment_check --production` performs a Redis cache round-trip and fails if Redis is enabled but unreachable.
- CSP is report-only/configurable by default; move to blocking CSP only after production asset/API/media domains are fully known.
- Fulfillment does not include payments, invoices, shipping labels, buyer/seller messaging, or courier integrations.
- The backfill command does not include force-recalculation; already-finalized disputed outcomes need manual admin review.
- Outcome repair approval requires a second admin, but applying an approved repair does not yet require a third distinct admin.
- Admin activity export is CSV-only for the MVP; JSON export and signed archival storage are deferred.
- `deployment_check` is a rollout gate, not a substitute for provider health checks, backups, or human release review.
- `release_check` includes manual `WARN` items because real login, bidding, fulfillment, and repair verification must happen against the deployed environment.
- `verify_backup` confirms database access and operator-recorded backup metadata; it does not perform a destructive restore.
- Notification read state is simple read/unread tracking; preferences and digest controls are deferred.

## Deployment Checklist

- GitHub repository created.
- CI workflow passing on `main`.
- Production env vars configured.
- PostgreSQL provisioned.
- Redis provisioned if needed.
- Backup provider configured and backup metadata recorded.
- Backend deployed.
- Migrations run with `python manage.py migrate`.
- Frontend deployed with `NEXT_PUBLIC_API_BASE_URL` pointing at the backend.
- Backend health check passes.
- Frontend health check passes.
- Login tested.
- Auction creation tested.
- Lot creation tested.
- Valid bid placement tested.
- Rejected bid tested.
- Audit log tested.
- Operations dashboard tested as an admin.
- Staging seed command tested outside production.
- Backup verification command run.
- Release readiness command/UI reviewed.
- Expired auction closing job run tested.
- Winner calculation and reserve/no-bid outcomes tested.
- Bid anomaly monitor run tested.
- Winner review page tested as seller/admin.
- Fulfillment workflow tested as seller/admin.
- Won lots page tested as the winning bidder.
- Backfill repair dry-run and live command tested in staging.
- Account notifications tested as the winning bidder.
- Fulfillment timeline tested as seller/admin and bidder.
- Notification read/unread flow tested.
- Global notification unread badge tested in navigation.
- Admin outcome repair workflow tested through two-admin request/approve, comments, reject, and apply.
- Admin activity export tested as admin.
- Repair audit detail tested as admin.
- `deployment_check --production` tested before production deploy.
- `release_check` tested before production deploy.
- `verify_backup` tested before production deploy.
- Notification delivery command tested with email disabled and configured.
