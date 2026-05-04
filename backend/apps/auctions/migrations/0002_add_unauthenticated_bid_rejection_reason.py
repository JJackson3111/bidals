# Generated for BIDALS Phase 2.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("auctions", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bid",
            name="rejection_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("AUCTION_NOT_LIVE", "Auction is not live"),
                    ("LOT_CLOSED", "Lot is closed"),
                    ("BID_TOO_LOW", "Bid is too low"),
                    ("INVALID_INCREMENT", "Bid increment is invalid"),
                    ("USER_NOT_ALLOWED", "User is not allowed to bid"),
                    ("UNAUTHENTICATED", "User is not authenticated"),
                    ("SERVER_ERROR", "Server error"),
                ],
                max_length=40,
                null=True,
            ),
        ),
    ]

