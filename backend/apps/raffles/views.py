from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from apps.raffles.models import (
    RaffleCampaign,
    RaffleCampaignStatus,
    RafflePlanCode,
    RafflePrize,
)
from apps.raffles.permissions import IsRaffleOwnerOrAdminOrReadOnly
from apps.raffles.serializers import (
    RaffleCampaignSerializer,
    RaffleCloseSerializer,
    RaffleDrawSerializer,
    RafflePrizeSerializer,
    RafflePurchaseCompletionSerializer,
    RafflePurchaseSerializer,
    RaffleTicketSerializer,
    RaffleWinnerSerializer,
)
from apps.raffles.services import (
    RaffleError,
    RaffleFeatureDisabledError,
    RafflePermissionError,
    close_raffle,
    complete_purchase_and_issue_tickets,
    create_campaign,
    create_prize,
    execute_draw,
    read_user_tickets,
    read_winners,
    update_campaign,
)

User = get_user_model()

PUBLIC_RAFFLE_STATUSES = (
    RaffleCampaignStatus.SCHEDULED,
    RaffleCampaignStatus.LIVE,
    RaffleCampaignStatus.CLOSED,
    RaffleCampaignStatus.DRAWN,
)


class RaffleCampaignViewSet(viewsets.ModelViewSet):
    serializer_class = RaffleCampaignSerializer
    permission_classes = (IsRaffleOwnerOrAdminOrReadOnly,)
    http_method_names = ("get", "post", "patch", "head", "options")

    def get_queryset(self):
        queryset = (
            RaffleCampaign.objects.select_related("auction", "created_by")
            .prefetch_related("prizes")
            .all()
        )
        user = self.request.user

        if user.is_authenticated and user.is_platform_admin:
            visible = queryset
        elif user.is_authenticated and user.can_sell:
            visible = queryset.filter(created_by=user)
        else:
            visible = queryset.filter(
                status__in=PUBLIC_RAFFLE_STATUSES,
            ).filter(_enabled_seller_filter())

        auction_id = self.request.query_params.get("auction")
        if auction_id:
            visible = visible.filter(auction_id=auction_id)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            visible = visible.filter(status=status_filter)

        return visible

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            campaign = create_campaign(actor=request.user, data=serializer.validated_data)
        except (RaffleError, IntegrityError) as exc:
            _raise_drf_raffle_error(exc)
        return Response(self.get_serializer(campaign).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        campaign = self.get_object()
        serializer = self.get_serializer(campaign, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            campaign = update_campaign(
                actor=request.user,
                campaign_id=campaign.id,
                data=serializer.validated_data,
            )
        except (RaffleError, IntegrityError) as exc:
            _raise_drf_raffle_error(exc)
        return Response(self.get_serializer(campaign).data)

    @action(detail=True, methods=("get", "post"), permission_classes=(IsRaffleOwnerOrAdminOrReadOnly,))
    def prizes(self, request, pk=None):
        campaign = self.get_object()
        if request.method == "GET":
            prizes = RafflePrize.objects.filter(campaign=campaign).order_by("position", "id")
            return Response(RafflePrizeSerializer(prizes, many=True, context={"request": request}).data)

        serializer = RafflePrizeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            prize = create_prize(
                actor=request.user,
                campaign_id=campaign.id,
                data=serializer.validated_data,
            )
        except (RaffleError, IntegrityError) as exc:
            _raise_drf_raffle_error(exc)
        return Response(
            RafflePrizeSerializer(prize, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=("post",), permission_classes=(IsAuthenticated,))
    def close(self, request, pk=None):
        campaign = self.get_object()
        serializer = RaffleCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            campaign = close_raffle(
                actor=request.user,
                campaign_id=campaign.id,
                comment=serializer.validated_data.get("comment", ""),
            )
        except RaffleError as exc:
            _raise_drf_raffle_error(exc)
        return Response(self.get_serializer(campaign).data)

    @action(detail=True, methods=("post",), permission_classes=(IsAuthenticated,))
    def draw(self, request, pk=None):
        campaign = self.get_object()
        try:
            result = execute_draw(actor=request.user, campaign_id=campaign.id)
        except (RaffleError, IntegrityError) as exc:
            _raise_drf_raffle_error(exc)
        return Response(
            {
                "draw": RaffleDrawSerializer(result.draw).data,
                "winners": RaffleWinnerSerializer(result.winners, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=("get",))
    def winners(self, request, pk=None):
        campaign = self.get_object()
        winners = read_winners(campaign_id=campaign.id)
        return Response({"results": RaffleWinnerSerializer(winners, many=True).data})

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(IsAuthenticated, IsAdminRole),
        url_path="purchase-completions",
    )
    def purchase_completions(self, request, pk=None):
        campaign = self.get_object()
        serializer = RafflePurchaseCompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            buyer = User.objects.get(pk=serializer.validated_data["buyer"])
        except User.DoesNotExist as exc:
            raise NotFound("Buyer not found.") from exc

        try:
            result = complete_purchase_and_issue_tickets(
                actor=request.user,
                campaign_id=campaign.id,
                buyer=buyer,
                quantity=serializer.validated_data["quantity"],
                gross_amount=serializer.validated_data.get("gross_amount"),
                platform_fee_amount=serializer.validated_data.get("platform_fee_amount"),
                charity_amount=serializer.validated_data.get("charity_amount"),
                payment_reference=serializer.validated_data.get("payment_reference", ""),
            )
        except (RaffleError, IntegrityError) as exc:
            _raise_drf_raffle_error(exc)

        return Response(
            {
                "purchase": RafflePurchaseSerializer(result.purchase).data,
                "tickets": RaffleTicketSerializer(result.tickets, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MyRaffleTicketsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        campaign_id = request.query_params.get("campaign")
        tickets = read_user_tickets(
            user=request.user,
            campaign_id=int(campaign_id) if campaign_id else None,
        )
        return Response({"results": RaffleTicketSerializer(tickets, many=True).data})


def _enabled_seller_filter():
    return Q(created_by__raffle_feature__raffles_enabled=True) | Q(
        created_by__raffle_feature__plan_code=RafflePlanCode.SIGNATURE
    )


def _raise_drf_raffle_error(exc: Exception) -> None:
    if isinstance(exc, (RafflePermissionError, RaffleFeatureDisabledError)):
        raise PermissionDenied(str(exc)) from exc
    if isinstance(exc, IntegrityError):
        raise ValidationError({"detail": "Raffle operation could not be completed because it would violate data integrity."}) from exc
    raise ValidationError({"detail": str(exc)}) from exc
