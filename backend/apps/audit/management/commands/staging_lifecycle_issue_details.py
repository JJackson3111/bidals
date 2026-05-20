import json

from django.core.management.base import BaseCommand

from apps.audit.services.staging_diagnostics import collect_staging_lifecycle_issue_details


class Command(BaseCommand):
    help = "Print read-only staging lifecycle issue record details without modifying data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print machine-readable JSON output.",
        )

    def handle(self, *args, **options):
        result = collect_staging_lifecycle_issue_details()

        if options["json"]:
            self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
            return

        self.stdout.write("staging_lifecycle_issue_details")
        self.stdout.write(f"generated_at={result['generated_at']}")
        summary = result["summary"]
        self.stdout.write(
            "summary "
            f"inconsistent_lots={summary['inconsistent_lots']} "
            f"closed_lots_in_live_auctions={summary['closed_lots_in_live_auctions']} "
            f"live_lots_in_closed_auctions={summary['live_lots_in_closed_auctions']} "
            f"auctions_start_after_end={summary['auctions_start_after_end']}"
        )

        self.stdout.write("lot_issues:")
        if not result["lot_issues"]:
            self.stdout.write("- none")
        for issue in result["lot_issues"]:
            self.stdout.write(format_lot_issue(issue))

        self.stdout.write("auction_issues:")
        if not result["auction_issues"]:
            self.stdout.write("- none")
        for issue in result["auction_issues"]:
            self.stdout.write(format_auction_issue(issue))

        if result["errors"]:
            self.stdout.write("errors:")
            for error in result["errors"]:
                self.stdout.write(f"- section={error['section']} error_type={error['error_type']}")


def format_lot_issue(issue: dict) -> str:
    return (
        f"- reasons={','.join(issue['reasons'])} "
        f"auction_id={issue['auction_id']} "
        f"auction_title={issue['auction_title']} "
        f"auction_status={issue['auction_status']} "
        f"auction_effective_status={issue['auction_effective_status']} "
        f"auction_start_time={issue['auction_start_time']} "
        f"auction_end_time={issue['auction_end_time']} "
        f"lot_id={issue['lot_id']} "
        f"lot_title={issue['lot_title']} "
        f"lot_status={issue['lot_status']} "
        f"lot_effective_status={issue['lot_effective_status']} "
        f"current_price={issue['current_price']} "
        f"winning_bid_id={issue['winning_bid_id']} "
        f"winner_id={issue['winner_id']} "
        f"winner_email={issue['winner_email']} "
        f"winner_status={issue['winner_status']} "
        f"bid_count={issue['bid_count']} "
        f"created_at={issue['created_at']} "
        f"updated_at={issue['updated_at']} "
        f"auction_created_at={issue['auction_created_at']} "
        f"auction_updated_at={issue['auction_updated_at']}"
    )


def format_auction_issue(issue: dict) -> str:
    return (
        f"- reasons={','.join(issue['reasons'])} "
        f"auction_id={issue['auction_id']} "
        f"auction_title={issue['auction_title']} "
        f"auction_status={issue['auction_status']} "
        f"auction_effective_status={issue['auction_effective_status']} "
        f"auction_start_time={issue['auction_start_time']} "
        f"auction_end_time={issue['auction_end_time']} "
        f"created_at={issue['created_at']} "
        f"updated_at={issue['updated_at']}"
    )
