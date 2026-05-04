from django.core.management.base import BaseCommand

from apps.auctions.services.closing import close_expired_auctions


class Command(BaseCommand):
    help = "Close expired live auctions and calculate lot winners using server-side data."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Maximum number of auctions to process.")

    def handle(self, *args, **options):
        results = close_expired_auctions(limit=options.get("limit"))
        transitioned = sum(1 for result in results if result.transitioned)
        lots_processed = sum(result.lots_processed for result in results)

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(results)} auction(s); ended {transitioned}; calculated {lots_processed} lot result(s)."
            )
        )
        for result in results:
            self.stdout.write(
                f"- Auction {result.auction_id}: {result.status}, transitioned={result.transitioned}, "
                f"lots_processed={result.lots_processed}"
            )
