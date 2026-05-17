# BIDALS Security Runbook

Use this after deploys, security-sensitive changes, or suspicious activity.

## Post-Deploy Security Checks

1. Confirm production settings:
   ```bash
   python manage.py deployment_check --production
   ```
2. Confirm `DEBUG=False` in the deployment environment.
3. Confirm `DJANGO_ALLOWED_HOSTS` contains only deployed backend hosts.
4. Confirm `DJANGO_CORS_ALLOWED_ORIGINS` or `CORS_ALLOWED_ORIGINS` contains only deployed frontend origins.
5. Confirm `DJANGO_CSRF_TRUSTED_ORIGINS` or `CSRF_TRUSTED_ORIGINS` contains only trusted HTTPS origins.
6. Confirm `USE_REDIS_CACHE=True` and Redis passes `deployment_check --production`.
7. Confirm `USE_S3=True` for production media storage.
8. Confirm `/api/health/` returns `{"status":"ok"}`.

## Confirm Rate Limiting

Login:

1. Set a temporary staging-only low limit, for example `RATE_LIMIT_LOGIN=1/minute`.
2. Make two failed login attempts.
3. Confirm the second response is HTTP `429`.
4. Confirm an audit log exists with `action=rate_limit_triggered`.

Bidding:

1. Set a temporary staging-only low limit, for example `RATE_LIMIT_BID_CREATE=1/minute`.
2. Place one valid bid.
3. Attempt a second bid in the same minute.
4. Confirm the second response is HTTP `429`.
5. Confirm the lot price only changed after the accepted bid.

Reset staging limits after testing.

## Review Audit Logs

In Django admin or the admin audit API, review:

- `login_failed`
- `login_success`
- `logout`
- `token_refresh`
- `permission_denied`
- `rate_limit_triggered`
- `bid_rejected_security`
- `bid_rejected_validation`
- `bid_accepted`
- `bid_rejected`

Audit metadata should include request path, method, client IP, user agent, request ID, actor ID, and actor role where available. It should not include passwords, tokens, authorization headers, or secrets.

## Suspicious Login Activity

1. Check recent `login_failed` and `rate_limit_triggered` events.
2. Check client IP and user agent clustering.
3. Temporarily lower `RATE_LIMIT_LOGIN` if abuse is active.
4. Rotate affected user passwords if account compromise is suspected.
5. Rotate `DJANGO_SECRET_KEY` only as a planned incident response because it can invalidate sessions/tokens.

## Suspicious Bidding Activity

1. Check `bid_rejected_security`, `bid_rejected_validation`, and `rate_limit_triggered` events.
2. Confirm Redis is healthy so bid throttling is shared across instances.
3. Confirm the transactional bidding tests pass before redeploying any bidding-related change.
4. Do not manually edit accepted bid history.
5. Use admin repair workflows only for audited outcome correction, never for normal winner calculation.

## Rotate Secrets

1. Generate a replacement secret in the provider secret manager.
2. Update the environment variable without committing it.
3. Redeploy the affected services.
4. Run:
   ```bash
   python manage.py deployment_check --production
   python manage.py release_check
   ```
5. Confirm login, bid placement, audit logs, scheduled jobs, Redis, and object storage.

## Dependency and Secret Scans

Run locally when needed:

```bash
python scripts/security_secrets_check.py
```

CI also runs advisory dependency audits. Treat high-confidence critical findings as release blockers.
