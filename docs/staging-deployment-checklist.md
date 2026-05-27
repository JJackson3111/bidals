# BIDALS Staging Deployment Checklist

Use this checklist for BIDALS demo/staging deploys.

## Before Deploy

- [ ] Confirm the branch or commit intended for staging/demo.
- [ ] Confirm backend tests pass.
- [ ] Confirm frontend checks/build pass.
- [ ] Confirm backend environment variables are set for staging, including `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and `FRONTEND_URL`.
- [ ] Confirm frontend environment variables are set for staging, especially `NEXT_PUBLIC_API_BASE_URL`.
- [ ] Confirm there are no accidental `MobileNav` or navigation CSS changes unless those changes are intended for this deploy.

## Deploy

- [ ] Deploy the backend first.
- [ ] Confirm the backend deploy completed successfully.
- [ ] Deploy the frontend second.
- [ ] Clear the frontend build cache only when env/build issues happen.
- [ ] Run demo seed after backend deploy if demo data is required:

```bash
python manage.py seed_demo \
  --allow-non-local \
  --confirm-known-demo-credentials="I understand seed_demo creates known demo credentials"
```

## Verify

- [ ] Backend health responds:

```text
https://bidals-backend-staging.onrender.com/api/health/
```

- [ ] Premium auction search returns the demo event:

```text
https://bidals-backend-staging.onrender.com/api/auctions/?search=Premium
```

- [ ] Lots load for the demo auction:

```text
https://bidals-backend-staging.onrender.com/api/lots/?auction=<auction_id>
```

- [ ] Demo auctions page loads:

```text
https://demo.bidals.com/auctions
```

- [ ] Login works.
- [ ] Bid placement works.
- [ ] Refreshing nested routes works.
- [ ] Mobile view works and navigation is usable.

## Rollback

- [ ] Use the stable demo tag as the rollback reference:

```text
demo-stable-v1
```

- [ ] Redeploy the last known good backend commit.
- [ ] Redeploy the last known good frontend commit.
- [ ] Re-run the verification checklist after rollback.
