from apps.auctions.services.lifecycle import (
    AuctionCloseResult,
    LotWinnerResult,
    close_due_auctions,
    sync_auction_lifecycle,
)

__all__ = (
    "AuctionCloseResult",
    "LotWinnerResult",
    "close_expired_auction",
    "close_expired_auctions",
)


def close_expired_auctions(*, now=None, limit: int | None = None) -> list[AuctionCloseResult]:
    return close_due_auctions(now=now, limit=limit)


def close_expired_auction(auction_id: int, *, now=None) -> AuctionCloseResult:
    return sync_auction_lifecycle(auction_id, now=now)
