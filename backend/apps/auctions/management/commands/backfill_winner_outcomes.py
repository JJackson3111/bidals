from django.core.management.base import BaseCommand

from apps.auctions.services.backfill import backfill_winner_outcomes


class Command(BaseCommand):
    help = "Safely backfill missing backend-owned winner outcomes and fulfillment records for ended auctions."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show repairs without writing changes.")
        parser.add_argument("--auction-id", type=int, help="Limit repair to one auction.")
        parser.add_argument("--lot-id", type=int, help="Limit repair to one lot.")

    def handle(self, *args, **options):
        results = backfill_winner_outcomes(
            dry_run=options["dry_run"],
            auction_id=options.get("auction_id"),
            lot_id=options.get("lot_id"),
        )
        repaired = [result for result in results if result.action != "skipped"]
        skipped = [result for result in results if result.action == "skipped"]

        for result in results:
            if result.action == "skipped":
                self.stdout.write(
                    f"SKIP lot={result.lot_id} auction={result.auction_id} reason={result.skipped_reason}"
                )
                continue
            mode = "DRY RUN" if result.dry_run else "REPAIRED"
            self.stdout.write(
                " ".join(
                    (
                        mode,
                        f"lot={result.lot_id}",
                        f"auction={result.auction_id}",
                        f"action={result.action}",
                        f"outcome={result.outcome_status}",
                        f"winner={result.winner_id or 'none'}",
                        f"winning_bid={result.winning_bid_id or 'none'}",
                        f"fulfillment_created={result.fulfillment_created}",
                    )
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete: seen={len(results)} repaired={len(repaired)} skipped={len(skipped)} dry_run={options['dry_run']}"
            )
        )
