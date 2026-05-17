# BIDALS Security Phase 1

Phase 1 security hardening turns BIDALS into a safer startup platform baseline. It does not change the server-authoritative bidding engine, winner calculation, fulfillment state, or repair workflow truth model.

## Implemented Controls

### Production Configuration

- Production settings fail fast when critical environment variables are missing.
- `DEBUG` is forced off in `bidals.settings.prod`.
- `DJANGO_ALLOWED_HOSTS`, CORS origins, and CSRF trusted origins are environment driven.
- Wildcard CORS is rejected in production.
- Secure cookies are enabled in production:
  - `SESSION_COOKIE_SECURE=True`
  - `CSRF_COOKIE_SECURE=True`
  - `SESSION_COOKIE_HTTPONLY=True`
  - `CSRF_COOKIE_HTTPONLY=True` by default in production
  - SameSite defaults to `Lax`
- HSTS, SSL redirect, referrer policy, permissions policy, and staged CSP headers are configurable.

### Authentication

- JWT access/refresh lifetimes are environment configurable.
- Refresh-token rotation and blacklist-after-rotation remain enabled by default.
- Login success, login failure, logout, and token refresh events are audit logged.
- Passwords, refresh tokens, access tokens, authorization headers, and secrets are not written to audit metadata.

### Access Control

- Admin-only and seller-only APIs remain server-side enforced.
- Permission failures on DRF API endpoints create `permission_denied` audit records.
- Sensitive admin actions can be rate limited through `RATE_LIMIT_ADMIN_ACTIONS`.

### Audit Logging

Security-focused audit event types include:

- `login_success`
- `login_failed`
- `logout`
- `token_refresh`
- `permission_denied`
- `rate_limit_triggered`
- `bid_rejected_security`
- `bid_rejected_validation`

Existing bid audit events are preserved:

- `bid_accepted`
- `bid_rejected`

Rejected bids now keep the original `bid_rejected` audit event and add a security or validation classification event where appropriate.

### Rate Limiting

Rate limiting uses Django cache. Production should use Redis with `USE_REDIS_CACHE=True`.

Configured controls:

- `RATE_LIMIT_LOGIN`
- `RATE_LIMIT_REGISTRATION`
- `RATE_LIMIT_BID_CREATE`
- `RATE_LIMIT_PASSWORD_RESET`
- `RATE_LIMIT_ADMIN_ACTIONS`

`RATE_LIMIT_BID_CREATE` is optional. Leave it blank/unset to keep using the bid-specific throttle settings: `BID_RATE_LIMIT_AUTHENTICATED_ATTEMPTS`, `BID_RATE_LIMIT_ANONYMOUS_ATTEMPTS`, and `BID_RATE_LIMIT_WINDOW_SECONDS`.

Bid rate limiting remains an abuse-prevention layer only. The transactional bidding service still validates auction status, server time, lot status, bidder permissions, increments, current price, and row-locked concurrency.

### API and Upload Safety

- Lot image uploads validate size and allowed image content types.
- Public APIs cannot set privileged fields exposed as read-only serializer fields.
- Error responses remain controlled by DRF and do not expose stack traces in production.

### Secure Headers

Implemented or confirmed:

- `X-Content-Type-Options`
- `X-Frame-Options`
- `Referrer-Policy`
- `Permissions-Policy`
- Optional staged `Content-Security-Policy-Report-Only`

Use report-only CSP first. Do not move to blocking CSP until frontend asset, API, image, and deployment domains are fully enumerated.

### Dependency and Secret Checks

- CI includes an obvious secret-pattern scan.
- CI includes Python and npm dependency audit steps as advisory checks.
- Docker build checks remain in CI.

## Required Production Environment Variables

Critical:

- `DJANGO_SETTINGS_MODULE=bidals.settings.prod`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL` or `DJANGO_DATABASE_URL`
- `FRONTEND_URL`, `DJANGO_CORS_ALLOWED_ORIGINS`, or `CORS_ALLOWED_ORIGINS`
- `FRONTEND_URL`, `DJANGO_CSRF_TRUSTED_ORIGINS`, or `CSRF_TRUSTED_ORIGINS`

Recommended security settings:

- `DJANGO_SECURE_SSL_REDIRECT=True`
- `DJANGO_SECURE_HSTS_SECONDS=31536000`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
- `DJANGO_SECURE_HSTS_PRELOAD=True`
- `DJANGO_CSRF_COOKIE_HTTPONLY=True`
- `DJANGO_SESSION_COOKIE_SAMESITE=Lax`
- `DJANGO_CSRF_COOKIE_SAMESITE=Lax`
- `DJANGO_REFERRER_POLICY=same-origin`
- `DJANGO_PERMISSIONS_POLICY=camera=(), microphone=(), geolocation=(), payment=()`

Rate limiting:

- `ENABLE_RATE_LIMITING=True`
- `USE_REDIS_CACHE=True`
- `REDIS_URL`
- `RATE_LIMIT_LOGIN=5/minute`
- `RATE_LIMIT_REGISTRATION=5/minute`
- `RATE_LIMIT_BID_CREATE=` to use bid-specific throttle settings, or set a unified value such as `10/minute`
- `RATE_LIMIT_PASSWORD_RESET=3/hour`
- `RATE_LIMIT_ADMIN_ACTIONS=30/minute`

JWT:

- `JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15`
- `JWT_REFRESH_TOKEN_LIFETIME_DAYS=7`
- `JWT_ROTATE_REFRESH_TOKENS=True`
- `JWT_BLACKLIST_AFTER_ROTATION=True`

## Known Remaining Gaps

- Password reset/change flows are not fully implemented yet, so their audit events are reserved but not emitted.
- CSP is report-only/configurable by default to avoid breaking the current frontend until all external domains are known.
- This phase is a technical security baseline, not ISO 27001 or SOC 2 certification.

## Recommended Security Phase 2

- Add account lockout or progressive delay after repeated failed login attempts.
- Add a reviewed admin role change workflow with explicit `user_role_changed` auditing.
- Add formal CSP reporting and tune a blocking CSP.
- Add object-level permission tests for every admin/governance endpoint.
- Add scheduled secret-rotation and dependency-review runbooks.
