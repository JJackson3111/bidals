from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog, OutboundNotification
from apps.audit.services.readiness import runtime_environment
from apps.auctions.models import (
    Auction,
    AuctionStatus,
    Bid,
    BidStatus,
    FulfillmentRecord,
    FulfillmentStatus,
    Lot,
    LotStatus,
    LotWinnerStatus,
)
from apps.auctions.services.bidding import place_bid
from apps.auctions.services.notifications import emit_notification_event


STAGING_PASSWORD = "ChangeMe123!"
STAGING_PREFIX = "[STAGING TEST AUCTION]"


class Command(BaseCommand):
    help = "Seed BIDALS with explicit staging-only users, auctions, lots, bids, fulfillment, and notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running when BIDALS_ENV/ENV/SENTRY_ENVIRONMENT is production.",
        )

    def handle(self, *args, **options):
        environment = runtime_environment()
        if environment == "production" and not options["force"]:
            raise CommandError("Refusing to seed staging data in production without --force.")

        self.stdout.write(self.style.WARNING(f"Seeding staging data for environment: {environment}"))
        with transaction.atomic():
            admin = self._upsert_user(
                username="staging_admin",
                email="admin@bidals.staging.test",
                role=UserRole.ADMIN,
                is_staff=True,
                is_superuser=True,
            )
            seller = self._upsert_user(
                username="staging_seller",
                email="seller@bidals.staging.test",
                role=UserRole.SELLER,
            )
            seller_two = self._upsert_user(
                username="staging_seller_two",
                email="seller2@bidals.staging.test",
                role=UserRole.SELLER,
            )
            bidder = self._upsert_user(
                username="staging_bidder",
                email="bidder@bidals.staging.test",
                role=UserRole.BIDDER,
            )
            bidder_two = self._upsert_user(
                username="staging_bidder_two",
                email="bidder2@bidals.staging.test",
                role=UserRole.BIDDER,
            )

            self._clear_existing_staging_data(sellers=(seller, seller_two))

            now = timezone.now()
            live_auction = self._create_auction(
                seller=seller,
                title=f"{STAGING_PREFIX} Live Governance Sale",
                description="Clearly fake live staging auction for bid, audit, and notification smoke tests.",
                start_time=now - timedelta(minutes=30),
                end_time=now + timedelta(hours=3),
                status=AuctionStatus.LIVE,
            )
            scheduled_auction = self._create_auction(
                seller=seller_two,
                title=f"{STAGING_PREFIX} Scheduled Seller Review",
                description="Clearly fake scheduled staging auction for create/edit/review flows.",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=2),
                status=AuctionStatus.SCHEDULED,
            )
            ended_auction = self._create_auction(
                seller=seller,
                title=f"{STAGING_PREFIX} Ended Fulfillment Drill",
                description="Clearly fake ended staging auction with winner and fulfillment records.",
                start_time=now - timedelta(days=2),
                end_time=now - timedelta(days=1, hours=21),
                status=AuctionStatus.ENDED,
            )

            live_lot = self._create_lot(
                auction=live_auction,
                title="[DEMO LOT] Staging Live Bid Device",
                description="Fake staging lot for accepted and rejected bid testing.",
                starting_price=Decimal("100.00"),
                reserve_price=Decimal("150.00"),
                bid_increment=Decimal("10.00"),
                status=LotStatus.OPEN,
            )
            self._create_lot(
                auction=live_auction,
                title="[DEMO LOT] Staging Reserve Practice Item",
                description="Fake staging lot for reserve and dashboard review.",
                starting_price=Decimal("250.00"),
                reserve_price=Decimal("400.00"),
                bid_increment=Decimal("25.00"),
                status=LotStatus.OPEN,
            )
            self._create_lot(
                auction=scheduled_auction,
                title="[DEMO LOT] Scheduled Preview Object",
                description="Fake staging scheduled lot for seller page review.",
                starting_price=Decimal("50.00"),
                reserve_price=None,
                bid_increment=Decimal("5.00"),
                status=LotStatus.OPEN,
            )
            ended_lot = self._create_lot(
                auction=ended_auction,
                title="[DEMO LOT] Ended Fulfillment Example",
                description="Fake staging ended lot with a backend-owned winner.",
                starting_price=Decimal("75.00"),
                reserve_price=Decimal("80.00"),
                bid_increment=Decimal("5.00"),
                status=LotStatus.CLOSED,
            )

            place_bid(bidder, live_lot.id, Decimal("110.00"))
            place_bid(bidder_two, live_lot.id, Decimal("120.00"))
            place_bid(bidder, live_lot.id, Decimal("115.00"))
            place_bid(bidder_two, live_lot.id, Decimal("125.00"))

            winning_bid = Bid.objects.create(
                lot=ended_lot,
                bidder=bidder,
                amount=Decimal("95.00"),
                status=BidStatus.ACCEPTED,
                server_timestamp=now - timedelta(days=1, hours=22),
            )
            Bid.objects.create(
                lot=ended_lot,
                bidder=bidder_two,
                amount=Decimal("80.00"),
                status=BidStatus.REJECTED,
                rejection_reason="BID_TOO_LOW",
                server_timestamp=now - timedelta(days=1, hours=22, minutes=10),
            )
            ended_lot.current_price = winning_bid.amount
            ended_lot.status = LotStatus.SOLD
            ended_lot.winner = bidder
            ended_lot.winning_bid = winning_bid
            ended_lot.winner_status = LotWinnerStatus.WINNER_ASSIGNED
            ended_lot.winner_calculated_at = now - timedelta(days=1, hours=20)
            ended_lot.save(
                update_fields=("current_price", "status", "winner", "winning_bid", "winner_status", "winner_calculated_at", "updated_at")
            )
            fulfillment = FulfillmentRecord.objects.create(
                lot=ended_lot,
                auction=ended_auction,
                winning_bid=winning_bid,
                winner=bidder,
                status=FulfillmentStatus.SELLER_CONTACTED,
                public_winner_message="Staging-only fulfillment follow-up has started.",
                seller_notes="STAGING TEST NOTE - not production data.",
            )
            emit_notification_event(
                event_type="seller_contacted",
                recipient=bidder,
                entity_type="fulfillment",
                entity_id=str(fulfillment.id),
                metadata={
                    "staging_seed": True,
                    "fulfillment_id": fulfillment.id,
                    "lot_id": ended_lot.id,
                    "auction_id": ended_auction.id,
                    "status": fulfillment.status,
                },
            )

            AuditLog.objects.create(
                actor=admin,
                action=AuditAction.STAGING_SEED_RUN,
                entity_type="staging_seed",
                entity_id=timezone.now().strftime("%Y%m%d%H%M%S"),
                metadata={
                    "staging_seed": True,
                    "environment": environment,
                    "seller_ids": [seller.id, seller_two.id],
                    "bidder_ids": [bidder.id, bidder_two.id],
                    "auction_ids": [live_auction.id, scheduled_auction.id, ended_auction.id],
                    "fulfillment_id": fulfillment.id,
                },
            )

        self.stdout.write(self.style.SUCCESS("BIDALS staging data seeded."))
        self.stdout.write("Admin:  admin@bidals.staging.test / ChangeMe123!")
        self.stdout.write("Seller: seller@bidals.staging.test / ChangeMe123!")
        self.stdout.write("Bidder: bidder@bidals.staging.test / ChangeMe123!")

    def _upsert_user(self, *, username, email, role, is_staff=False, is_superuser=False):
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User(email=email)
        user.username = username
        user.role = role
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(STAGING_PASSWORD)
        user.save()
        return user

    def _clear_existing_staging_data(self, *, sellers):
        demo_auctions = Auction.objects.filter(created_by__in=sellers, title__startswith=STAGING_PREFIX)
        auction_ids = list(demo_auctions.values_list("id", flat=True))
        lot_ids = list(Lot.objects.filter(auction_id__in=auction_ids).values_list("id", flat=True))
        bid_ids = list(Bid.objects.filter(lot_id__in=lot_ids).values_list("id", flat=True))

        audit_filter = Q(metadata__staging_seed=True)
        if auction_ids:
            audit_filter |= Q(metadata__auction_id__in=auction_ids) | Q(entity_type="auction", entity_id__in=[str(value) for value in auction_ids])
        if lot_ids:
            audit_filter |= Q(metadata__lot_id__in=lot_ids) | Q(entity_type="lot", entity_id__in=[str(value) for value in lot_ids])
        if bid_ids:
            audit_filter |= Q(entity_type="bid", entity_id__in=[str(value) for value in bid_ids])

        OutboundNotification.objects.filter(metadata__staging_seed=True).delete()
        AuditLog.objects.filter(audit_filter).delete()
        FulfillmentRecord.objects.filter(lot_id__in=lot_ids).delete()
        demo_auctions.delete()

    def _create_auction(self, *, seller, title, description, start_time, end_time, status):
        auction = Auction.objects.create(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            status=status,
            created_by=seller,
        )
        AuditLog.objects.create(
            actor=seller,
            action=AuditAction.AUCTION_CREATED,
            entity_type="auction",
            entity_id=str(auction.id),
            metadata={"staging_seed": True, "auction_id": auction.id, "title": auction.title, "status": auction.status},
        )
        return auction

    def _create_lot(self, *, auction, title, description, starting_price, reserve_price, bid_increment, status):
        lot = Lot.objects.create(
            auction=auction,
            title=title,
            description=description,
            starting_price=starting_price,
            current_price=starting_price,
            reserve_price=reserve_price,
            bid_increment=bid_increment,
            status=status,
        )
        AuditLog.objects.create(
            actor=auction.created_by,
            action=AuditAction.LOT_CREATED,
            entity_type="lot",
            entity_id=str(lot.id),
            metadata={
                "staging_seed": True,
                "lot_id": lot.id,
                "auction_id": auction.id,
                "title": lot.title,
                "status": lot.status,
            },
        )
        return lot
