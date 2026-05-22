# BIDALS Demo Reset Runbook

Use this runbook to safely refresh the BIDALS demo environment without changing production data or application code.

## Reset Process

1. Confirm the backend service is deployed from the intended branch or `main`.
   - In Render, open the backend staging service and check the deployed commit/branch.
   - If the branch or commit is wrong, deploy the intended backend revision before seeding.

2. Confirm the frontend points to the staging backend.
   - In the Render frontend service, verify:

```text
NEXT_PUBLIC_API_BASE_URL=https://bidals-backend-staging.onrender.com
```

   - Redeploy the frontend if the value was changed or if the active deploy is stale.

3. Run the demo seed command from the Render backend shell:

```bash
python manage.py seed_demo
```

4. Verify the staging backend API:

```text
https://bidals-backend-staging.onrender.com/api/auctions/?search=Premium
https://bidals-backend-staging.onrender.com/api/lots/?auction=<auction_id>
```

5. Hard refresh the demo auctions page:

```text
https://demo.bidals.com/auctions
```

## Common Failures

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| No active event | Frontend is using the wrong API base URL, or the frontend deploy is stale. | Confirm `NEXT_PUBLIC_API_BASE_URL=https://bidals-backend-staging.onrender.com`, redeploy the frontend, then hard refresh `/auctions`. |
| Unexpected API response shape | Browser or frontend is calling a non-staging backend, old deploy, or wrong endpoint. | Check the Network tab request URL, confirm the backend staging deploy branch/commit, and query the verification URLs directly. |
| `DisallowedHost` | Backend `ALLOWED_HOSTS` is missing the Render/backend domain. | Add `bidals-backend-staging.onrender.com` to backend `ALLOWED_HOSTS`, redeploy, and retry the API check. |
| `count: 0` from API | Demo data is missing, archived, or the wrong backend/database is being queried. | Run `python manage.py seed_demo` on the Render backend shell, then verify `/api/auctions/?search=Premium` again. |
| Wrong backend domain in browser Network tab | Frontend build was created with the wrong `NEXT_PUBLIC_API_BASE_URL`. | Update the frontend Render env var, redeploy the frontend so Next.js rebuilds with the staging backend URL, and hard refresh. |

`seed_demo` creates `[Demo]` premium auction/lots and is safe to rerun for demo refreshes.
