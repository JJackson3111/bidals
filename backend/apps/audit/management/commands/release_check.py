from django.core.management.base import BaseCommand, CommandError

from apps.audit.services.readiness import run_release_check


class Command(BaseCommand):
    help = "Generate a BIDALS release readiness report."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-warn",
            action="store_true",
            help="Exit non-zero when warnings are present.",
        )

    def handle(self, *args, **options):
        result = run_release_check()
        self.stdout.write(f"Release readiness report generated at {result['generated_at']} for {result['environment']}.")
        for check in result["checks"]:
            self.stdout.write(f"[{check['status']}] {check['category']} / {check['name']}: {check['message']}")

        failures = result["summary"]["fail"]
        warnings = result["summary"]["warn"]
        if failures or (warnings and options["fail_on_warn"]):
            raise CommandError(f"Release check completed with {failures} failure(s) and {warnings} warning(s).")

        self.stdout.write(self.style.SUCCESS("Release check completed."))
