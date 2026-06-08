from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.raffles.models import (
    RaffleCampaign,
    RaffleCampaignStatus,
    RaffleDraw,
    RafflePrize,
    RafflePurchase,
    RaffleTicket,
    RaffleWinner,
)
from apps.raffles.services import seller_has_raffles_enabled


class RafflePrizeSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = RafflePrize
        fields = (
            "id",
            "campaign",
            "title",
            "description",
            "image",
            "image_url",
            "position",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "campaign", "image_url", "created_at", "updated_at")

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        url = obj.image.url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


class RaffleCampaignSerializer(serializers.ModelSerializer):
    auction_title = serializers.CharField(source="auction.title", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    can_purchase = serializers.SerializerMethodField()
    server_now = serializers.SerializerMethodField()
    prizes = RafflePrizeSerializer(many=True, read_only=True)

    class Meta:
        model = RaffleCampaign
        fields = (
            "id",
            "auction",
            "auction_title",
            "title",
            "description",
            "ticket_price",
            "start_time",
            "end_time",
            "draw_time",
            "max_tickets",
            "status",
            "can_purchase",
            "server_now",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "prizes",
        )
        read_only_fields = ("id", "created_by", "created_by_username", "created_at", "updated_at", "prizes")

    def validate(self, attrs):
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        draw_time = attrs.get("draw_time", getattr(self.instance, "draw_time", None))
        max_tickets = attrs.get("max_tickets", getattr(self.instance, "max_tickets", None))
        ticket_price = attrs.get("ticket_price", getattr(self.instance, "ticket_price", None))
        status = attrs.get("status", getattr(self.instance, "status", RaffleCampaignStatus.DRAFT))

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "Raffle end time must be after start time."})
        if end_time and draw_time and draw_time < end_time:
            raise serializers.ValidationError({"draw_time": "Raffle draw time cannot be before end time."})
        if max_tickets is not None and max_tickets <= 0:
            raise serializers.ValidationError({"max_tickets": "Raffle max tickets must be positive."})
        if ticket_price is not None and ticket_price <= Decimal("0.00"):
            raise serializers.ValidationError({"ticket_price": "Ticket price must be positive."})
        if status == RaffleCampaignStatus.DRAWN:
            raise serializers.ValidationError({"status": "Raffle draw status is controlled by the draw engine."})

        return attrs

    def get_can_purchase(self, obj):
        now = self.get_server_now(obj)
        return (
            obj.status == RaffleCampaignStatus.LIVE
            and obj.start_time <= now < obj.end_time
            and seller_has_raffles_enabled(obj.created_by)
        )

    def get_server_now(self, obj):
        server_now = self.context.get("server_now")
        if server_now is None:
            server_now = timezone.now()
            self.context["server_now"] = server_now
        return server_now


class RafflePurchaseSerializer(serializers.ModelSerializer):
    buyer_username = serializers.CharField(source="buyer.username", read_only=True)

    class Meta:
        model = RafflePurchase
        fields = (
            "id",
            "campaign",
            "buyer",
            "buyer_username",
            "quantity",
            "gross_amount",
            "platform_fee_amount",
            "charity_amount",
            "payment_reference",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RaffleTicketSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source="campaign.title", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    purchase_status = serializers.CharField(source="purchase.status", read_only=True)

    class Meta:
        model = RaffleTicket
        fields = (
            "id",
            "campaign",
            "campaign_title",
            "purchase",
            "purchase_status",
            "owner",
            "owner_username",
            "ticket_number",
            "issued_at",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RaffleDrawSerializer(serializers.ModelSerializer):
    drawn_by_username = serializers.CharField(source="drawn_by.username", read_only=True)

    class Meta:
        model = RaffleDraw
        fields = (
            "id",
            "campaign",
            "drawn_by",
            "drawn_by_username",
            "drawn_at",
            "randomness_metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RaffleWinnerSerializer(serializers.ModelSerializer):
    prize_title = serializers.CharField(source="prize.title", read_only=True)
    prize_position = serializers.IntegerField(source="prize.position", read_only=True)
    ticket_number = serializers.IntegerField(source="ticket.ticket_number", read_only=True)
    winner_username = serializers.CharField(source="winner.username", read_only=True)

    class Meta:
        model = RaffleWinner
        fields = (
            "id",
            "campaign",
            "prize",
            "prize_title",
            "prize_position",
            "ticket",
            "ticket_number",
            "winner",
            "winner_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RafflePurchaseCompletionSerializer(serializers.Serializer):
    buyer = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
    gross_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    platform_fee_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
    )
    charity_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    payment_reference = serializers.CharField(required=False, allow_blank=True, max_length=160)


class RaffleCloseSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)
