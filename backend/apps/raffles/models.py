from decimal import Decimal
from pathlib import Path
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class RafflePlanCode(models.TextChoices):
    ESSENTIALS = "essentials", "Essentials"
    SIGNATURE = "signature", "Signature"
    CUSTOM = "custom", "Custom"


class RaffleCampaignStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    LIVE = "live", "Live"
    CLOSED = "closed", "Closed"
    DRAWN = "drawn", "Drawn"
    CANCELLED = "cancelled", "Cancelled"


class RafflePurchaseStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class RaffleTicketStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    VOID = "void", "Void"


class SellerRaffleFeature(models.Model):
    seller = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="raffle_feature",
    )
    plan_code = models.CharField(
        max_length=30,
        choices=RafflePlanCode.choices,
        default=RafflePlanCode.ESSENTIALS,
    )
    raffles_enabled = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("seller_id",)
        indexes = [
            models.Index(fields=("plan_code", "raffles_enabled"), name="raffle_feature_plan_idx"),
        ]

    def __str__(self) -> str:
        return f"Raffle features for {self.seller}"

    @property
    def has_raffles(self) -> bool:
        return self.raffles_enabled or self.plan_code == RafflePlanCode.SIGNATURE


class ImmutableAfterCreateMixin:
    immutable_fields: tuple[str, ...] = ()

    def _assert_immutable_fields_unchanged(self) -> None:
        if self._state.adding or not self.pk:
            return

        existing = type(self).objects.get(pk=self.pk)
        changed_fields = [
            field
            for field in self.immutable_fields
            if getattr(existing, field) != getattr(self, field)
        ]
        if changed_fields:
            raise ValidationError(
                {
                    field: "This field is immutable after creation."
                    for field in changed_fields
                }
            )


class RaffleCampaign(models.Model):
    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.PROTECT,
        related_name="raffle_campaigns",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    ticket_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    draw_time = models.DateTimeField()
    max_tickets = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=RaffleCampaignStatus.choices,
        default=RaffleCampaignStatus.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_raffle_campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_time", "-created_at")
        indexes = [
            models.Index(fields=("status", "start_time", "end_time"), name="raffle_campaign_time_idx"),
            models.Index(fields=("auction", "status"), name="raffle_campaign_auction_idx"),
            models.Index(fields=("created_by", "status"), name="raffle_campaign_owner_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="raffle_end_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(draw_time__gte=models.F("end_time")),
                name="raffle_draw_after_end",
            ),
            models.CheckConstraint(
                condition=models.Q(max_tickets__gt=0),
                name="raffle_max_tickets_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError({"end_time": "Raffle end time must be after start time."})
        if self.draw_time < self.end_time:
            raise ValidationError({"draw_time": "Raffle draw time cannot be before end time."})
        if self.max_tickets <= 0:
            raise ValidationError({"max_tickets": "Raffle max tickets must be positive."})

    def is_live_at(self, timestamp=None) -> bool:
        timestamp = timestamp or timezone.now()
        return (
            self.status == RaffleCampaignStatus.LIVE
            and self.start_time <= timestamp
            and self.end_time > timestamp
        )


def raffle_prize_upload_path(instance, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return f"raffle-prizes/{instance.campaign_id}/{uuid.uuid4().hex}{extension}"


class RafflePrize(models.Model):
    campaign = models.ForeignKey(RaffleCampaign, on_delete=models.CASCADE, related_name="prizes")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    image = models.FileField(
        upload_to=raffle_prize_upload_path,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=("jpg", "jpeg", "png", "webp", "gif")),
        ],
    )
    position = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("campaign", "position", "id")
        indexes = [
            models.Index(fields=("campaign", "position"), name="raffle_prize_order_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=("campaign", "position"), name="raffle_prize_position_unique"),
            models.CheckConstraint(condition=models.Q(position__gt=0), name="raffle_prize_position_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.position}. {self.title}"


class RafflePurchase(models.Model):
    campaign = models.ForeignKey(RaffleCampaign, on_delete=models.PROTECT, related_name="purchases")
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="raffle_purchases",
    )
    quantity = models.PositiveIntegerField()
    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    platform_fee_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    charity_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    payment_reference = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=20,
        choices=RafflePurchaseStatus.choices,
        default=RafflePurchaseStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("campaign", "status"), name="raffle_purchase_campaign_idx"),
            models.Index(fields=("buyer", "-created_at"), name="raffle_purchase_buyer_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="raffle_purchase_qty_positive"),
            models.CheckConstraint(condition=models.Q(gross_amount__gte=0), name="raffle_purchase_gross_nonneg"),
            models.CheckConstraint(condition=models.Q(platform_fee_amount__gte=0), name="raffle_purchase_fee_nonneg"),
            models.CheckConstraint(condition=models.Q(charity_amount__gte=0), name="raffle_purchase_charity_nonneg"),
        ]

    def __str__(self) -> str:
        return f"Raffle purchase {self.id} for {self.campaign}"

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({"quantity": "Ticket quantity must be positive."})
        if self.gross_amount != self.platform_fee_amount + self.charity_amount:
            raise ValidationError({"gross_amount": "Gross amount must equal platform fee plus charity amount."})


class RaffleTicket(ImmutableAfterCreateMixin, models.Model):
    immutable_fields = ("campaign_id", "purchase_id", "owner_id", "ticket_number")

    campaign = models.ForeignKey(RaffleCampaign, on_delete=models.PROTECT, related_name="tickets")
    purchase = models.ForeignKey(RafflePurchase, on_delete=models.PROTECT, related_name="tickets")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="raffle_tickets",
    )
    ticket_number = models.PositiveIntegerField()
    issued_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=RaffleTicketStatus.choices,
        default=RaffleTicketStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("campaign", "ticket_number", "id")
        indexes = [
            models.Index(fields=("owner", "-issued_at"), name="raffle_ticket_owner_idx"),
            models.Index(fields=("campaign", "status"), name="raffle_ticket_campaign_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=("campaign", "ticket_number"), name="raffle_ticket_number_unique"),
            models.CheckConstraint(condition=models.Q(ticket_number__gt=0), name="raffle_ticket_number_positive"),
        ]

    def __str__(self) -> str:
        return f"Ticket {self.ticket_number} for {self.campaign}"

    def clean(self):
        if self.purchase_id and self.campaign_id and self.purchase.campaign_id != self.campaign_id:
            raise ValidationError({"purchase": "Ticket purchase must belong to the same raffle campaign."})
        if self.purchase_id and self.owner_id and self.purchase.buyer_id != self.owner_id:
            raise ValidationError({"owner": "Ticket owner must match the purchase buyer."})
        if self.status == RaffleTicketStatus.ACTIVE and self.purchase_id:
            if self.purchase.status != RafflePurchaseStatus.COMPLETED:
                raise ValidationError({"status": "Active tickets can only be issued for completed purchases."})

    def save(self, *args, **kwargs):
        self._assert_immutable_fields_unchanged()
        self.clean()
        super().save(*args, **kwargs)


class RaffleDraw(ImmutableAfterCreateMixin, models.Model):
    immutable_fields = ("campaign_id", "drawn_by_id", "drawn_at", "randomness_metadata")

    campaign = models.OneToOneField(RaffleCampaign, on_delete=models.PROTECT, related_name="draw")
    drawn_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="raffle_draws_executed",
    )
    drawn_at = models.DateTimeField(default=timezone.now)
    randomness_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-drawn_at", "-id")
        indexes = [
            models.Index(fields=("drawn_by", "-drawn_at"), name="raffle_draw_actor_idx"),
        ]

    def __str__(self) -> str:
        return f"Draw for {self.campaign}"

    def save(self, *args, **kwargs):
        self._assert_immutable_fields_unchanged()
        super().save(*args, **kwargs)


class RaffleWinner(ImmutableAfterCreateMixin, models.Model):
    immutable_fields = ("campaign_id", "prize_id", "ticket_id", "winner_id")

    campaign = models.ForeignKey(RaffleCampaign, on_delete=models.PROTECT, related_name="winners")
    prize = models.ForeignKey(RafflePrize, on_delete=models.PROTECT, related_name="winners")
    ticket = models.OneToOneField(RaffleTicket, on_delete=models.PROTECT, related_name="winner_record")
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="raffle_wins",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("campaign", "prize__position", "id")
        indexes = [
            models.Index(fields=("winner", "-created_at"), name="raffle_winner_user_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=("campaign", "prize"), name="raffle_winner_prize_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.winner} won {self.prize}"

    def clean(self):
        if self.prize_id and self.campaign_id and self.prize.campaign_id != self.campaign_id:
            raise ValidationError({"prize": "Winning prize must belong to the raffle campaign."})
        if self.ticket_id and self.campaign_id and self.ticket.campaign_id != self.campaign_id:
            raise ValidationError({"ticket": "Winning ticket must belong to the raffle campaign."})
        if self.ticket_id and self.winner_id and self.ticket.owner_id != self.winner_id:
            raise ValidationError({"winner": "Winner must match the winning ticket owner."})
        if self.ticket_id and self.ticket.status != RaffleTicketStatus.ACTIVE:
            raise ValidationError({"ticket": "Winning ticket must be active."})

    def save(self, *args, **kwargs):
        self._assert_immutable_fields_unchanged()
        self.clean()
        super().save(*args, **kwargs)
