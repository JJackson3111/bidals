from django.core.management.base import BaseCommand

from apps.auctions.services.notifications import deliver_pending_notifications


class Command(BaseCommand):
    help = "Deliver pending BIDALS outbound notifications when email delivery is configured."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Maximum pending notifications to process.")

    def handle(self, *args, **options):
        result = deliver_pending_notifications(limit=options["limit"])
        self.stdout.write(
            self.style.SUCCESS(
                "Notification delivery run: "
                f"seen={result['seen']} sent={result['sent']} skipped={result['skipped']} failed={result['failed']}"
            )
        )
