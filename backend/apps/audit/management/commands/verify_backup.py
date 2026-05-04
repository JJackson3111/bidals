from django.core.management.base import BaseCommand, CommandError

from apps.audit.services.readiness import run_backup_verification


class Command(BaseCommand):
    help = "Verify BIDALS database backup readiness without running a destructive restore."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-warn",
            action="store_true",
            help="Exit non-zero when warnings are present.",
        )

    def handle(self, *args, **options):
        result = run_backup_verification()
        for check in result["checks"]:
            self.stdout.write(f"[{check['status']}] {check['category']} / {check['name']}: {check['message']}")

        failures = result["summary"]["fail"]
        warnings = result["summary"]["warn"]
        if failures or (warnings and options["fail_on_warn"]):
            raise CommandError(f"Backup verification completed with {failures} failure(s) and {warnings} warning(s).")

        self.stdout.write(self.style.SUCCESS("Backup verification completed."))
