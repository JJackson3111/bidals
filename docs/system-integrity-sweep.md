# BIDALS Phase 2 - System Integrity Sweep

## 1. Executive summary

This was an audit and verification sweep of the BIDALS repository at `C:\Dev\bidals`. The repository was clean before the sweep. No application source code was changed. Local development data was seeded with `seed_demo` so the existing smoke/E2E flow could be verified.

The core bid path is in strong shape: `backend/apps/auctions/services/bidding.py::place_bid` is server-authoritative, uses database transactions and row locks, records accepted and rejected bids, and writes audit logs. Auction lifecycle and winner calculation are backend-owned in `backend/apps/auctions/services/lifecycle.py`, use timezone-aware timestamps, and are written to be idempotent. Outcome repair flows in `backend/apps/auctions/services/outcome_repairs.py` are audited and require a second admin approval.

Docker, backend health, migrations, Django checks, backend tests, frontend typecheck/lint, production frontend build, and smoke/E2E all passed after the frontend dev server was restarted. One important operational problem was confirmed: running `npm run build` inside the dev `frontend` compose service shares the same named `.next` volume as the live dev server and can leave the frontend serving missing static chunks until restart.

No critical auction-correctness defect was confirmed. The highest-priority risks are operational/data-safety and governance risks: unguarded demo seeding, frontend `.next` volume contamination from one-off builds, direct Django admin lifecycle edits that may bypass app-level audit paths, bid rate limits failing open when cache is unavailable, and non-blocking dependency audit jobs in CI.

## 2. Commands run and results

| Command | Result |
| --- | --- |
| `git status --short --branch` | Passed. Repo started clean: `## main...origin/main`. |
| `docker compose ps` | Passed. `backend`, `frontend`, `db`, and `redis` were running; Postgres and Redis were healthy. |
| `docker compose up -d --build` | Passed. Used detached mode instead of foreground `docker compose up --build` so the audit could continue. Backend and frontend were rebuilt/recreated. |
| `docker compose ps` after rebuild | Passed. All four services were up; Postgres and Redis healthy. |
| `curl.exe -sS -i http://localhost:8000/api/health/` | Initially returned an empty reply while Django/Next were cold-starting. Retry passed with HTTP 200 and JSON `status: ok`. |
| `curl.exe -sS -i http://localhost:8000/api/health/ready/` | Initially returned an empty reply during startup. Retry passed with HTTP 200; database and cache checks were `ok`. |
| `curl.exe -sS -i http://localhost:3000/api/health` | Initially timed out while Next compiled. Retry passed with HTTP 200. |
| `curl.exe -I http://localhost:3000/` | Initially timed out during Next cold compilation. Retry passed with HTTP 200. |
| `docker compose exec backend python manage.py migrate --check` | Passed. No unapplied migrations. |
| `docker compose exec backend python manage.py makemigrations --check --dry-run` | Passed. `No changes detected`. |
| `docker compose exec backend python manage.py check` | Passed. No system check issues. |
| `docker compose exec backend python manage.py deployment_check` | Passed with expected local-dev warnings: DEBUG, dev SECRET_KEY, local media storage. |
| `docker compose exec backend python manage.py release_check` | Passed with documented warnings for local/dev release readiness items, including backup verification timestamps and manual production flow checks. |
| `docker compose exec backend python manage.py backup_verify` | Passed DB/table checks; warned that backup and restore verification timestamps were not configured. |
| `docker compose run --rm --no-deps frontend npm run typecheck` | Passed. |
| `docker compose run --rm --no-deps frontend npm run lint` | Passed. Warning: `next lint` is deprecated and will be removed in Next.js 16. |
| `docker compose run --rm --no-deps frontend npm run build` | Failed in the dev image. Because `frontend/Dockerfile` sets `NODE_ENV=development`, Next emitted a non-standard NODE_ENV warning and failed prerendering `/404` with `<Html> should not be imported outside of pages/_document`. No `next/document` import was found in app source. |
| `docker compose run --rm --no-deps -e NODE_ENV=production frontend npm run build` | Passed. Production-mode build completed successfully. |
| `docker build --file frontend/Dockerfile.prod --build-arg NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api -t bidals-frontend:integrity-sweep frontend` | Passed. Production frontend Docker build completed. |
| `docker compose run --rm backend pytest -vv --maxfail=1` | Passed. 185 tests passed in 524.73s. 88 warnings, mostly staticfiles path and short dev/CI HMAC key warnings. |
| `docker compose run --rm backend python scripts/security_secrets_check.py` | Could not run in the backend image because the repo-level `scripts/` directory is not present at `/app/scripts`. |
| `C:\Users\joshj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\security_secrets_check.py` | Passed. `No obvious committed secrets found.` |
| `docker compose exec backend python manage.py seed_demo` | Passed. This intentionally mutated only the local dev database so smoke/E2E tests could run. |
| `E2E_SKIP_WEB_SERVER=1 E2E_BASE_URL=http://127.0.0.1:3000 npm.cmd run test:e2e:ci` | First run failed at login after the dev `.next` volume was contaminated by a one-off build. After `docker compose restart frontend`, the rerun passed: 1 Playwright smoke test passed in about 1.2 minutes. |

## 3. Pass/fail table by area

| Area | Status | What was verified |
| --- | --- | --- |
| Environment and Docker integrity | Pass with finding | Compose starts `frontend`, `backend`, `db`, and `redis`; db/redis health checks pass; frontend/backend remain running. Frontend `node_modules` and `.next` are named volumes isolated from the bind mount. Operational issue confirmed for one-off dev builds sharing `frontend_next`. |
| Backend health and Django correctness | Pass | `/api/health/` and `/api/health/ready/` returned 200 after startup. Migrations/checks passed. Dev/prod settings separation was inspected. Production uses `bidals.settings.prod`, required env validation, secure cookies/HSTS, and gunicorn rather than runserver. |
| Bid integrity and lifecycle logic | Pass | `place_bid`, rejection handling, lifecycle sync, scheduled open/close jobs, and winner calculation were inspected. Backend owns bid acceptance, timing, permission checks, and winner outcomes. |
| Audit and admin governance | Pass with findings | Bid acceptance/rejection and lifecycle decisions are audited. Outcome repair is traceable and two-admin approved. Direct Django admin lifecycle/status edits need stronger audit/guard rails. |
| Frontend integrity | Pass with findings | Typecheck/lint passed; production build passed; smoke/E2E passed after restart. Frontend bid UI submits only amount and displays backend results. Browse/landing include demo/display-only logic that does not control bid acceptance. |
| CI and GitHub workflow | Partial pass | `.github/workflows/ci.yml` includes backend, frontend, Docker, security, and E2E jobs with deterministic installs. Dependency audit jobs are non-blocking. Branch protection could not be verified locally, and `docs/engineering-standards.md` is missing. |
| Data safety and seed/demo state | Fail for `seed_demo` guard | Staging reset/seed tools include environment guards and dry-run behavior. `seed_demo` lacks a production/staging guard and creates known demo credentials. No normal docs inspected tell users to delete `bidals_postgres_data`. |
| Security and operational readiness | Pass with findings | No committed secrets found by repo scanner. Production settings require critical env vars. Rate limiting is present but cache failures fail open. Deployment/rollback/DR docs exist, but backup/restore verification timestamps are not configured locally. |

## 4. Critical findings

No critical auction-correctness issue was confirmed in this sweep.

Confirmed non-critical but important risks are listed below. None were changed during this audit.

## 5. High-priority findings

### H1 - Demo seed command is not production-guarded

Confirmed in `backend/apps/auctions/management/commands/seed_demo.py`.

`seed_demo` creates known demo accounts using `DEMO_PASSWORD = "ChangeMe123!"`, clears existing demo data, removes related demo audit logs, and archives legacy public test auctions. Unlike `seed_staging_data.py` and `staging_reset_qa_data.py`, it does not refuse to run in production-like environments.

Risk: a mistaken production or staging invocation could create known-credential accounts and mutate visible auction/demo state.

Recommended fix: add an explicit environment guard similar to staging reset/seed commands. Require local/dev environment or an explicit `--force` with clear warnings. Avoid deleting audit logs where production-like audit retention matters.

### H2 - One-off frontend builds can corrupt the running dev `.next` volume

Confirmed with `docker compose run --rm --no-deps frontend npm run build` followed by smoke/E2E failure.

`docker-compose.yml` mounts `frontend_next:/app/.next` for the running dev server. A one-off build container using the same `frontend` service also writes to that volume. After the dev build command failed, the live frontend served missing `_next/static/...` assets, the login page was unhydrated, and the Playwright smoke test submitted the form as a plain `GET /login?`. Restarting frontend recovered the dev server and the E2E test passed.

Risk: normal verification commands can leave local frontend state broken in a way that looks like an app regression.

Recommended fix: document that production builds must use `frontend/Dockerfile.prod` or a separate compose service/volume, or configure the dev service so `npm run build` does not share the live dev `.next` volume.

### H3 - Direct Django admin lifecycle edits may bypass app-level audit paths

Confirmed by inspecting `backend/apps/auctions/admin.py`, `backend/apps/auctions/views.py`, and lifecycle/audit services.

API updates through `AuctionViewSet.perform_update` create audit entries. Bid and lot outcome fields are mostly read-only in Django admin. However, the Django admin still exposes sensitive auction fields such as status and start/end times without an obvious custom audit hook equivalent to the API/service path.

Risk: staff using Django admin could change lifecycle-defining fields without the same audit trail and validation envelope used by the application.

Recommended fix: either make sensitive lifecycle fields read-only in Django admin and force changes through audited repair/lifecycle APIs, or add explicit admin `save_model` audit entries and validation for status/time changes.

### H4 - Bid/security rate limits fail open if cache is unavailable

Confirmed in `backend/apps/auctions/services/rate_limits.py::check_bid_rate_limit` and `backend/apps/audit/security.py::check_security_rate_limit`.

On cache exceptions, these controls log warnings and allow the request. Database transactions still protect bid correctness, but abuse/throttling controls degrade silently from the user's perspective.

Risk: Redis/cache outages reduce bid endpoint protection during high-pressure auction periods.

Recommended fix: make fail-open/fail-closed behavior environment-configurable. For production bid-sensitive endpoints, consider fail-closed or a database-backed fallback for high-risk actions.

## 6. Medium/low-priority findings

### M1 - CI dependency audits are non-blocking

Confirmed in `.github/workflows/ci.yml`.

The security job runs `pip-audit` and `npm audit`, but both steps use `continue-on-error: true`.

Risk: PRs can pass with known vulnerable dependencies.

Recommended fix: make audits blocking for high/critical findings, or split advisory reporting from a required high-severity gate.

### M2 - `docs/engineering-standards.md` is missing

The requested standards document was not present. Branch protection expectations could not be compared against it.

Recommended fix: restore or add the engineering standards document and include required PR checks, branch protection expectations, release gates, and data safety rules.

### M3 - Platform admins can bid

Confirmed in `backend/apps/auctions/services/bidding.py::_user_can_bid`.

The current policy permits platform admins to bid. This may be intentional for demos/testing, but in a trust-sensitive fundraising auction it should be an explicit governance decision.

Recommended fix: decide whether admins may bid in real auctions. If yes, audit/admin disclosures should make that visible. If no, block it server-side except for local/demo environments.

### M4 - Health endpoint exposes low-sensitivity environment details

Confirmed in `backend/bidals/views.py::health_check`.

The endpoint returns `environment`, `allowed_frontend`, and whether demo seed data is available. This is not a secret, but it is more information than a public liveness endpoint strictly needs.

Recommended fix: keep detailed readiness data for internal checks and return a smaller public health payload in production.

### M5 - Backup/restore verification is documented but not proven in local release checks

Confirmed by `backup_verify` and `release_check`.

The commands warn that `BACKUP_LAST_VERIFIED_AT` and `BACKUP_LAST_RESTORE_TEST_AT` are not configured. Docs in `docs/disaster-recovery.md`, `docs/rollback-runbook.md`, and `docs/production-release-checklist.md` treat backup/restore verification as part of readiness.

Recommended fix: ensure staging/production environments set and update these proof-of-verification variables during release readiness.

### M6 - Frontend lint command is on a deprecated Next path

Confirmed by `docker compose run --rm --no-deps frontend npm run lint`.

`next lint` passed but warned that it will be removed in Next.js 16.

Recommended fix: migrate to the ESLint CLI before the Next 16 upgrade.

### M7 - Landing analytics contains mojibake display text

Confirmed in `frontend/src/components/LandingLiveAnalytics.tsx`.

The visible delta marker uses mojibake text like `â†‘` instead of a clean ASCII/Unicode arrow. This is display-only and does not affect auction integrity.

Recommended fix: replace with a safe display character or ASCII text after the integrity work is complete.

### M8 - Browse page uses display-only demo/fallback metadata

Confirmed in `frontend/src/components/BrowseAuctionsExperience.tsx`.

Browse cards derive demo-style images, stories, impact text, raffle ticket counts, and stats when backend fields are missing. This does not affect real bid acceptance, but it can make browse metrics look more authoritative than the backend data actually is.

Recommended fix: label or remove synthetic display values in production-facing contexts unless the backend explicitly marks them as demo data.

## 7. No-change confirmations

- No source code was changed.
- No Docker volumes were deleted.
- `bidals_postgres_data` was not removed or reset.
- The frontend bind mount does not mask `node_modules` or `.next`; named volumes `frontend_node_modules` and `frontend_next` isolate those paths.
- `frontend/docker-entrypoint.sh` uses a hash of `package-lock.json` and runs `npm ci` when dependencies are missing or stale.
- `frontend/package-lock.json` is present; frontend CI and local install paths use deterministic install commands.
- Backend production settings are separate from dev settings and require key production env vars through `assert_required_production_env()`.
- `docker-compose.prod.yml` uses `bidals.settings.prod` and gunicorn, not Django `runserver`.
- Bid acceptance is server-side in `backend/apps/auctions/services/bidding.py::place_bid`; the frontend sends only the bid amount through `frontend/src/lib/api.ts::placeBid`.
- Accepted and rejected bids are auditable through `AuditLog` entries.
- Winner calculation is backend-owned in `backend/apps/auctions/services/lifecycle.py::_finalise_locked_lot_outcome`.
- Scheduled lifecycle jobs in `open_due_auctions`, `close_due_auctions`, and `sync_auction_lifecycle` are written to be idempotent.
- Outcome repair requests are audited and require two admins through `backend/apps/auctions/services/outcome_repairs.py`.
- Browse and lot UI state is used for user experience only; backend responses drive real bid acceptance and rejection.
- No committed secrets were found by `scripts/security_secrets_check.py`.
- No normal reset/runbook instruction inspected directs users to remove the Postgres named volume.

## 8. Recommended next fixes in order

1. Add a production/staging guard to `seed_demo` and preserve audit retention expectations.
2. Prevent dev `.next` volume contamination by separating production build verification from the running dev compose service.
3. Add audit/validation controls for sensitive Django admin auction and lot lifecycle edits, or make those fields read-only in admin.
4. Decide and implement production behavior for cache/rate-limit outages on bid-sensitive endpoints.
5. Make high/critical dependency audit findings blocking in CI.
6. Restore or create `docs/engineering-standards.md` and align it with required branch protection and CI checks.
7. Formalize the platform-admin bidding policy.
8. Reduce production health endpoint detail if the endpoint is public.
9. Migrate frontend linting away from `next lint`.
10. Clean up display-only frontend issues such as mojibake and unlabeled synthetic browse metadata.

## 9. Items intentionally not changed

- No code fixes were made because this phase was requested as an audit and verification sweep first.
- `seed_demo` was run only to support smoke/E2E verification; no seed logic was changed.
- No Docker volumes were pruned, deleted, or recreated.
- No dependencies were upgraded.
- No CI workflow was modified.
- No branch protection or GitHub repository settings were changed or claimed as verified.

## 10. Risks that require human decision

- Whether platform administrators should ever be allowed to bid in real auctions.
- Whether bid-sensitive endpoints should fail closed when Redis/cache-backed rate limiting is unavailable.
- Whether public health endpoints should expose environment/frontend/demo-seed details in production.
- Whether demo data commands should be allowed outside local development with a force flag, or completely blocked in staging/production.
- What branch protection rules are required, since `docs/engineering-standards.md` was not present for comparison.
- Whether browse-page synthetic/demo display metadata is acceptable in production if backend fields are absent.

## 11. Phase 2A mitigation note

Updated May 27, 2026 after the Phase 2A safety hardening pass.

- H1 mitigated: `seed_demo` now refuses production, requires explicit confirmation for non-local demo/staging use, and remains available for local/dev/CI.
- H2 mitigated: one-off frontend builds in the Docker dev image now use `.next-build` instead of the shared dev `.next` volume, with generated Next config files restored after the build.
- H3 mitigated: Django admin lifecycle/winner-sensitive auction and lot fields are read-only after creation, outcome repair records are view-only in Django admin, destructive deletes are disabled for trust-sensitive admin records, and allowed admin edits are audited.
- H4 mitigated: rate-limit cache failure behavior is explicit. Local development defaults to `allow`; production settings default to `deny`; fail-closed bid/admin paths are covered by tests.
- M1 mitigated for high/critical gating: CI dependency audit steps are blocking, frontend npm audit runs with `--audit-level=high`, and the frontend lockfile was updated to clear the previous high Next.js audit finding. Two moderate frontend advisories remain for follow-up because npm reports only a breaking `--force` path.
