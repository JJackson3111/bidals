from django.db.models import Q


PUBLIC_BROWSE_DEMO_AUCTION_TITLE_PREFIXES = (
    "[Demo]",
)
PUBLIC_BROWSE_DEMO_LOT_TITLE_PREFIXES = (
    "[Demo]",
)
PUBLIC_BROWSE_TEST_AUCTION_TITLE_PREFIXES = (
    "PHASE17",
    "[RC SMOKE]",
    "[STAGING TEST AUCTION]",
    "Test Auction",
    "BIDALS Demo Auction",
)
PUBLIC_BROWSE_TEST_AUCTION_TITLE_FRAGMENTS = (
    "BID FIX AUCTION",
    "REDIS SMOKE",
    "STAGING SMOKE",
)
PUBLIC_BROWSE_TEST_LOT_TITLE_PREFIXES = (
    "PHASE17",
    "[RC SMOKE]",
    "[DEMO LOT]",
    "Test Lot",
    "Test_",
)
PUBLIC_BROWSE_TEST_LOT_TITLE_FRAGMENTS = (
    "BID FIX LOT",
    "REDIS SMOKE",
    "STAGING SMOKE",
    "Test Sweet",
)


def public_browse_demo_auction_query(*, title_field: str = "title") -> Q:
    query = Q()

    for prefix in PUBLIC_BROWSE_DEMO_AUCTION_TITLE_PREFIXES:
        query |= Q(**{f"{title_field}__istartswith": prefix})

    return query


def public_browse_demo_lot_query(
    *,
    auction_title_field: str = "auction__title",
    lot_title_field: str = "title",
) -> Q:
    query = Q()

    for auction_prefix in PUBLIC_BROWSE_DEMO_AUCTION_TITLE_PREFIXES:
        for lot_prefix in PUBLIC_BROWSE_DEMO_LOT_TITLE_PREFIXES:
            query |= Q(**{f"{auction_title_field}__istartswith": auction_prefix}) & Q(
                **{f"{lot_title_field}__istartswith": lot_prefix}
            )

    return query


def public_browse_test_auction_query(*, title_field: str = "title") -> Q:
    query = Q()

    for prefix in PUBLIC_BROWSE_TEST_AUCTION_TITLE_PREFIXES:
        query |= Q(**{f"{title_field}__istartswith": prefix})

    for fragment in PUBLIC_BROWSE_TEST_AUCTION_TITLE_FRAGMENTS:
        query |= Q(**{f"{title_field}__icontains": fragment})

    return query & ~public_browse_demo_auction_query(title_field=title_field)


def public_browse_test_lot_query(
    *,
    auction_title_field: str = "auction__title",
    lot_title_field: str = "title",
) -> Q:
    query = public_browse_test_auction_query(title_field=auction_title_field)

    for prefix in PUBLIC_BROWSE_TEST_LOT_TITLE_PREFIXES:
        query |= Q(**{f"{lot_title_field}__istartswith": prefix})

    for fragment in PUBLIC_BROWSE_TEST_LOT_TITLE_FRAGMENTS:
        query |= Q(**{f"{lot_title_field}__icontains": fragment})

    return query & ~public_browse_demo_lot_query(
        auction_title_field=auction_title_field,
        lot_title_field=lot_title_field,
    )


def exclude_public_browse_test_auctions(queryset):
    return queryset.exclude(public_browse_test_auction_query())


def exclude_public_browse_test_lots(queryset):
    return queryset.exclude(public_browse_test_lot_query())
