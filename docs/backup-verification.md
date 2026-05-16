# BIDALS Backup Verification

Backup verification proves that BIDALS data can be recovered without corrupting backend-owned auction truth. It is separate from normal deployment checks and must be completed before production launch.

## Production Backup Baseline

Recommended MVP baseline:

- Managed PostgreSQL backups enabled.
- Daily automated backups at minimum.
- Point-in-time recovery when the provider supports it.
- At least 7 days retention for MVP.
- Longer retention for high-value or regulated auctions.
- Restore rehearsal before production launch and after major schema changes.

Render note: free Render PostgreSQL is not suitable for production backup assurance. Use a paid Render PostgreSQL plan with backups/PITR or another managed PostgreSQL provider with restore support.

## Operator Responsibilities

Before risky migrations or production release, an operator must confirm:

- latest backup exists
- backup timestamp is recorded
- restore test was completed recently
- restore evidence is stored outside the application repo
- rollback target is known

Record safe metadata only:

```text
BACKUP_PROVIDER=render
BACKUP_LAST_VERIFIED_AT=<iso-8601-timestamp>
BACKUP_LAST_RESTORE_TEST_AT=<iso-8601-timestamp>
```

Do not record backup URLs, database URLs, credentials, or private keys.

## Read-Only Verification Command

Run:

```bash
python manage.py backup_verify
```

`backup_verify` is a non-destructive alias for `verify_backup`. It checks:

- database connectivity
- critical BIDALS tables
- configured backup timestamp metadata
- configured restore-test timestamp metadata

It does not perform a restore and does not modify auction, bid, winner, fulfillment, notification, or audit records except for the audit record noting the verification run.

## Restore Into Staging

Preferred workflow:

1. Create a new restore-test PostgreSQL database.
2. Restore the provider backup or `pg_dump` into that database.
3. Point a staging backend at the restored database.
4. Run migrations if needed.
5. Run:

```bash
python manage.py check
python manage.py backup_verify
python manage.py release_check
```

6. Run the release candidate smoke suite against the restored staging URLs.

## Integrity Checks After Restore

Verify:

- users exist with expected roles
- auctions exist
- lots exist
- accepted bid history exists
- rejected bid history exists
- audit logs exist
- lot `current_price` agrees with accepted bids
- winner outcomes are readable
- fulfillment records are readable
- notifications are readable
- admin export works
- invalid bids are still rejected by the backend

## Cadence

- Before production launch.
- Monthly during active auction operations.
- Before major migrations touching auction, lot, bid, outcome, fulfillment, notification, or audit tables.
- After provider backup configuration changes.

## Disaster Recovery

For incident response and restore promotion steps, see [disaster-recovery.md](disaster-recovery.md).
