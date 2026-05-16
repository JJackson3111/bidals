# BIDALS Observability

BIDALS observability is intentionally lightweight for MVP production readiness. It focuses on request traceability, audit logs, health checks, bid anomaly signals, and provider-level monitoring.

## Structured Request Logging

When `ENABLE_STRUCTURED_LOGGING=True`, backend logs are JSON. API request logs include safe fields:

- `event`
- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`
- `user_id` when authenticated

The backend preserves inbound `X-Request-ID` or generates one. Responses include `X-Request-ID` so an operator can correlate a browser/API failure with backend logs.

Do not log:

- passwords
- JWTs
- refresh tokens
- database URLs
- Redis URLs
- R2/S3 secrets
- raw authorization headers

## Bid And Security Events

Audit logs and structured logs should be reviewed for:

- `bid_accepted`
- `bid_rejected`
- `bid_rejected_validation`
- `bid_rejected_security`
- `rate_limit_triggered`
- `permission_denied`
- `login_failed`
- `login_success`
- `bid_anomaly_detected`
- `job_failed`

Bid rejection logs classify the reason without moving validation to the frontend. The transactional bidding service remains authoritative.

## Health Endpoints

Public non-sensitive endpoints:

- `GET /health/`: app process is alive.
- `GET /api/health/`: API-compatible alive endpoint kept for existing checks.
- `GET /health/ready/`: database and configured cache readiness.
- `GET /api/health/ready/`: API-compatible readiness endpoint.

Readiness responses include only status and dependency names. They do not expose connection strings, secrets, hostnames, or credentials.

## Render Health Checks

Recommended Render backend health path:

```text
/health/
```

Use `/health/ready/` for a stricter readiness probe where the provider supports dependency-aware health checks. If Redis is enabled and unreachable, readiness returns degraded.

## External Monitoring

Recommended MVP setup:

- Render health checks for backend and frontend.
- Uptime monitor against `/health/`.
- Sentry or equivalent error tracking with `send_default_pii=False`.
- Render log drain or log aggregation for JSON logs.
- Alerting for deploy failures.
- Alerting for sustained 5xx spikes.
- Alerting for repeated login failures.
- Alerting for bid anomaly events.
- Alerting for scheduled job failures.

## Admin Operations Review

Admins should review `/dashboard/operations` after deploys and incidents. It summarizes:

- accepted and rejected bid counts
- repeated failed bidders
- rejected bid reasons
- recent audit activity
- auction close job runs
- winner calculations
- bid anomalies
- alert hook events
- failed notification delivery
- fulfillment status totals

## Deployment Verification

After every deploy:

```bash
python manage.py deployment_check --production
python manage.py release_check
```

Then verify:

- `X-Request-ID` appears on API responses.
- `/health/` returns ok.
- `/health/ready/` returns ok.
- Admin operations dashboard loads.
- Recent smoke-test bid attempts have matching audit entries.
