import json

from django.core.management.base import BaseCommand, CommandError

from apps.audit.services.staging_qa_reset import seed_staging_qa_baseline, staging_writes_allowed


class Command(BaseCommand):
    help = "Create a clean staging QA baseline auction, lots, seller, and bidders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print machine-readable JSON output.",
        )

    def handle(self, *args, **options):
        if not staging_writes_allowed():
            raise CommandError(
                "seed_staging_qa_baseline is allowed only when ENVIRONMENT=staging "
                "or RENDER_SERVICE_NAME contains 'staging'."
            )

        result = seed_staging_qa_baseline()
        if options["json"]:
            self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
            return

        self.stdout.write("seed_staging_qa_baseline")
        self.stdout.write(f"auction_id={result['auction_id']} title={result['auction_title']}")
        self.stdout.write(f"lot_ids={','.join(str(value) for value in result['lot_ids'])}")
        self.stdout.write(
            f"seller={result['seller']['email']} bidders="
            f"{','.join(item['email'] for item in result['bidders'])}"
        )
        self.stdout.write(f"password={result['password']}")
        self.stdout.write("post_seed_readiness:")
        for check in result["readiness"]:
            self.stdout.write(f"[{check['status']}] {check['name']}: {check['message']}")
