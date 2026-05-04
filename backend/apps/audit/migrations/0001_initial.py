# Generated for BIDALS Phase 1.
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
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("user_registered", "User registered"),
                            ("auction_created", "Auction created"),
                            ("auction_updated", "Auction updated"),
                            ("auction_ended", "Auction ended"),
                            ("lot_created", "Lot created"),
                            ("lot_updated", "Lot updated"),
                            ("bid_accepted", "Bid accepted"),
                            ("bid_rejected", "Bid rejected"),
                            ("winner_calculated", "Winner calculated"),
                            ("admin_action", "Admin action"),
                        ],
                        max_length=60,
                    ),
                ),
                ("entity_type", models.CharField(max_length=60)),
                ("entity_id", models.CharField(max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("server_timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-server_timestamp", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["entity_type", "entity_id"], name="audit_entity_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["action", "-server_timestamp"], name="audit_action_time_idx"),
        ),
    ]

