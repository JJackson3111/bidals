# BIDALS Demo Environment

This document captures the concise staging/demo setup for BIDALS.

## URLs

- Frontend demo URL: `https://demo.bidals.com`
- Backend staging API URL: `https://bidals-backend-staging.onrender.com`

## Render Environment

Frontend Render environment:

```text
NEXT_PUBLIC_API_BASE_URL=https://bidals-backend-staging.onrender.com
```

Backend Render environment requirements:

```text
ALLOWED_HOSTS=<existing-hosts>,demo.bidals.com,bidals-backend-staging.onrender.com
CORS_ALLOWED_ORIGINS=https://demo.bidals.com
CSRF_TRUSTED_ORIGINS=https://demo.bidals.com
FRONTEND_URL=https://demo.bidals.com
```

## Demo Data

Run the demo seed command on the backend:

```bash
python manage.py seed_demo
```

`seed_demo` creates `[Demo]` premium auction/lots.

## API Checks

Use these endpoints against the backend staging API:

- `/api/auctions/?search=Premium`
- `/api/lots/?auction=<auction_id>`

## Troubleshooting

- Frontend showing no active event usually means wrong `NEXT_PUBLIC_API_BASE_URL` or a stale deploy.
- `DisallowedHost` means `ALLOWED_HOSTS` is missing the Render/backend domain.
- If demo data is missing, rerun `python manage.py seed_demo`.
