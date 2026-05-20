from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.auctions.models import (
    Auction,
    AuctionStatus,
    Bid,
    BidStatus,
    FulfillmentRecord,
    FulfillmentStatus,
    Lot,
    LotImage,
    LotStatus,
    OutcomeRepairComment,
    OutcomeRepairRequest,
)
from apps.auctions.services.fulfillment import get_allowed_fulfillment_transitions
from apps.auctions.services.lifecycle import (
    get_auction_closure_reason,
    get_effective_auction_status,
    get_effective_lot_status,
    get_lot_closure_reason,
    is_lot_biddable,
)


def _serializer_server_now(serializer) -> object:
    server_now = serializer.context.get("server_now")
    if server_now is None:
        server_now = timezone.now()
        serializer.context["server_now"] = server_now
    return server_now


class LotImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = LotImage
        fields = ("id", "lot", "image", "image_url", "alt_text", "sort_order", "created_at")
        read_only_fields = fields

    def get_image_url(self, obj):
        if not obj.image:
            return ""

        url = obj.image.url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


class LotImageUploadSerializer(serializers.ModelSerializer):
    ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

    class Meta:
        model = LotImage
        fields = ("image", "alt_text", "sort_order")

    def validate_image(self, image):
        max_size_mb = self.context.get("max_size_mb", 5)
        max_size_bytes = max_size_mb * 1024 * 1024

        if image.size > max_size_bytes:
            raise serializers.ValidationError(f"Image file must be {max_size_mb}MB or smaller.")

        content_type = getattr(image, "content_type", "")
        if content_type and content_type not in self.ALLOWED_IMAGE_CONTENT_TYPES:
            raise serializers.ValidationError("Uploaded file must be a JPG, PNG, WebP, or GIF image.")

        return image


class LotImageOrderItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    sort_order = serializers.IntegerField(min_value=0)


class LotImageReorderSerializer(serializers.Serializer):
    image_order = LotImageOrderItemSerializer(many=True)

    def validate_image_order(self, value):
        image_ids = [item["id"] for item in value]
        if len(image_ids) != len(set(image_ids)):
            raise serializers.ValidationError("Image ids must be unique.")
        return value


class AuctionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    effective_status = serializers.SerializerMethodField()
    server_now = serializers.SerializerMethodField()
    bidding_opens_at = serializers.DateTimeField(source="start_time", read_only=True)
    bidding_closes_at = serializers.DateTimeField(source="end_time", read_only=True)
    can_bid = serializers.SerializerMethodField()
    closure_reason = serializers.SerializerMethodField()

    class Meta:
        model = Auction
        fields = (
            "id",
            "title",
            "description",
            "start_time",
            "end_time",
            "status",
            "effective_status",
            "server_now",
            "bidding_opens_at",
            "bidding_closes_at",
            "can_bid",
            "closure_reason",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_by_username", "created_at", "updated_at")

    def validate(self, attrs):
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        status = attrs.get("status", getattr(self.instance, "status", AuctionStatus.DRAFT))

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "Auction end time must be after start time."})

        now = timezone.now()
        if status in {AuctionStatus.SCHEDULED, AuctionStatus.LIVE} and end_time and end_time <= now:
            raise serializers.ValidationError({"end_time": "Auction end time must stay in the future."})

        if status == AuctionStatus.LIVE and start_time and end_time and not (start_time <= now < end_time):
            raise serializers.ValidationError({"status": "Live auctions must be within their backend bidding window."})

        if self.instance:
            effective_status = get_effective_auction_status(self.instance, now=now)
            timing_updates = {"start_time", "end_time"}.intersection(attrs)
            if effective_status == AuctionStatus.LIVE and timing_updates:
                if "start_time" in attrs and attrs["start_time"] != self.instance.start_time:
                    raise serializers.ValidationError(
                        {"start_time": "Live auction start time cannot be changed."}
                    )
                if "end_time" in attrs:
                    new_end_time = attrs["end_time"]
                    if new_end_time <= now:
                        raise serializers.ValidationError(
                            {"end_time": "Live auction end time cannot be moved into the past."}
                        )
                    if new_end_time < self.instance.end_time:
                        raise serializers.ValidationError(
                            {"end_time": "Live auction end time can only be extended."}
                        )

            if effective_status == AuctionStatus.LIVE and "status" in attrs and attrs["status"] != self.instance.status:
                raise serializers.ValidationError({"status": "Live auction status is controlled by backend lifecycle jobs."})

        return attrs

    def get_effective_status(self, obj):
        return get_effective_auction_status(obj, now=_serializer_server_now(self))

    def get_server_now(self, obj):
        return _serializer_server_now(self)

    def get_can_bid(self, obj):
        return get_effective_auction_status(obj, now=_serializer_server_now(self)) == AuctionStatus.LIVE

    def get_closure_reason(self, obj):
        return get_auction_closure_reason(obj, now=_serializer_server_now(self))


class LotSerializer(serializers.ModelSerializer):
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    auction_status = serializers.CharField(source="auction.status", read_only=True)
    auction_effective_status = serializers.SerializerMethodField()
    effective_status = serializers.SerializerMethodField()
    server_now = serializers.SerializerMethodField()
    bidding_opens_at = serializers.DateTimeField(source="auction.start_time", read_only=True)
    bidding_closes_at = serializers.DateTimeField(source="auction.end_time", read_only=True)
    can_bid = serializers.SerializerMethodField()
    closure_reason = serializers.SerializerMethodField()
    uploaded_images = LotImageSerializer(many=True, read_only=True)
    winner_username = serializers.CharField(source="winner.username", read_only=True)

    class Meta:
        model = Lot
        fields = (
            "id",
            "auction",
            "auction_title",
            "auction_status",
            "auction_effective_status",
            "title",
            "description",
            "images",
            "uploaded_images",
            "starting_price",
            "reserve_price",
            "current_price",
            "bid_increment",
            "status",
            "winner",
            "winner_username",
            "winning_bid",
            "winner_status",
            "winner_calculated_at",
            "effective_status",
            "server_now",
            "bidding_opens_at",
            "bidding_closes_at",
            "can_bid",
            "closure_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "auction_title",
            "auction_status",
            "auction_effective_status",
            "uploaded_images",
            "current_price",
            "winner",
            "winner_username",
            "winning_bid",
            "winner_status",
            "winner_calculated_at",
            "effective_status",
            "server_now",
            "bidding_opens_at",
            "bidding_closes_at",
            "can_bid",
            "closure_reason",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        auction = attrs.get("auction", getattr(self.instance, "auction", None))
        lot_status = attrs.get("status", getattr(self.instance, "status", LotStatus.DRAFT))
        starting_price = attrs.get("starting_price", getattr(self.instance, "starting_price", None))
        reserve_price = attrs.get("reserve_price", getattr(self.instance, "reserve_price", None))
        bid_increment = attrs.get("bid_increment", getattr(self.instance, "bid_increment", None))

        if lot_status == LotStatus.OPEN and auction and auction.status not in {AuctionStatus.SCHEDULED, AuctionStatus.LIVE}:
            raise serializers.ValidationError(
                {
                    "status": (
                        "Lots can only be marked open when the auction is scheduled or live. "
                        "Lots only become bid-open when the auction is live."
                    )
                }
            )

        if starting_price is not None and starting_price < Decimal("0.00"):
            raise serializers.ValidationError({"starting_price": "Starting price must be zero or positive."})

        if reserve_price is not None and starting_price is not None and reserve_price < starting_price:
            raise serializers.ValidationError({"reserve_price": "Reserve price cannot be below starting price."})

        if bid_increment is not None and bid_increment <= Decimal("0.00"):
            raise serializers.ValidationError({"bid_increment": "Bid increment must be positive."})

        immutable_after_bid = {"starting_price", "bid_increment"}
        if self.instance and immutable_after_bid.intersection(attrs):
            has_accepted_bids = self.instance.bids.filter(status=BidStatus.ACCEPTED).exists()
            if has_accepted_bids:
                raise serializers.ValidationError(
                    "Starting price and bid increment cannot be changed after accepted bids exist."
                )

        return attrs

    def get_auction_effective_status(self, obj):
        return get_effective_auction_status(obj.auction, now=_serializer_server_now(self))

    def get_effective_status(self, obj):
        return get_effective_lot_status(obj, now=_serializer_server_now(self))

    def get_server_now(self, obj):
        return _serializer_server_now(self)

    def get_can_bid(self, obj):
        return is_lot_biddable(obj, now=_serializer_server_now(self))

    def get_closure_reason(self, obj):
        return get_lot_closure_reason(obj, now=_serializer_server_now(self))


class BidSerializer(serializers.ModelSerializer):
    bidder_username = serializers.CharField(source="bidder.username", read_only=True)

    class Meta:
        model = Bid
        fields = (
            "id",
            "lot",
            "bidder",
            "bidder_username",
            "amount",
            "status",
            "rejection_reason",
            "server_timestamp",
            "created_at",
        )
        read_only_fields = fields


class BidRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class BidResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("accepted", "rejected"))
    lot_id = serializers.IntegerField()
    bid_id = serializers.IntegerField(required=False)
    reason = serializers.CharField(required=False)
    current_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    server_timestamp = serializers.DateTimeField()


class AuctionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Auction
        fields = ("id", "title", "status", "start_time", "end_time")


class LotSummarySerializer(serializers.ModelSerializer):
    auction = AuctionSummarySerializer(read_only=True)

    class Meta:
        model = Lot
        fields = ("id", "auction", "title", "current_price", "bid_increment", "status")


class LotWinnerReviewSerializer(serializers.ModelSerializer):
    auction_id = serializers.IntegerField(source="auction.id", read_only=True)
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    auction_status = serializers.CharField(source="auction.status", read_only=True)
    auction_end_time = serializers.DateTimeField(source="auction.end_time", read_only=True)
    lot_id = serializers.IntegerField(source="id", read_only=True)
    lot_title = serializers.CharField(source="title", read_only=True)
    lot_status = serializers.CharField(source="status", read_only=True)
    outcome_status = serializers.CharField(source="winner_status", read_only=True)
    winner_id = serializers.IntegerField(source="winner.id", read_only=True, allow_null=True)
    winner_username = serializers.CharField(source="winner.username", read_only=True, allow_null=True)
    winner_email = serializers.EmailField(source="winner.email", read_only=True, allow_null=True)
    winning_bid_id = serializers.IntegerField(source="winning_bid.id", read_only=True, allow_null=True)
    winning_bid_amount = serializers.DecimalField(source="winning_bid.amount", max_digits=12, decimal_places=2, read_only=True, allow_null=True)
    calculated_at = serializers.DateTimeField(source="winner_calculated_at", read_only=True)
    reserve_met = serializers.SerializerMethodField()
    fulfillment_id = serializers.SerializerMethodField()
    fulfillment_status = serializers.SerializerMethodField()

    class Meta:
        model = Lot
        fields = (
            "auction_id",
            "auction_title",
            "auction_status",
            "auction_end_time",
            "lot_id",
            "lot_title",
            "lot_status",
            "outcome_status",
            "winner_id",
            "winner_username",
            "winner_email",
            "winning_bid_id",
            "winning_bid_amount",
            "reserve_price",
            "reserve_met",
            "calculated_at",
            "fulfillment_id",
            "fulfillment_status",
        )
        read_only_fields = fields

    def get_reserve_met(self, obj):
        if obj.reserve_price is None or obj.winning_bid is None:
            return None
        return obj.winning_bid.amount >= obj.reserve_price

    def get_fulfillment_id(self, obj):
        fulfillment = getattr(obj, "fulfillment", None)
        return fulfillment.id if fulfillment else None

    def get_fulfillment_status(self, obj):
        fulfillment = getattr(obj, "fulfillment", None)
        return fulfillment.status if fulfillment else None


class FulfillmentRecordSerializer(serializers.ModelSerializer):
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    lot_title = serializers.CharField(source="lot.title", read_only=True)
    lot_status = serializers.CharField(source="lot.status", read_only=True)
    outcome_status = serializers.CharField(source="lot.winner_status", read_only=True)
    winner_username = serializers.CharField(source="winner.username", read_only=True)
    winner_email = serializers.EmailField(source="winner.email", read_only=True)
    winning_bid_amount = serializers.DecimalField(source="winning_bid.amount", max_digits=12, decimal_places=2, read_only=True)
    allowed_next_statuses = serializers.SerializerMethodField()

    class Meta:
        model = FulfillmentRecord
        fields = (
            "id",
            "auction",
            "auction_title",
            "lot",
            "lot_title",
            "lot_status",
            "outcome_status",
            "winning_bid",
            "winning_bid_amount",
            "winner",
            "winner_username",
            "winner_email",
            "status",
            "confirmation_notes",
            "seller_notes",
            "admin_notes",
            "public_winner_message",
            "allowed_next_statuses",
            "last_follow_up_at",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_allowed_next_statuses(self, obj):
        return list(get_allowed_fulfillment_transitions(obj.status))


class FulfillmentUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=FulfillmentStatus.choices, required=False)
    confirmation_notes = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    seller_notes = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    admin_notes = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    public_winner_message = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one field to update.")
        return attrs


class WonLotSerializer(serializers.ModelSerializer):
    auction_id = serializers.IntegerField(source="auction.id", read_only=True)
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    lot_id = serializers.IntegerField(source="lot.id", read_only=True)
    lot_title = serializers.CharField(source="lot.title", read_only=True)
    outcome_status = serializers.CharField(source="lot.winner_status", read_only=True)
    winning_bid_amount = serializers.DecimalField(source="winning_bid.amount", max_digits=12, decimal_places=2, read_only=True)
    date_won = serializers.DateTimeField(source="lot.winner_calculated_at", read_only=True)
    fulfillment_status = serializers.CharField(source="status", read_only=True)

    class Meta:
        model = FulfillmentRecord
        fields = (
            "id",
            "auction_id",
            "auction_title",
            "lot_id",
            "lot_title",
            "winning_bid",
            "winning_bid_amount",
            "outcome_status",
            "fulfillment_status",
            "public_winner_message",
            "date_won",
            "last_follow_up_at",
            "completed_at",
        )
        read_only_fields = fields


class OutcomeRepairRequestSerializer(serializers.ModelSerializer):
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    lot_title = serializers.CharField(source="lot.title", read_only=True)
    requested_winner_username = serializers.CharField(source="requested_winner.username", read_only=True)
    requested_winning_bid_amount = serializers.DecimalField(source="requested_winning_bid.amount", max_digits=12, decimal_places=2, read_only=True)
    requested_by_username = serializers.CharField(source="requested_by.username", read_only=True)
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)
    applied_by_username = serializers.CharField(source="applied_by.username", read_only=True, allow_null=True)

    class Meta:
        model = OutcomeRepairRequest
        fields = (
            "id",
            "lot",
            "lot_title",
            "auction",
            "auction_title",
            "current_outcome",
            "requested_winning_bid",
            "requested_winning_bid_amount",
            "requested_winner",
            "requested_winner_username",
            "reason",
            "status",
            "requested_by",
            "requested_by_username",
            "reviewed_by",
            "reviewed_by_username",
            "reviewed_at",
            "approval_notes",
            "applied_by",
            "applied_by_username",
            "applied_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OutcomeRepairCreateSerializer(serializers.Serializer):
    lot = serializers.IntegerField(min_value=1)
    requested_winning_bid = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=5000)

    def validate_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A repair reason is required.")
        return value


class OutcomeRepairApproveSerializer(serializers.Serializer):
    approval_notes = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class OutcomeRepairCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = OutcomeRepairComment
        fields = (
            "id",
            "repair_request",
            "author",
            "author_username",
            "comment_text",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OutcomeRepairCommentCreateSerializer(serializers.Serializer):
    comment_text = serializers.CharField(max_length=5000)

    def validate_comment_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A repair comment is required.")
        return value
