import json

from django.core.management.base import BaseCommand, CommandError

from apps.audit.services.staging_qa_reset import (
    ResetOptions,
    reset_staging_qa_data,
    staging_writes_allowed,
)


class Command(BaseCommand):
    help = "Safely reset old staging QA lifecycle test data. Defaults to dry-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview cleanup without writing changes. This is the default.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply cleanup. Refuses to run outside staging.",
        )
        parser.add_argument(
            "--older-than-days",
            type=int,
            default=30,
            help="Age threshold for stale ended QA/demo cleanup candidates.",
        )
        parser.add_argument(
            "--include-demo",
            action="store_true",
            help="Include current staging demo/baseline auctions in cleanup candidates.",
        )
        parser.add_argument(
            "--hard-delete",
            action="store_true",
            help="Also delete audit-log noise tied directly to deleted QA records.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print machine-readable JSON output.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        dry_run = options["dry_run"] or not apply
        if apply and options["dry_run"]:
            raise CommandError("Use either --dry-run or --apply, not both.")
        if options["older_than_days"] < 0:
            raise CommandError("--older-than-days must be 0 or greater.")
        if apply and not staging_writes_allowed():
            raise CommandError(
                "--apply is allowed only when ENVIRONMENT=staging or RENDER_SERVICE_NAME contains 'staging'."
            )

        result = reset_staging_qa_data(
            options=ResetOptions(
                apply=apply,
                older_than_days=options["older_than_days"],
                include_demo=options["include_demo"],
                hard_delete=options["hard_delete"],
            )
        )
        if options["json"]:
            self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
            return

        self.stdout.write(f"staging_reset_qa_data mode={result['mode']}")
        if dry_run:
            self.stdout.write("No data was modified.")
        self.stdout.write(format_summary("before", result["before"]))
        self.stdout.write(format_summary("planned", result["planned"]))
        self.stdout.write(format_candidates("candidates", result["candidates"]))
        self.stdout.write(format_candidates("protected", result["protected"]))
        self.stdout.write(format_summary("deleted", result["deleted"]))
        self.stdout.write(format_summary("after", result["after"]))
        self.stdout.write("post_reset_readiness:")
        for check in result["readiness"]:
            self.stdout.write(f"[{check['status']}] {check['name']}: {check['message']}")


def format_summary(label: str, summary: dict) -> str:
    fields = " ".join(f"{key}={summary[key]}" for key in sorted(summary))
    return f"{label}: {fields}"


def format_candidates(label: str, candidates: list[dict]) -> str:
    if not candidates:
        return f"{label}: none"
    lines = [f"{label}:"]
    for item in candidates:
        reasons = ",".join(item["reasons"])
        protected_reason = f" protected_reason={item['protected_reason']}" if "protected_reason" in item else ""
        lines.append(
            f"- auction_id={item['id']} title={item['title']} status={item['status']} "
            f"effective_status={item['effective_status']} reasons={reasons}{protected_reason}"
        )
    return "\n".join(lines)
