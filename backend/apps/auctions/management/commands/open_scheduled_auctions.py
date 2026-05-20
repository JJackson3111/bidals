from django.core.management.base import BaseCommand

from apps.auctions.services.lifecycle import open_scheduled_auctions


class Command(BaseCommand):
    help = "Open due scheduled auctions whose server start time has passed."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Maximum number of auctions to process.")

    def handle(self, *args, **options):
        results = open_scheduled_auctions(limit=options.get("limit"))
        due_found = len(results)
        transitioned = sum(1 for result in results if result.transitioned)
        skipped = sum(1 for result in results if not result.transitioned)

        self.stdout.write(
            self.style.SUCCESS(
                f"Due auctions found: {due_found}; opened {transitioned}; skipped {skipped}."
            )
        )
        for result in results:
            self.stdout.write(
                f"- Auction {result.auction_id}: {result.status}, transitioned={result.transitioned}, "
                f"skipped_reason={result.skipped_reason or 'none'}"
            )
