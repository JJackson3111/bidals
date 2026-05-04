import apps.auctions.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("auctions", "0003_add_rate_limited_bid_rejection_reason"),
    ]

    operations = [
        migrations.CreateModel(
            name="LotImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "image",
                    models.FileField(
                        upload_to=apps.auctions.models.lot_image_upload_path,
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                allowed_extensions=("jpg", "jpeg", "png", "webp", "gif")
                            )
                        ],
                    ),
                ),
                ("alt_text", models.CharField(blank=True, max_length=180)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "lot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="uploaded_images",
                        to="auctions.lot",
                    ),
                ),
            ],
            options={
                "ordering": ("sort_order", "id"),
                "indexes": [
                    models.Index(fields=["lot", "sort_order"], name="lot_image_order_idx"),
                ],
            },
        ),
    ]
