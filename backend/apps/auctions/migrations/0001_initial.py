# Generated for BIDALS Phase 1.
import decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Auction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("scheduled", "Scheduled"),
                            ("live", "Live"),
                            ("ended", "Ended"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_auctions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-start_time", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="Lot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("images", models.JSONField(blank=True, default=list)),
                (
                    "starting_price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.00"))],
                    ),
                ),
                (
                    "reserve_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.00"))],
                    ),
                ),
                (
                    "current_price",
                    models.DecimalField(
                        decimal_places=2,
                        default=decimal.Decimal("0.00"),
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.00"))],
                    ),
                ),
                (
                    "bid_increment",
                    models.DecimalField(
                        decimal_places=2,
                        default=decimal.Decimal("1.00"),
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("open", "Open"),
                            ("closed", "Closed"),
                            ("sold", "Sold"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "auction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lots",
                        to="auctions.auction",
                    ),
                ),
            ],
            options={
                "ordering": ("auction", "id"),
            },
        ),
        migrations.CreateModel(
            name="Bid",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("status", models.CharField(choices=[("accepted", "Accepted"), ("rejected", "Rejected")], max_length=20)),
                (
                    "rejection_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("AUCTION_NOT_LIVE", "Auction is not live"),
                            ("LOT_CLOSED", "Lot is closed"),
                            ("BID_TOO_LOW", "Bid is too low"),
                            ("INVALID_INCREMENT", "Bid increment is invalid"),
                            ("USER_NOT_ALLOWED", "User is not allowed to bid"),
                            ("SERVER_ERROR", "Server error"),
                        ],
                        max_length=40,
                        null=True,
                    ),
                ),
                ("server_timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "bidder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bids",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "lot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bids",
                        to="auctions.lot",
                    ),
                ),
            ],
            options={
                "ordering": ("-server_timestamp", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="auction",
            index=models.Index(fields=["status", "start_time", "end_time"], name="auction_status_time_idx"),
        ),
        migrations.AddConstraint(
            model_name="auction",
            constraint=models.CheckConstraint(
                condition=models.Q(("end_time__gt", models.F("start_time"))),
                name="auction_end_after_start",
            ),
        ),
        migrations.AddIndex(
            model_name="lot",
            index=models.Index(fields=["auction", "status"], name="lot_auction_status_idx"),
        ),
        migrations.AddIndex(
            model_name="bid",
            index=models.Index(fields=["lot", "-server_timestamp"], name="bid_lot_time_idx"),
        ),
        migrations.AddIndex(
            model_name="bid",
            index=models.Index(fields=["bidder", "-server_timestamp"], name="bid_bidder_time_idx"),
        ),
    ]

