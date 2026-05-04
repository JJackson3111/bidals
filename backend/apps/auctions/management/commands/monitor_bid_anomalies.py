from django.core.management.base import BaseCommand

from apps.auctions.services.anomalies import detect_bid_anomalies


class Command(BaseCommand):
    help = "Detect lightweight bid anomalies and trigger configured alert hooks."

    def add_arguments(self, parser):
        parser.add_argument("--window-minutes", type=int, default=60, help="Lookback window for bid anomaly checks.")

    def handle(self, *args, **options):
        anomalies = detect_bid_anomalies(window_minutes=options["window_minutes"])
        self.stdout.write(self.style.SUCCESS(f"Detected {len(anomalies)} new bid anomaly signal(s)."))
        for anomaly in anomalies:
            self.stdout.write(
                f"- {anomaly.anomaly_type}: {anomaly.anomaly_key} count={anomaly.count} "
                f"threshold={anomaly.threshold}"
            )
