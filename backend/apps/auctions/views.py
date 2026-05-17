import logging
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from apps.audit.models import AuditAction, AuditLog
from apps.audit.security import (
    audit_security_event,
    check_security_rate_limit,
    client_ip,
    rate_limited_response,
    request_audit_metadata,
)
from apps.audit.serializers import AuditLogSerializer, SafeAuditLogSerializer
from apps.auctions.models import (
    Auction,
    AuctionStatus,
    Bid,
    BidRejectionReason,
    BidStatus,
    FulfillmentRecord,
    Lot,
    LotImage,
    LotStatus,
    OutcomeRepairComment,
    OutcomeRepairRequest,
)
from apps.auctions.permissions import (
    IsAuctionOwnerOrAdminOrReadOnly,
    IsLotOwnerOrAdminOrReadOnly,
)
from apps.auctions.serializers import (
    AuctionSerializer,
    BidRequestSerializer,
    BidResultSerializer,
    BidSerializer,
    FulfillmentRecordSerializer,
    FulfillmentUpdateSerializer,
    LotImageReorderSerializer,
    LotImageSerializer,
    LotImageUploadSerializer,
    LotSerializer,
    LotWinnerReviewSerializer,
    OutcomeRepairApproveSerializer,
    OutcomeRepairCommentCreateSerializer,
    OutcomeRepairCommentSerializer,
    OutcomeRepairCreateSerializer,
    OutcomeRepairRequestSerializer,
    WonLotSerializer,
)
from apps.auctions.services.bidding import place_bid
from apps.auctions.services.fulfillment import FulfillmentTransitionError, update_fulfillment_record
from apps.auctions.services.outcome_repairs import (
    OutcomeRepairError,
    apply_outcome_repair,
    approve_outcome_repair,
    create_outcome_repair_comment,
    create_outcome_repair_request,
    reject_outcome_repair,
)
from apps.auctions.services.rate_limits import check_bid_rate_limit
from apps.auctions.services.timeline import fulfillment_timeline, serialize_timeline_event

logger = logging.getLogger(__name__)

VISIBLE_AUCTION_STATUSES = (
    AuctionStatus.SCHEDULED,
    AuctionStatus.LIVE,
    AuctionStatus.ENDED,
)
VISIBLE_LOT_STATUSES = (
    LotStatus.OPEN,
    LotStatus.CLOSED,
    LotStatus.SOLD,
)


def _parse_datetime_query_param(value: str | None, field_name: str):
    if not value:
        return None

    parsed = parse_datetime(value)
    if parsed is None:
        raise ValidationError({field_name: "Use an ISO-8601 datetime."})

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _ensure_can_manage_lot_images(*, user, lot: Lot) -> None:
    if not (user and user.is_authenticated and (user.is_platform_admin or lot.auction.created_by_id == user.id)):
        raise PermissionDenied("Only the auction owner or an admin can manage lot images.")


def _admin_action_rate_limit_response(request, scope: str):
    rate_limit = check_security_rate_limit(
        request,
        scope=scope,
        identifier=str(request.user.id) if request.user.is_authenticated else client_ip(request),
        setting_name="RATE_LIMIT_ADMIN_ACTIONS",
        default_rate="30/minute",
        actor=request.user if request.user.is_authenticated else None,
    )
    if not rate_limit.allowed:
        return rate_limited_response(rate_limit)
    return None


def _ensure_local_media_root_available() -> None:
    if settings.USE_S3:
        return

    try:
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.exception(
            "Lot image media root is not writable",
            extra={
                "event": "lot_image_storage_unavailable",
                "media_root": str(settings.MEDIA_ROOT),
            },
        )
        raise ValidationError(
            {
                "image": [
                    "Image storage is not available. Configure a writable MEDIA_ROOT for staging "
                    "or enable object storage for production."
                ]
            }
        ) from exc


def _winner_review_queryset_for_user(user):
    if not (user and user.is_authenticated and user.can_sell):
        raise PermissionDenied("Only sellers and admins can review auction outcomes.")

    queryset = (
        Lot.objects.select_related("auction", "auction__created_by", "winner", "winning_bid")
        .filter(winner_calculated_at__isnull=False)
        .order_by("-auction__end_time", "auction_id", "id")
    )
    if user.is_platform_admin:
        return queryset
    return queryset.filter(auction__created_by=user)


def _winner_summary(lots) -> dict:
    return {
        "total_lots": len(lots),
        "winner_assigned": sum(1 for lot in lots if lot.winner_status == "winner_assigned"),
        "no_bids": sum(1 for lot in lots if lot.winner_status == "no_bids"),
        "reserve_not_met": sum(1 for lot in lots if lot.winner_status == "reserve_not_met"),
    }


def _fulfillment_queryset_for_user(user):
    if not (user and user.is_authenticated and user.can_sell):
        raise PermissionDenied("Only sellers and admins can manage fulfillment.")

    queryset = FulfillmentRecord.objects.select_related(
        "auction",
        "auction__created_by",
        "lot",
        "winner",
        "winning_bid",
    ).order_by("-updated_at", "-id")
    if user.is_platform_admin:
        return queryset
    return queryset.filter(auction__created_by=user)


def _fulfillment_summary(records) -> dict:
    statuses = (
        "pending_confirmation",
        "winner_confirmed",
        "seller_contacted",
        "awaiting_collection_or_delivery",
        "completed",
        "cancelled",
        "disputed",
    )
    return {
        "total": len(records),
        **{status: sum(1 for record in records if record.status == status) for status in statuses},
    }


class WinnerReviewView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        lots = _winner_review_queryset_for_user(request.user)

        outcome_status = request.query_params.get("outcome_status")
        if outcome_status:
            lots = lots.filter(winner_status=outcome_status)

        auction_id = request.query_params.get("auction")
        if auction_id:
            lots = lots.filter(auction_id=auction_id)

        lots_list = list(lots[:200])
        return Response(
            {
                "summary": _winner_summary(lots_list),
                "results": LotWinnerReviewSerializer(lots_list, many=True).data,
            }
        )


class FulfillmentListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        records = _fulfillment_queryset_for_user(request.user)

        status_filter = request.query_params.get("status")
        if status_filter:
            records = records.filter(status=status_filter)

        search = request.query_params.get("search")
        if search:
            records = records.filter(
                Q(auction__title__icontains=search)
                | Q(lot__title__icontains=search)
                | Q(winner__username__icontains=search)
                | Q(winner__email__icontains=search)
            )

        records_list = list(records[:200])
        return Response(
            {
                "summary": _fulfillment_summary(records_list),
                "results": FulfillmentRecordSerializer(records_list, many=True).data,
            }
        )


class FulfillmentDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request, pk):
        record = _fulfillment_queryset_for_user(request.user).filter(pk=pk).first()
        if record is None:
            raise NotFound("Fulfillment record not found.")

        serializer = FulfillmentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = update_fulfillment_record(
                record_id=record.id,
                actor=request.user,
                updates=serializer.validated_data,
            )
        except FulfillmentTransitionError as exc:
            raise ValidationError(
                {
                    "status": str(exc),
                    "old_status": exc.old_status,
                    "attempted_status": exc.new_status,
                    "allowed_statuses": list(exc.allowed_statuses),
                }
            ) from exc
        return Response(FulfillmentRecordSerializer(result.record).data)


class FulfillmentTimelineView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        record = _fulfillment_queryset_for_user(request.user).filter(pk=pk).first()
        if record is None:
            raise NotFound("Fulfillment record not found.")

        events = [
            serialize_timeline_event(log, public=False)
            for log in fulfillment_timeline(record, public=False)
        ]
        return Response({"results": events})


class WonLotsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        records = (
            FulfillmentRecord.objects.select_related("auction", "lot", "winning_bid", "winner")
            .filter(winner=request.user)
            .order_by("-lot__winner_calculated_at", "-id")
        )
        return Response(
            {
                "results": WonLotSerializer(records, many=True).data,
            }
        )


class WonLotTimelineView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        record = (
            FulfillmentRecord.objects.select_related("auction", "lot", "winning_bid", "winner")
            .filter(pk=pk, winner=request.user)
            .first()
        )
        if record is None:
            raise NotFound("Won lot not found.")

        events = [
            serialize_timeline_event(log, public=True)
            for log in fulfillment_timeline(record, public=True)
        ]
        return Response({"results": events})


class OutcomeRepairListView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get(self, request):
        repairs = OutcomeRepairRequest.objects.select_related(
            "auction",
            "lot",
            "requested_winning_bid",
            "requested_winner",
            "requested_by",
            "reviewed_by",
            "applied_by",
        ).order_by("-created_at", "-id")
        status_filter = request.query_params.get("status")
        if status_filter:
            repairs = repairs.filter(status=status_filter)
        lot_id = request.query_params.get("lot")
        if lot_id:
            repairs = repairs.filter(lot_id=lot_id)
        return Response({"results": OutcomeRepairRequestSerializer(repairs[:200], many=True).data})

    def post(self, request):
        limited = _admin_action_rate_limit_response(request, "outcome_repair_create")
        if limited is not None:
            return limited

        serializer = OutcomeRepairCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            repair = create_outcome_repair_request(
                actor=request.user,
                lot_id=serializer.validated_data["lot"],
                requested_winning_bid_id=serializer.validated_data["requested_winning_bid"],
                reason=serializer.validated_data["reason"],
            )
        except (Lot.DoesNotExist, Bid.DoesNotExist) as exc:
            raise NotFound("Lot or bid not found.") from exc
        except OutcomeRepairError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(OutcomeRepairRequestSerializer(repair).data, status=status.HTTP_201_CREATED)


class OutcomeRepairDetailView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get(self, request, pk):
        repair = _get_repair(pk)
        return Response(OutcomeRepairRequestSerializer(repair).data)


class OutcomeRepairActionView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)
    action_name = ""

    def post(self, request, pk):
        limited = _admin_action_rate_limit_response(request, f"outcome_repair_{self.action_name}")
        if limited is not None:
            return limited

        try:
            if self.action_name == "approve":
                serializer = OutcomeRepairApproveSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                repair = approve_outcome_repair(
                    repair_id=pk,
                    actor=request.user,
                    approval_notes=serializer.validated_data.get("approval_notes", ""),
                )
            elif self.action_name == "reject":
                repair = reject_outcome_repair(repair_id=pk, actor=request.user)
            elif self.action_name == "apply":
                repair = apply_outcome_repair(repair_id=pk, actor=request.user).repair
            else:
                raise ValidationError({"detail": "Unknown repair action."})
        except OutcomeRepairRequest.DoesNotExist as exc:
            raise NotFound("Outcome repair request not found.") from exc
        except OutcomeRepairError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(OutcomeRepairRequestSerializer(repair).data)


class OutcomeRepairCommentsView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get(self, request, pk):
        _get_repair(pk)
        comments = (
            OutcomeRepairComment.objects.select_related("author")
            .filter(repair_request_id=pk)
            .order_by("created_at", "id")
        )
        return Response({"results": OutcomeRepairCommentSerializer(comments, many=True).data})

    def post(self, request, pk):
        limited = _admin_action_rate_limit_response(request, "outcome_repair_comment")
        if limited is not None:
            return limited

        serializer = OutcomeRepairCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            comment = create_outcome_repair_comment(
                repair_id=pk,
                actor=request.user,
                comment_text=serializer.validated_data["comment_text"],
            )
        except OutcomeRepairRequest.DoesNotExist as exc:
            raise NotFound("Outcome repair request not found.") from exc
        except OutcomeRepairError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(OutcomeRepairCommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class OutcomeRepairAuditView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get(self, request, pk):
        limited = _admin_action_rate_limit_response(request, "outcome_repair_audit")
        if limited is not None:
            return limited

        repair = _get_repair(pk)
        events = list(_repair_audit_queryset(repair))
        AuditLog.objects.create(
            actor=request.user,
            action=AuditAction.OUTCOME_REPAIR_AUDIT_VIEWED,
            entity_type="outcome_repair",
            entity_id=str(repair.id),
            metadata={
                "repair_id": repair.id,
                "auction_id": repair.auction_id,
                "lot_id": repair.lot_id,
                "actor_id": request.user.id,
                "request_id": getattr(request, "request_id", None),
            },
        )
        return Response({"results": SafeAuditLogSerializer(events, many=True).data})


def _get_repair(pk):
    try:
        return OutcomeRepairRequest.objects.select_related(
            "auction",
            "lot",
            "requested_winning_bid",
            "requested_winner",
            "requested_by",
            "reviewed_by",
            "applied_by",
        ).get(pk=pk)
    except OutcomeRepairRequest.DoesNotExist as exc:
        raise NotFound("Outcome repair request not found.") from exc


def _repair_audit_queryset(repair: OutcomeRepairRequest):
    return (
        AuditLog.objects.select_related("actor")
        .filter(
            Q(entity_type="outcome_repair", entity_id=str(repair.id))
            | Q(metadata__repair_id=repair.id)
            | Q(
                action__in=(AuditAction.FULFILLMENT_CREATED, AuditAction.FULFILLMENT_STATUS_CHANGED),
                metadata__source="outcome_repair",
                metadata__lot_id=repair.lot_id,
            )
        )
        .exclude(action=AuditAction.OUTCOME_REPAIR_AUDIT_VIEWED)
        .order_by("server_timestamp", "id")
    )


class AuctionViewSet(viewsets.ModelViewSet):
    serializer_class = AuctionSerializer
    permission_classes = (IsAuctionOwnerOrAdminOrReadOnly,)

    def get_queryset(self):
        queryset = Auction.objects.select_related("created_by").all()
        user = self.request.user

        if user.is_authenticated and user.is_platform_admin:
            visible = queryset
        elif user.is_authenticated and user.can_sell:
            visible = queryset.filter(
                Q(status__in=VISIBLE_AUCTION_STATUSES) | Q(created_by=user)
            )
        else:
            visible = queryset.filter(status__in=VISIBLE_AUCTION_STATUSES)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            visible = visible.filter(status=status_filter)

        search = self.request.query_params.get("search")
        if search:
            visible = visible.filter(Q(title__icontains=search) | Q(description__icontains=search))

        starts_after = _parse_datetime_query_param(self.request.query_params.get("starts_after"), "starts_after")
        if starts_after:
            visible = visible.filter(start_time__gte=starts_after)

        ends_before = _parse_datetime_query_param(self.request.query_params.get("ends_before"), "ends_before")
        if ends_before:
            visible = visible.filter(end_time__lte=ends_before)

        sort = self.request.query_params.get("sort")
        if sort == "oldest":
            visible = visible.order_by("start_time", "created_at")
        elif sort == "ending_soon":
            visible = visible.order_by("end_time", "start_time")
        elif sort == "newest":
            visible = visible.order_by("-created_at", "-start_time")

        return visible

    def perform_create(self, serializer):
        auction = serializer.save(created_by=self.request.user)
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditAction.AUCTION_CREATED,
            entity_type="auction",
            entity_id=str(auction.id),
            metadata={
                "auction_id": auction.id,
                "title": auction.title,
                "status": auction.status,
            },
        )

    def perform_update(self, serializer):
        auction = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditAction.AUCTION_UPDATED,
            entity_type="auction",
            entity_id=str(auction.id),
            metadata={
                "auction_id": auction.id,
                "updated_fields": sorted(serializer.validated_data.keys()),
                "status": auction.status,
            },
        )

    @action(detail=True, methods=["get"], permission_classes=(IsAuthenticated,))
    def manage(self, request, pk=None):
        auction = self.get_object()
        user = request.user
        if not user.can_sell:
            raise PermissionDenied("Only sellers and admins can manage auctions.")
        if not user.is_platform_admin and auction.created_by_id != user.id:
            raise PermissionDenied("You can only manage your own auctions.")

        return Response(AuctionSerializer(auction).data)

    @action(detail=True, methods=["get"], permission_classes=(IsAuthenticated,))
    def results(self, request, pk=None):
        auction = self.get_object()
        user = request.user
        if not user.can_sell:
            raise PermissionDenied("Only sellers and admins can review auction outcomes.")
        if not user.is_platform_admin and auction.created_by_id != user.id:
            raise PermissionDenied("You can only review outcomes for your own auctions.")

        lots = list(
            Lot.objects.select_related("auction", "winner", "winning_bid")
            .filter(auction=auction, winner_calculated_at__isnull=False)
            .order_by("id")
        )
        return Response(
            {
                "auction": AuctionSerializer(auction).data,
                "summary": _winner_summary(lots),
                "results": LotWinnerReviewSerializer(lots, many=True).data,
            }
        )


class LotViewSet(viewsets.ModelViewSet):
    serializer_class = LotSerializer
    permission_classes = (IsLotOwnerOrAdminOrReadOnly,)

    def get_queryset(self):
        queryset = Lot.objects.select_related("auction", "auction__created_by").prefetch_related("uploaded_images").all()
        user = self.request.user

        if user.is_authenticated and user.is_platform_admin:
            visible = queryset
        elif user.is_authenticated and user.can_sell:
            visible = queryset.filter(
                Q(auction__status__in=VISIBLE_AUCTION_STATUSES, status__in=VISIBLE_LOT_STATUSES)
                | Q(auction__created_by=user)
            )
        else:
            visible = queryset.filter(
                auction__status__in=VISIBLE_AUCTION_STATUSES,
                status__in=VISIBLE_LOT_STATUSES,
            )

        auction_id = self.request.query_params.get("auction")
        if auction_id:
            visible = visible.filter(auction_id=auction_id)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            visible = visible.filter(status=status_filter)

        search = self.request.query_params.get("search")
        if search:
            visible = visible.filter(Q(title__icontains=search) | Q(description__icontains=search))

        auction_search = self.request.query_params.get("auction_search")
        if auction_search:
            visible = visible.filter(auction__title__icontains=auction_search)

        starts_after = _parse_datetime_query_param(self.request.query_params.get("starts_after"), "starts_after")
        if starts_after:
            visible = visible.filter(auction__start_time__gte=starts_after)

        ends_before = _parse_datetime_query_param(self.request.query_params.get("ends_before"), "ends_before")
        if ends_before:
            visible = visible.filter(auction__end_time__lte=ends_before)

        sort = self.request.query_params.get("sort")
        if sort == "oldest":
            visible = visible.order_by("created_at", "id")
        elif sort == "ending_soon":
            visible = visible.order_by("auction__end_time", "id")
        elif sort == "newest":
            visible = visible.order_by("-created_at", "-id")

        return visible

    def perform_create(self, serializer):
        auction = serializer.validated_data["auction"]
        user = self.request.user
        if not user.is_platform_admin and auction.created_by_id != user.id:
            raise PermissionDenied("You can only create lots for your own auctions.")

        lot = serializer.save()
        AuditLog.objects.create(
            actor=user,
            action=AuditAction.LOT_CREATED,
            entity_type="lot",
            entity_id=str(lot.id),
            metadata={
                "lot_id": lot.id,
                "auction_id": auction.id,
                "title": lot.title,
                "status": lot.status,
                "starting_price": str(lot.starting_price),
            },
        )

    def perform_update(self, serializer):
        target_auction = serializer.validated_data.get("auction", serializer.instance.auction)
        user = self.request.user
        if not user.is_platform_admin and target_auction.created_by_id != user.id:
            raise PermissionDenied("You can only move lots between auctions you own.")

        lot = serializer.save()
        AuditLog.objects.create(
            actor=user,
            action=AuditAction.LOT_UPDATED,
            entity_type="lot",
            entity_id=str(lot.id),
            metadata={
                "lot_id": lot.id,
                "auction_id": lot.auction_id,
                "updated_fields": sorted(serializer.validated_data.keys()),
                "status": lot.status,
            },
        )

    @action(detail=True, methods=["post"], permission_classes=(AllowAny,))
    def bid(self, request, pk=None):
        try:
            lot = Lot.objects.only("id", "auction_id", "current_price").get(pk=pk)
        except Lot.DoesNotExist as exc:
            raise NotFound("Lot not found.") from exc

        rate_limit = check_bid_rate_limit(request)
        if not rate_limit.allowed:
            server_timestamp = timezone.now()
            actor = request.user if request.user.is_authenticated else None
            request_context = request_audit_metadata(request)
            AuditLog.objects.create(
                actor=actor,
                action=AuditAction.BID_REJECTED,
                entity_type="lot",
                entity_id=str(lot.id),
                server_timestamp=server_timestamp,
                metadata={
                    "lot_id": lot.id,
                    "auction_id": lot.auction_id,
                    "bidder_id": actor.id if actor else None,
                    "current_price": str(lot.current_price),
                    "reason": BidRejectionReason.RATE_LIMITED,
                    "rate_limit_scope": rate_limit.scope,
                    "rate_limit": rate_limit.limit,
                    "retry_after": rate_limit.retry_after,
                    **request_context,
                },
            )
            audit_security_event(
                request=request,
                actor=actor,
                action=AuditAction.RATE_LIMIT_TRIGGERED,
                entity_type="lot",
                entity_id=str(lot.id),
                metadata={
                    "lot_id": lot.id,
                    "auction_id": lot.auction_id,
                    "scope": "bid_create",
                    "limit": rate_limit.limit,
                    "retry_after": rate_limit.retry_after,
                },
            )
            logger.warning(
                "Bid attempt rate limited",
                extra={
                    "event": "bid_rejected",
                    "lot_id": lot.id,
                    "auction_id": lot.auction_id,
                    "bidder_id": actor.id if actor else None,
                    "attempted_amount": str(request.data.get("amount", "")),
                    "current_price": str(lot.current_price),
                    "rejection_reason": BidRejectionReason.RATE_LIMITED,
                    "scope": rate_limit.scope,
                    "limit": rate_limit.limit,
                    "retry_after": rate_limit.retry_after,
                    "server_timestamp": server_timestamp.isoformat(),
                },
            )
            return Response(
                {
                    "status": "rejected",
                    "lot_id": lot.id,
                    "reason": BidRejectionReason.RATE_LIMITED,
                    "message": "Too many bid attempts. Please wait before bidding again.",
                    "current_price": str(lot.current_price),
                    "server_timestamp": server_timestamp,
                    "retry_after": rate_limit.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = BidRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = place_bid(
            user=request.user,
            lot_id=lot.id,
            amount=serializer.validated_data["amount"],
            request_context=request_audit_metadata(request),
        )
        response = BidResultSerializer(result.as_dict()).data

        if result.accepted:
            return Response(response, status=status.HTTP_201_CREATED)

        if result.reason == "UNAUTHENTICATED":
            return Response(response, status=status.HTTP_401_UNAUTHORIZED)

        if result.reason == "USER_NOT_ALLOWED":
            return Response(response, status=status.HTTP_403_FORBIDDEN)

        return Response(response, status=status.HTTP_409_CONFLICT)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=(IsAuthenticated,),
        parser_classes=(MultiPartParser, FormParser),
        url_path="images",
    )
    def images(self, request, pk=None):
        lot = self.get_object()
        user = request.user
        _ensure_can_manage_lot_images(user=user, lot=lot)

        serializer = LotImageUploadSerializer(
            data=request.data,
            context={
                "request": request,
                "max_size_mb": getattr(settings, "LOT_IMAGE_MAX_UPLOAD_SIZE_MB", 5),
            },
        )
        serializer.is_valid(raise_exception=True)
        _ensure_local_media_root_available()
        try:
            lot_image = serializer.save(lot=lot)
        except OSError as exc:
            logger.exception(
                "Lot image upload failed while saving file",
                extra={
                    "event": "lot_image_upload_failed",
                    "lot_id": lot.id,
                    "auction_id": lot.auction_id,
                    "actor_id": user.id,
                    "media_root": str(settings.MEDIA_ROOT),
                },
            )
            raise ValidationError(
                {
                    "image": [
                        "Image upload failed because storage is unavailable. "
                        "Check MEDIA_ROOT/SERVE_LOCAL_MEDIA for staging or object storage settings for production."
                    ]
                }
            ) from exc

        AuditLog.objects.create(
            actor=user,
            action=AuditAction.LOT_UPDATED,
            entity_type="lot",
            entity_id=str(lot.id),
            metadata={
                "lot_id": lot.id,
                "auction_id": lot.auction_id,
                "updated_fields": ["uploaded_images"],
                "image_id": lot_image.id,
            },
        )

        return Response(
            LotImageSerializer(lot_image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=(IsAuthenticated,),
        url_path=r"images/(?P<image_id>\d+)",
    )
    def image_detail(self, request, pk=None, image_id=None):
        lot = self.get_object()
        user = request.user
        _ensure_can_manage_lot_images(user=user, lot=lot)

        try:
            lot_image = lot.uploaded_images.get(pk=image_id)
        except LotImage.DoesNotExist as exc:
            raise NotFound("Lot image not found.") from exc

        image_metadata = {
            "image_id": lot_image.id,
            "image_name": lot_image.image.name,
            "sort_order": lot_image.sort_order,
            "alt_text": lot_image.alt_text,
        }
        image_file = lot_image.image
        lot_image.delete()
        if image_file:
            image_file.delete(save=False)

        AuditLog.objects.create(
            actor=user,
            action=AuditAction.LOT_UPDATED,
            entity_type="lot",
            entity_id=str(lot.id),
            metadata={
                "lot_id": lot.id,
                "auction_id": lot.auction_id,
                "updated_fields": ["uploaded_images"],
                "image_deleted": image_metadata,
            },
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=(IsAuthenticated,),
        url_path="images/reorder",
    )
    def reorder_images(self, request, pk=None):
        lot = self.get_object()
        user = request.user
        _ensure_can_manage_lot_images(user=user, lot=lot)

        serializer = LotImageReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_items = serializer.validated_data["image_order"]
        requested_ids = [item["id"] for item in order_items]
        images = {image.id: image for image in lot.uploaded_images.filter(id__in=requested_ids)}
        missing_ids = sorted(set(requested_ids) - set(images))
        if missing_ids:
            raise ValidationError({"image_order": f"Images do not belong to this lot: {missing_ids}."})

        with transaction.atomic():
            for item in order_items:
                images[item["id"]].sort_order = item["sort_order"]
            LotImage.objects.bulk_update(images.values(), ["sort_order"])

            AuditLog.objects.create(
                actor=user,
                action=AuditAction.LOT_UPDATED,
                entity_type="lot",
                entity_id=str(lot.id),
                metadata={
                    "lot_id": lot.id,
                    "auction_id": lot.auction_id,
                    "updated_fields": ["uploaded_images"],
                    "image_reorder": order_items,
                },
            )

        refreshed_images = LotImage.objects.filter(lot=lot).order_by("sort_order", "id")
        return Response(
            LotImageSerializer(refreshed_images, many=True, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def bids(self, request, pk=None):
        lot = self.get_object()
        bids = Bid.objects.filter(lot=lot).select_related("bidder")

        user = request.user
        if not (
            user.is_authenticated
            and (user.is_platform_admin or lot.auction.created_by_id == user.id)
        ):
            bids = bids.filter(status=BidStatus.ACCEPTED)

        serializer = BidSerializer(bids, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=(IsAuthenticated,))
    def audit(self, request, pk=None):
        lot = self.get_object()
        user = request.user
        if not (user.is_platform_admin or lot.auction.created_by_id == user.id):
            raise PermissionDenied("Only the auction owner or an admin can view lot audit logs.")

        audit_logs = AuditLog.objects.filter(
            Q(entity_type="lot", entity_id=str(lot.id)) | Q(metadata__lot_id=lot.id)
        ).select_related("actor")
        serializer = AuditLogSerializer(audit_logs, many=True)
        return Response(serializer.data)
