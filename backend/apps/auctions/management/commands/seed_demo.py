from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.auctions.models import Auction, AuctionStatus, Bid, Lot, LotStatus
from apps.auctions.services.bidding import place_bid


DEMO_PASSWORD = "ChangeMe123!"


class Command(BaseCommand):
    help = "Seed BIDALS with demo users, auctions, lots, bids, and audit activity."

    def handle(self, *args, **options):
        with transaction.atomic():
            admin = self._upsert_user(
                username="demo_admin",
                email="admin@bidals.demo",
                role=UserRole.ADMIN,
                is_staff=True,
                is_superuser=True,
            )
            seller = self._upsert_user(
                username="demo_seller",
                email="seller@bidals.demo",
                role=UserRole.SELLER,
            )
            bidder = self._upsert_user(
                username="demo_bidder",
                email="bidder@bidals.demo",
                role=UserRole.BIDDER,
            )
            bidder_two = self._upsert_user(
                username="demo_bidder_two",
                email="bidder2@bidals.demo",
                role=UserRole.BIDDER,
            )

            self._clear_existing_demo_data(seller=seller)

            now = timezone.now()
            live_auction = self._create_auction(
                seller=seller,
                title="[Demo] BIDALS Premium Benefit Auction",
                description="A polished live demo event featuring premium lots for fundraising guests.",
                start_time=now - timedelta(minutes=25),
                end_time=now + timedelta(hours=2),
                status=AuctionStatus.LIVE,
            )
            scheduled_auction = self._create_auction(
                seller=seller,
                title="[Demo] Collector Experiences Preview",
                description="A scheduled preview of premium experiences and collector-grade lots.",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=3),
                status=AuctionStatus.SCHEDULED,
            )
            ended_auction = self._create_auction(
                seller=seller,
                title="[Demo] Completed Supporter Showcase",
                description="A completed demo auction showing historical bid and audit activity.",
                start_time=now - timedelta(days=2),
                end_time=now - timedelta(days=1, hours=20),
                status=AuctionStatus.ENDED,
            )

            starter_cellar = self._create_lot(
                auction=live_auction,
                title="[Demo] Starter Wine Cellar",
                description="A curated premium wine case with tasting notes and a private sommelier handover.",
                images=[
                    "/demo-lots/wine-hero.webp",
                    "/demo-lots/wine-detail.webp",
                    "/demo-lots/wine-lifestyle.webp",
                ],
                starting_price=Decimal("300.00"),
                reserve_price=Decimal("450.00"),
                bid_increment=Decimal("25.00"),
                status=LotStatus.OPEN,
            )
            reserve_watch = self._create_lot(
                auction=live_auction,
                title="[Demo] Reserve Swiss Watch Set",
                description="A serviced automatic dress watch with box, strap roll, and collector presentation.",
                images=[
                    "/demo-lots/watch-hero.webp",
                    "/demo-lots/watch-detail.webp",
                    "/demo-lots/watch-box.webp",
                ],
                starting_price=Decimal("1200.00"),
                reserve_price=Decimal("1800.00"),
                bid_increment=Decimal("50.00"),
                status=LotStatus.OPEN,
            )
            increment_retreat = self._create_lot(
                auction=live_auction,
                title="[Demo] Increment Travel Retreat",
                description="A two-night luxury retreat with spa access, chef dinner, and flexible guest dates.",
                images=[
                    "/demo-lots/vacation-resort.webp",
                    "/demo-lots/vacation-room.webp",
                    "/demo-lots/vacation-spa.webp",
                    "/demo-lots/vacation-dinner.webp",
                ],
                starting_price=Decimal("1800.00"),
                reserve_price=Decimal("2500.00"),
                bid_increment=Decimal("100.00"),
                status=LotStatus.OPEN,
            )
            self._create_lot(
                auction=scheduled_auction,
                title="[Demo] Private Dining Preview",
                description="A scheduled chef's table preview for eight guests.",
                images=["/demo-lots/vacation-dinner.webp"],
                starting_price=Decimal("500.00"),
                reserve_price=Decimal("750.00"),
                bid_increment=Decimal("25.00"),
                status=LotStatus.OPEN,
            )
            self._create_lot(
                auction=scheduled_auction,
                title="[Demo] Reserve Cellar Preview",
                description="A scheduled preview of a reserve wine pairing lot.",
                images=["/demo-lots/wine-lifestyle.webp"],
                starting_price=Decimal("250.00"),
                reserve_price=None,
                bid_increment=Decimal("25.00"),
                status=LotStatus.OPEN,
            )
            self._create_lot(
                auction=ended_auction,
                title="[Demo] Supporter Watch Lot",
                description="A completed example lot with bidding closed.",
                images=["/demo-lots/watch-detail.webp"],
                starting_price=Decimal("500.00"),
                reserve_price=Decimal("700.00"),
                bid_increment=Decimal("50.00"),
                status=LotStatus.SOLD,
            )

            place_bid(bidder, starter_cellar.id, Decimal("325.00"))
            place_bid(bidder_two, starter_cellar.id, Decimal("350.00"))
            place_bid(bidder, reserve_watch.id, Decimal("1250.00"))
            place_bid(bidder_two, reserve_watch.id, Decimal("1300.00"))
            place_bid(bidder, increment_retreat.id, Decimal("1900.00"))

            self._audit(
                actor=admin,
                action=AuditAction.ADMIN_ACTION,
                entity_type="demo_seed",
                entity_id="phase5",
                metadata={
                    "demo_seed": True,
                    "message": "Premium demo data refreshed for the BIDALS browse experience.",
                    "seller_id": seller.id,
                },
            )

        self.stdout.write(self.style.SUCCESS("BIDALS demo data seeded."))
        self.stdout.write("Admin:  admin@bidals.demo / ChangeMe123!")
        self.stdout.write("Seller: seller@bidals.demo / ChangeMe123!")
        self.stdout.write("Bidder: bidder@bidals.demo / ChangeMe123!")

    def _upsert_user(self, *, username, email, role, is_staff=False, is_superuser=False):
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User(email=email)

        user.username = username
        user.role = role
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _clear_existing_demo_data(self, *, seller):
        demo_auctions = Auction.objects.filter(created_by=seller, title__startswith="[Demo]")
        auction_ids = list(demo_auctions.values_list("id", flat=True))
        lot_ids = list(Lot.objects.filter(auction_id__in=auction_ids).values_list("id", flat=True))
        bid_ids = list(Bid.objects.filter(lot_id__in=lot_ids).values_list("id", flat=True))

        audit_filter = Q(metadata__demo_seed=True)
        if auction_ids:
            auction_entity_ids = [str(auction_id) for auction_id in auction_ids]
            audit_filter |= Q(metadata__auction_id__in=auction_ids) | Q(
                entity_type="auction",
                entity_id__in=auction_entity_ids,
            )
        if lot_ids:
            lot_entity_ids = [str(lot_id) for lot_id in lot_ids]
            audit_filter |= Q(metadata__lot_id__in=lot_ids) | Q(
                entity_type="lot",
                entity_id__in=lot_entity_ids,
            )
        if bid_ids:
            bid_entity_ids = [str(bid_id) for bid_id in bid_ids]
            audit_filter |= Q(entity_type="bid", entity_id__in=bid_entity_ids)

        AuditLog.objects.filter(audit_filter).delete()
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
        self._audit(
            actor=seller,
            action=AuditAction.AUCTION_CREATED,
            entity_type="auction",
            entity_id=str(auction.id),
            metadata={
                "demo_seed": True,
                "auction_id": auction.id,
                "title": auction.title,
                "status": auction.status,
            },
        )
        return auction

    def _create_lot(
        self,
        *,
        auction,
        title,
        description,
        starting_price,
        reserve_price,
        bid_increment,
        status,
        images=None,
    ):
        lot = Lot.objects.create(
            auction=auction,
            title=title,
            description=description,
            images=images or [],
            starting_price=starting_price,
            current_price=starting_price,
            reserve_price=reserve_price,
            bid_increment=bid_increment,
            status=status,
        )
        self._audit(
            actor=auction.created_by,
            action=AuditAction.LOT_CREATED,
            entity_type="lot",
            entity_id=str(lot.id),
            metadata={
                "demo_seed": True,
                "lot_id": lot.id,
                "auction_id": auction.id,
                "title": lot.title,
                "starting_price": str(lot.starting_price),
                "status": lot.status,
            },
        )
        return lot

    def _audit(self, *, actor, action, entity_type, entity_id, metadata):
        AuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )
