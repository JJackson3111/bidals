from django.core.management.base import BaseCommand

from apps.audit.services.staging_diagnostics import collect_staging_lifecycle_readiness


class Command(BaseCommand):
    help = "Run read-only BIDALS staging lifecycle readiness checks."

    def handle(self, *args, **options):
        checks = collect_staging_lifecycle_readiness()

        self.stdout.write("staging_lifecycle_readiness")
        for check in checks:
            self.stdout.write(f"[{check.status}] {check.name}: {check.message}")

        failures = sum(1 for check in checks if check.status == "FAIL")
        warnings = sum(1 for check in checks if check.status == "WARN")
        passes = sum(1 for check in checks if check.status == "PASS")
        self.stdout.write(f"summary: pass={passes} warn={warnings} fail={failures}")
