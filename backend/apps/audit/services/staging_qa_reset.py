from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import os

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog, OutboundNotification
from apps.audit.services.staging_diagnostics import (
    collect_staging_lifecycle_readiness,
    inconsistent_lot_query,
)
from apps.auctions.models import (
    Auction,
    AuctionStatus,
    Bid,
    FulfillmentRecord,
    Lot,
    LotStatus,
    OutcomeRepairComment,
    OutcomeRepairRequest,
)
from apps.auctions.services.lifecycle import (
    ACTIVE_AUCTION_STATUSES,
    ENDED_AUCTION_STATUS_ALIASES,
    get_effective_auction_status,
)

QA_TITLE_PREFIXES = ("QA-", "E2E", "Test", "Retest")
DEMO_TITLE_PREFIXES = ("[STAGING TEST AUCTION]", "[STAGING QA BASELINE]")
PROTECTED_TITLE_PREFIXES = ("[PROTECTED]", "PROTECTED")
RESET_SOURCE = "staging_reset_qa_data"
QA_BASELINE_SOURCE = "seed_staging_qa_baseline"
QA_BASELINE_PASSWORD = "ChangeMe123!"
QA_BASELINE_AUCTION_TITLE = "[STAGING QA BASELINE] Clean Demo Auction"


@dataclass(frozen=True)
class ResetOptions:
    apply: bool = False
    older_than_days: int = 30
    include_demo: bool = False
    hard_delete: bool = False


def staging_writes_allowed() -> bool:
    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    render_service_name = os.environ.get("RENDER_SERVICE_NAME", "").strip().lower()
    production_markers = (
        environment,
        os.environ.get("BIDALS_ENV", "").strip().lower(),
        os.environ.get("ENV", "").strip().lower(),
        os.environ.get("SENTRY_ENVIRONMENT", "").strip().lower(),
    )
    if any(marker == "production" for marker in production_markers):
        return False
    return environment == "staging" or "staging" in render_service_name


def reset_staging_qa_data(*, options: ResetOptions) -> dict:
    now = timezone.now()
    candidate_plan = build_reset_plan(options=options, now=now)
    before = reset_summary()
    result = {
        "command": RESET_SOURCE,
        "mode": "apply" if options.apply else "dry-run",
        "options": {
            "older_than_days": options.older_than_days,
            "include_demo": options.include_demo,
            "hard_delete": options.hard_delete,
        },
        "before": before,
        "candidates": candidate_plan["candidates"],
        "protected": candidate_plan["protected"],
        "planned": candidate_plan["planned"],
        "deleted": zero_delete_counts(),
        "after": before,
        "readiness": readiness_payload(),
    }

    if not options.apply:
        return result

    with transaction.atomic():
        deleted = apply_reset_plan(candidate_plan, hard_delete=options.hard_delete, now=now)
        result["deleted"] = deleted
        if any(deleted.values()):
            AuditLog.objects.create(
                actor=None,
                action=AuditAction.ADMIN_ACTION,
                entity_type="staging_qa_reset",
                entity_id=now.strftime("%Y%m%d%H%M%S"),
                server_timestamp=now,
                metadata={
                    "source": RESET_SOURCE,
                    "options": result["options"],
                    "candidate_auction_ids": [item["id"] for item in candidate_plan["candidates"]],
                    "protected_auction_ids": [item["id"] for item in candidate_plan["protected"]],
                    "planned": candidate_plan["planned"],
                    "deleted": deleted,
                },
            )

    result["after"] = reset_summary()
    result["readiness"] = readiness_payload()
    return result


def build_reset_plan(*, options: ResetOptions, now) -> dict:
    cutoff = now - timedelta(days=options.older_than_days)
    protected_ids = protected_auction_ids_from_environment()
    inconsistent_auction_ids = set(
        Lot.objects.filter(inconsistent_lot_query()).values_list("auction_id", flat=True).distinct()
    )
    candidates = []
    protected = []

    for auction in Auction.objects.order_by("id"):
        reasons = candidate_reasons(
            auction,
            cutoff=cutoff,
            include_demo=options.include_demo,
            inconsistent_auction_ids=inconsistent_auction_ids,
            now=now,
        )
        if not reasons:
            continue

        item = auction_plan_item(auction, reasons=reasons)
        if auction.id in protected_ids or is_protected_title(auction.title):
            protected.append({**item, "protected_reason": "manual_protection"})
            continue
        candidates.append(item)

    auction_ids = [item["id"] for item in candidates]
    related_ids = related_record_ids(auction_ids)
    orphan_notification_ids = orphan_notification_ids_for_cleanup()
    planned = planned_delete_counts(
        auction_ids=auction_ids,
        related_ids=related_ids,
        orphan_notification_ids=orphan_notification_ids,
        hard_delete=options.hard_delete,
    )
    return {
        "candidates": candidates,
        "protected": protected,
        "auction_ids": auction_ids,
        "related_ids": related_ids,
        "orphan_notification_ids": orphan_notification_ids,
        "planned": planned,
    }


def candidate_reasons(auction: Auction, *, cutoff, include_demo: bool, inconsistent_auction_ids: set[int], now) -> list[str]:
    title = auction.title or ""
    qa_title = starts_with_any(title, QA_TITLE_PREFIXES)
    demo_title = starts_with_any(title, DEMO_TITLE_PREFIXES)
    if demo_title and not include_demo:
        return []

    reasons = []
    effective_status = safe_effective_auction_status(auction, now=now)
    older_than_cutoff = auction.end_time <= cutoff
    if qa_title:
        reasons.append("title_prefix")
    if demo_title and include_demo:
        reasons.append("include_demo")
    if auction.status in ACTIVE_AUCTION_STATUSES and effective_status == AuctionStatus.ENDED:
        reasons.append("stale_effective_ended_auction")
    if auction.id in inconsistent_auction_ids:
        reasons.append("inconsistent_lifecycle_records")
    if older_than_cutoff and (
        qa_title
        or demo_title
        or auction.status in ENDED_AUCTION_STATUS_ALIASES
        or effective_status == AuctionStatus.ENDED
    ):
        reasons.append("older_than_days")
    return sorted(set(reasons))


def apply_reset_plan(plan: dict, *, hard_delete: bool, now) -> dict:
    auction_ids = plan["auction_ids"]
    related_ids = plan["related_ids"]
    notification_ids = sorted(set(plan["orphan_notification_ids"]) | set(notification_ids_for_related_records(related_ids)))
    deleted = zero_delete_counts()

    deleted["notifications"] += delete_queryset(OutboundNotification.objects.filter(id__in=notification_ids))
    deleted["outcome_repair_comments"] += delete_queryset(
        OutcomeRepairComment.objects.filter(repair_request_id__in=related_ids["outcome_repair_ids"])
    )
    deleted["outcome_repair_requests"] += delete_queryset(
        OutcomeRepairRequest.objects.filter(id__in=related_ids["outcome_repair_ids"])
    )
    deleted["fulfillment_records"] += delete_queryset(
        FulfillmentRecord.objects.filter(id__in=related_ids["fulfillment_ids"])
    )
    if hard_delete:
        deleted["audit_logs"] += delete_queryset(audit_logs_for_related_records(related_ids))
    deleted["auctions"] += delete_queryset(Auction.objects.filter(id__in=auction_ids))
    if auction_ids:
        deleted["lots"] = len(related_ids["lot_ids"])
        deleted["bids"] = len(related_ids["bid_ids"])
    return deleted


def delete_queryset(queryset) -> int:
    count = queryset.count()
    queryset.delete()
    return count


def related_record_ids(auction_ids: list[int]) -> dict:
    lot_ids = list(Lot.objects.filter(auction_id__in=auction_ids).values_list("id", flat=True))
    bid_ids = list(Bid.objects.filter(lot_id__in=lot_ids).values_list("id", flat=True))
    fulfillment_ids = list(FulfillmentRecord.objects.filter(lot_id__in=lot_ids).values_list("id", flat=True))
    outcome_repair_ids = list(OutcomeRepairRequest.objects.filter(lot_id__in=lot_ids).values_list("id", flat=True))
    return {
        "auction_ids": auction_ids,
        "lot_ids": lot_ids,
        "bid_ids": bid_ids,
        "fulfillment_ids": fulfillment_ids,
        "outcome_repair_ids": outcome_repair_ids,
    }


def planned_delete_counts(*, auction_ids: list[int], related_ids: dict, orphan_notification_ids: list[int], hard_delete: bool) -> dict:
    notification_ids = sorted(set(orphan_notification_ids) | set(notification_ids_for_related_records(related_ids)))
    counts = zero_delete_counts()
    counts.update(
        {
            "auctions": len(auction_ids),
            "lots": len(related_ids["lot_ids"]),
            "bids": len(related_ids["bid_ids"]),
            "fulfillment_records": len(related_ids["fulfillment_ids"]),
            "outcome_repair_requests": len(related_ids["outcome_repair_ids"]),
            "outcome_repair_comments": OutcomeRepairComment.objects.filter(
                repair_request_id__in=related_ids["outcome_repair_ids"]
            ).count(),
            "notifications": len(notification_ids),
            "audit_logs": audit_logs_for_related_records(related_ids).count() if hard_delete else 0,
        }
    )
    return counts


def zero_delete_counts() -> dict:
    return {
        "auctions": 0,
        "lots": 0,
        "bids": 0,
        "fulfillment_records": 0,
        "outcome_repair_requests": 0,
        "outcome_repair_comments": 0,
        "notifications": 0,
        "audit_logs": 0,
    }


def notification_ids_for_related_records(related_ids: dict) -> list[int]:
    query = Q(pk__in=[])
    for entity_type, ids in (
        ("auction", related_ids["auction_ids"]),
        ("lot", related_ids["lot_ids"]),
        ("bid", related_ids["bid_ids"]),
        ("fulfillment", related_ids["fulfillment_ids"]),
        ("outcome_repair", related_ids["outcome_repair_ids"]),
    ):
        if ids:
            query |= Q(related_entity_type=entity_type, related_entity_id__in=[str(value) for value in ids])
    return list(OutboundNotification.objects.filter(query).values_list("id", flat=True))


def orphan_notification_ids_for_cleanup() -> list[int]:
    ids = []
    for entity_type, model in (
        ("auction", Auction),
        ("lot", Lot),
        ("bid", Bid),
        ("fulfillment", FulfillmentRecord),
        ("outcome_repair", OutcomeRepairRequest),
    ):
        existing = {str(value) for value in model.objects.values_list("id", flat=True)}
        ids.extend(
            OutboundNotification.objects.filter(related_entity_type=entity_type)
            .exclude(related_entity_id__in=existing)
            .values_list("id", flat=True)
        )
    return sorted(set(ids))


def audit_logs_for_related_records(related_ids: dict):
    query = Q(pk__in=[])
    for entity_type, ids in (
        ("auction", related_ids["auction_ids"]),
        ("lot", related_ids["lot_ids"]),
        ("bid", related_ids["bid_ids"]),
        ("fulfillment", related_ids["fulfillment_ids"]),
        ("outcome_repair", related_ids["outcome_repair_ids"]),
    ):
        if ids:
            query |= Q(entity_type=entity_type, entity_id__in=[str(value) for value in ids])
    return AuditLog.objects.filter(query)


def reset_summary() -> dict:
    return {
        "auctions": Auction.objects.count(),
        "lots": Lot.objects.count(),
        "bids": Bid.objects.count(),
        "fulfillment_records": FulfillmentRecord.objects.count(),
        "notifications": OutboundNotification.objects.count(),
        "audit_logs": AuditLog.objects.count(),
        "inconsistent_lots": Lot.objects.filter(inconsistent_lot_query()).count(),
        "stale_effective_ended_auctions": stale_effective_ended_auction_count(),
        "orphan_notifications": len(orphan_notification_ids_for_cleanup()),
    }


def stale_effective_ended_auction_count() -> int:
    count = 0
    now = timezone.now()
    for auction in Auction.objects.filter(status__in=ACTIVE_AUCTION_STATUSES):
        if safe_effective_auction_status(auction, now=now) == AuctionStatus.ENDED:
            count += 1
    return count


def readiness_payload() -> list[dict]:
    return [
        {"status": line.status, "name": line.name, "message": line.message}
        for line in collect_staging_lifecycle_readiness()
    ]


def auction_plan_item(auction: Auction, *, reasons: list[str]) -> dict:
    return {
        "id": auction.id,
        "title": auction.title,
        "status": auction.status,
        "effective_status": safe_effective_auction_status(auction, now=timezone.now()),
        "start_time": auction.start_time.isoformat(),
        "end_time": auction.end_time.isoformat(),
        "created_by_id": auction.created_by_id,
        "reasons": reasons,
    }


def safe_effective_auction_status(auction: Auction, *, now) -> str:
    try:
        return get_effective_auction_status(auction, now=now)
    except Exception as exc:
        return f"unavailable ({exc.__class__.__name__})"


def starts_with_any(value: str, prefixes: tuple[str, ...]) -> bool:
    normalized = value.strip().lower()
    return any(normalized.startswith(prefix.lower()) for prefix in prefixes)


def is_protected_title(title: str) -> bool:
    return starts_with_any(title, PROTECTED_TITLE_PREFIXES) or "[protected]" in title.lower()


def protected_auction_ids_from_environment() -> set[int]:
    raw = os.environ.get("STAGING_PROTECTED_AUCTION_IDS", "")
    protected = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            protected.add(int(item))
        except ValueError:
            continue
    return protected


def seed_staging_qa_baseline() -> dict:
    now = timezone.now()
    with transaction.atomic():
        seller = upsert_qa_user(
            username="qa_seller",
            email="qa-seller@bidals.staging.test",
            role=UserRole.SELLER,
        )
        bidder_one = upsert_qa_user(
            username="qa_bidder_one",
            email="qa-bidder-one@bidals.staging.test",
            role=UserRole.BIDDER,
        )
        bidder_two = upsert_qa_user(
            username="qa_bidder_two",
            email="qa-bidder-two@bidals.staging.test",
            role=UserRole.BIDDER,
        )

        existing_ids = list(
            Auction.objects.filter(title=QA_BASELINE_AUCTION_TITLE).values_list("id", flat=True)
        )
        if existing_ids:
            plan = {
                "auction_ids": existing_ids,
                "related_ids": related_record_ids(existing_ids),
                "orphan_notification_ids": [],
            }
            apply_reset_plan(plan, hard_delete=True, now=now)

        auction = Auction.objects.create(
            title=QA_BASELINE_AUCTION_TITLE,
            description="Clean staging QA baseline auction for lifecycle and browsing smoke tests.",
            start_time=now - timedelta(minutes=15),
            end_time=now + timedelta(hours=4),
            status=AuctionStatus.LIVE,
            created_by=seller,
        )
        lots = [
            Lot.objects.create(
                auction=auction,
                title="[QA BASELINE LOT] Starter Object",
                description="Clean open lot with no bids.",
                starting_price=Decimal("50.00"),
                current_price=Decimal("50.00"),
                reserve_price=None,
                bid_increment=Decimal("5.00"),
                status=LotStatus.OPEN,
            ),
            Lot.objects.create(
                auction=auction,
                title="[QA BASELINE LOT] Reserve Practice",
                description="Clean open lot with reserve pricing.",
                starting_price=Decimal("100.00"),
                current_price=Decimal("100.00"),
                reserve_price=Decimal("150.00"),
                bid_increment=Decimal("10.00"),
                status=LotStatus.OPEN,
            ),
            Lot.objects.create(
                auction=auction,
                title="[QA BASELINE LOT] Increment Practice",
                description="Clean open lot for bid increment checks.",
                starting_price=Decimal("25.00"),
                current_price=Decimal("25.00"),
                reserve_price=None,
                bid_increment=Decimal("2.50"),
                status=LotStatus.OPEN,
            ),
        ]
        AuditLog.objects.create(
            actor=None,
            action=AuditAction.STAGING_SEED_RUN,
            entity_type="staging_qa_baseline",
            entity_id=str(auction.id),
            server_timestamp=now,
            metadata={
                "source": QA_BASELINE_SOURCE,
                "auction_id": auction.id,
                "lot_ids": [lot.id for lot in lots],
                "seller_id": seller.id,
                "bidder_ids": [bidder_one.id, bidder_two.id],
            },
        )

    return {
        "command": QA_BASELINE_SOURCE,
        "auction_id": auction.id,
        "auction_title": auction.title,
        "lot_ids": [lot.id for lot in lots],
        "seller": {"username": seller.username, "email": seller.email},
        "bidders": [
            {"username": bidder_one.username, "email": bidder_one.email},
            {"username": bidder_two.username, "email": bidder_two.email},
        ],
        "password": QA_BASELINE_PASSWORD,
        "readiness": readiness_payload(),
    }


def upsert_qa_user(*, username: str, email: str, role: str):
    User = get_user_model()
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User(email=email)
    user.username = username
    user.email = email
    user.role = role
    user.is_staff = False
    user.is_superuser = False
    user.is_active = True
    user.set_password(QA_BASELINE_PASSWORD)
    user.save()
    return user
