from django.core.management.base import BaseCommand, CommandError

from apps.audit.services.staging_diagnostics import collect_staging_lifecycle_readiness
from apps.audit.services.staging_lifecycle_repairs import (
    apply_allowed_in_current_environment,
    apply_lifecycle_repairs,
    plan_lifecycle_repairs,
)


class Command(BaseCommand):
    help = "Safely repair selected staging lifecycle data issues. Defaults to dry-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview repairs without writing changes. This is the default.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply repairs. Refuses to run outside staging.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        dry_run = options["dry_run"] or not apply
        if apply and options["dry_run"]:
            raise CommandError("Use either --dry-run or --apply, not both.")
        if apply and not apply_allowed_in_current_environment():
            raise CommandError(
                "--apply is allowed only when ENVIRONMENT=staging or RENDER_SERVICE_NAME contains 'staging'."
            )

        operations = apply_lifecycle_repairs() if apply else plan_lifecycle_repairs()
        mode = "apply" if apply else "dry-run"
        self.stdout.write(f"staging_repair_lifecycle_issues mode={mode}")
        if dry_run:
            self.stdout.write("No data was modified.")

        for operation in operations:
            self.stdout.write(format_operation(operation))

        planned = sum(1 for operation in operations if operation.status == "planned")
        applied = sum(1 for operation in operations if operation.status == "applied")
        unrepaired = sum(1 for operation in operations if operation.status == "unrepaired")
        skipped = sum(1 for operation in operations if operation.status == "skipped")
        self.stdout.write(
            f"summary planned={planned} applied={applied} unrepaired={unrepaired} skipped={skipped}"
        )

        self.stdout.write("post_repair_readiness:")
        for check in collect_staging_lifecycle_readiness():
            self.stdout.write(f"[{check.status}] {check.name}: {check.message}")

        if not operations:
            self.stdout.write("No repairable lifecycle issues found.")


def format_operation(operation) -> str:
    after = operation.after if operation.after is not None else {}
    return (
        f"- status={operation.status} "
        f"action={operation.action} "
        f"target={operation.target_type}:{operation.target_id} "
        f"reason={operation.reason} "
        f"before={operation.before} "
        f"after={after}"
    )
