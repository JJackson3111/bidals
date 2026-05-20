# Staging Render Diagnostics

Use these checks when a command exists locally but does not appear in the Render shell. Do not print or copy secrets, database URLs, Redis URLs, API tokens, or credentials into tickets or docs.

## Safe Fingerprint Command

Run this locally from the backend directory:

```bash
python manage.py deployment_fingerprint
```

Run this in the Render shell for the backend web service and for every scheduled job service:

```bash
cd /app && python manage.py deployment_fingerprint
```

The output should show the same expected commit or branch, the same installed `apps.auctions` and `apps.audit` apps, and `True` for both command files:

- `staging_env_diagnostics.py`
- `staging_lifecycle_readiness.py`

If Render only lists old management commands, compare this output with the latest Git commit on the expected branch.

## Render Service Checks

In the Render dashboard, confirm the backend web service:

- Uses the expected repository.
- Uses the expected branch, currently `tighten-seller-browse-isolation` if validating this diagnostics branch.
- Shows the latest deployed commit SHA matching the GitHub branch head.
- Uses the correct root directory or build context. For BIDALS this should include the `backend` source that contains `apps/audit/management/commands`.
- Uses the intended Dockerfile path for the backend image, normally `backend/Dockerfile` when the service root is the repository root.
- Has auto deploy enabled if commits should deploy automatically.
- If deploying manually, the manual deploy is triggered after the latest commit has reached the configured Render branch.
- Is not pinned to an old image, old commit, or old branch.

For scheduled job services, confirm each job:

- Uses the same repository as the backend web service.
- Uses the same branch as the backend web service.
- Deploys the same commit SHA as the backend web service.
- Uses the same root directory or build context as the backend image.
- Uses the same Dockerfile path and image source as the backend service.
- Runs with the same copied environment group/secrets as the backend, without printing those values.
- Uses `/app/scripts/run_scheduled_job.sh` or the deployed backend image rather than an older one-off command image.

## Expected Follow-Up

After Render deploys the correct commit, run:

```bash
cd /app && python manage.py help | grep -E 'staging|diagnostics|lifecycle|fingerprint'
cd /app && python manage.py staging_env_diagnostics
cd /app && python manage.py staging_lifecycle_readiness
```

If `grep` is unavailable in the shell, run:

```bash
cd /app && python manage.py deployment_fingerprint
```
