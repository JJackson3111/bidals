from decimal import Decimal
from pathlib import Path
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class AuctionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    LIVE = "live", "Live"
    ENDED = "ended", "Ended"
    CANCELLED = "cancelled", "Cancelled"


class LotStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    SOLD = "sold", "Sold"
    CANCELLED = "cancelled", "Cancelled"


class LotWinnerStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    WINNER_ASSIGNED = "winner_assigned", "Winner assigned"
    NO_BIDS = "no_bids", "No bids"
    RESERVE_NOT_MET = "reserve_not_met", "Reserve not met"


class FulfillmentStatus(models.TextChoices):
    PENDING_CONFIRMATION = "pending_confirmation", "Pending confirmation"
    WINNER_CONFIRMED = "winner_confirmed", "Winner confirmed"
    SELLER_CONTACTED = "seller_contacted", "Seller contacted"
    AWAITING_COLLECTION_OR_DELIVERY = "awaiting_collection_or_delivery", "Awaiting collection or delivery"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    DISPUTED = "disputed", "Disputed"


class OutcomeRepairStatus(models.TextChoices):
    PENDING_REVIEW = "pending_review", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    APPLIED = "applied", "Applied"
    CANCELLED = "cancelled", "Cancelled"


class BidStatus(models.TextChoices):
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class BidRejectionReason(models.TextChoices):
    AUCTION_NOT_LIVE = "AUCTION_NOT_LIVE", "Auction is not live"
    LOT_CLOSED = "LOT_CLOSED", "Lot is closed"
    BID_TOO_LOW = "BID_TOO_LOW", "Bid is too low"
    INVALID_INCREMENT = "INVALID_INCREMENT", "Bid increment is invalid"
    USER_NOT_ALLOWED = "USER_NOT_ALLOWED", "User is not allowed to bid"
    UNAUTHENTICATED = "UNAUTHENTICATED", "User is not authenticated"
    RATE_LIMITED = "RATE_LIMITED", "Bidder is rate limited"
    SERVER_ERROR = "SERVER_ERROR", "Server error"


class Auction(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=AuctionStatus.choices,
        default=AuctionStatus.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_auctions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_time", "-created_at")
        indexes = [
            models.Index(fields=("status", "start_time", "end_time"), name="auction_status_time_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="auction_end_after_start",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError({"end_time": "Auction end time must be after start time."})

    def is_live_at(self, timestamp=None) -> bool:
        timestamp = timestamp or timezone.now()
        return (
            self.status == AuctionStatus.LIVE
            and self.start_time <= timestamp
            and self.end_time > timestamp
        )


class Lot(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="lots")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    images = models.JSONField(default=list, blank=True)
    starting_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    reserve_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    current_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    bid_increment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(
        max_length=20,
        choices=LotStatus.choices,
        default=LotStatus.DRAFT,
    )
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="won_lots",
        blank=True,
        null=True,
    )
    winning_bid = models.OneToOneField(
        "auctions.Bid",
        on_delete=models.SET_NULL,
        related_name="winning_lot",
        blank=True,
        null=True,
    )
    winner_status = models.CharField(
        max_length=30,
        choices=LotWinnerStatus.choices,
        default=LotWinnerStatus.PENDING,
    )
    winner_calculated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("auction", "id")
        indexes = [
            models.Index(fields=("auction", "status"), name="lot_auction_status_idx"),
            models.Index(fields=("winner_status", "winner_calculated_at"), name="lot_winner_status_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        if self.reserve_price is not None and self.reserve_price < self.starting_price:
            raise ValidationError({"reserve_price": "Reserve price cannot be below starting price."})

    def save(self, *args, **kwargs):
        if self._state.adding and self.current_price == Decimal("0.00"):
            self.current_price = self.starting_price
        super().save(*args, **kwargs)


def lot_image_upload_path(instance, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return f"lot-images/{instance.lot_id}/{uuid.uuid4().hex}{extension}"


class LotImage(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="uploaded_images")
    image = models.FileField(
        upload_to=lot_image_upload_path,
        validators=[
            FileExtensionValidator(allowed_extensions=("jpg", "jpeg", "png", "webp", "gif")),
        ],
    )
    alt_text = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")
        indexes = [
            models.Index(fields=("lot", "sort_order"), name="lot_image_order_idx"),
        ]

    def __str__(self) -> str:
        return f"Image for {self.lot}"


class Bid(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="bids")
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bids",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=BidStatus.choices)
    rejection_reason = models.CharField(
        max_length=40,
        choices=BidRejectionReason.choices,
        blank=True,
        null=True,
    )
    server_timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-server_timestamp", "-id")
        indexes = [
            models.Index(fields=("lot", "-server_timestamp"), name="bid_lot_time_idx"),
            models.Index(fields=("bidder", "-server_timestamp"), name="bid_bidder_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.bidder} bid {self.amount} on {self.lot}"


class FulfillmentRecord(models.Model):
    lot = models.OneToOneField(Lot, on_delete=models.CASCADE, related_name="fulfillment")
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="fulfillment_records")
    winning_bid = models.ForeignKey(
        Bid,
        on_delete=models.PROTECT,
        related_name="fulfillment_records",
    )
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fulfillment_records",
    )
    status = models.CharField(
        max_length=40,
        choices=FulfillmentStatus.choices,
        default=FulfillmentStatus.PENDING_CONFIRMATION,
    )
    confirmation_notes = models.TextField(blank=True)
    seller_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    public_winner_message = models.TextField(blank=True)
    last_follow_up_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        indexes = [
            models.Index(fields=("status", "-updated_at"), name="fulfillment_status_idx"),
            models.Index(fields=("winner", "-updated_at"), name="fulfillment_winner_idx"),
            models.Index(fields=("auction", "status"), name="fulfillment_auction_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Fulfillment for {self.lot}"


class OutcomeRepairRequest(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, related_name="outcome_repair_requests")
    auction = models.ForeignKey(Auction, on_delete=models.PROTECT, related_name="outcome_repair_requests")
    current_outcome = models.CharField(max_length=30, choices=LotWinnerStatus.choices)
    requested_winning_bid = models.ForeignKey(
        Bid,
        on_delete=models.PROTECT,
        related_name="requested_outcome_repairs",
    )
    requested_winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_outcome_repairs_as_winner",
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=OutcomeRepairStatus.choices,
        default=OutcomeRepairStatus.PENDING_REVIEW,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="outcome_repairs_requested",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="outcome_repairs_reviewed",
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    approval_notes = models.TextField(blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="outcome_repairs_applied",
        blank=True,
        null=True,
    )
    applied_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("status", "-created_at"), name="repair_status_created_idx"),
            models.Index(fields=("lot", "status"), name="repair_lot_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Repair request {self.id} for {self.lot}"


class OutcomeRepairComment(models.Model):
    repair_request = models.ForeignKey(
        OutcomeRepairRequest,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="outcome_repair_comments",
    )
    comment_text = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=("repair_request", "created_at"), name="repair_comment_time_idx"),
        ]

    def __str__(self) -> str:
        return f"Comment {self.id} on repair {self.repair_request_id}"
