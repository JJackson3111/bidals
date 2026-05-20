"use client";

import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Eye,
  Flame,
  Gavel,
  Minus,
  Plus,
  Search,
  TrendingUp,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { api, ApiError } from "@/lib/api";
import { getAuctionDisplayState, phaseFromAuctionStatus, type AuctionPhase } from "@/lib/auctionLifecycle";
import { formatMoney, getLotPrimaryImageUrl } from "@/lib/format";
import type { Auction, Bid, Lot } from "@/lib/types";

const FILTERS = [
  "All",
  "Live",
  "Ending soon",
  "Upcoming",
  "Art",
  "Travel",
  "Experiences",
  "Memorabilia",
];

const ONE_HOUR_MS = 60 * 60 * 1000;

type AuctionSummary = {
  auction: Auction;
  bidIncrement: number;
  bidderCount: number;
  bidsLastHour: number;
  currentBid: number;
  display: ReturnType<typeof getAuctionDisplayState>;
  featuredLot: Lot | null;
  imageUrls: string[];
  lots: Lot[];
  reserveMet: boolean;
  totalRaised: number;
  watcherCount: number;
};

export function BrowseAuctionsExperience() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [lots, setLots] = useState<Lot[]>([]);
  const [bidHistoryByLotId, setBidHistoryByLotId] = useState<Record<number, Bid[]>>({});
  const [activeFilter, setActiveFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lotError, setLotError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState<number | null>(null);
  const refreshInFlight = useRef(false);
  const lastLifecycleRefreshKey = useRef<string | null>(null);

  const loadBidSignals = useCallback(async (lotData: Lot[]) => {
    if (lotData.length === 0) {
      setBidHistoryByLotId({});
      return;
    }

    const settledHistories = await Promise.allSettled(
      lotData.map(async (lot) => {
        const bids = await api.getBidHistory(lot.id);
        return [lot.id, bids] as const;
      }),
    );

    const nextHistory: Record<number, Bid[]> = {};
    for (const result of settledHistories) {
      if (result.status === "fulfilled") {
        const [lotId, bids] = result.value;
        nextHistory[lotId] = bids;
      }
    }

    setBidHistoryByLotId(nextHistory);
  }, []);

  const loadBrowseData = useCallback(async ({ showLoading = true }: { showLoading?: boolean } = {}) => {
    if (showLoading) {
      setIsLoading(true);
      setError(null);
      setLotError(null);
    }

    try {
      const auctionData = await api.getAuctions();
      setAuctions(auctionData);

      try {
        const lotData = await api.getLots();
        setLots(lotData);
        setLotError(null);
        void loadBidSignals(lotData);
      } catch (err) {
        setLots([]);
        setBidHistoryByLotId({});
        setLotError(err instanceof ApiError ? err.message : "Unable to load lot details.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load auctions.");
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  }, [loadBidSignals]);

  useEffect(() => {
    void loadBrowseData();
  }, [loadBrowseData]);

  useEffect(() => {
    setNowMs(Date.now());
    const interval = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);

    return () => window.clearInterval(interval);
  }, []);

  const summaries = useMemo(
    () => buildAuctionSummaries({ auctions, bidHistoryByLotId, lots, nowMs }),
    [auctions, bidHistoryByLotId, lots, nowMs],
  );

  useEffect(() => {
    if (nowMs === null || summaries.length === 0) return;

    const staleAuction = summaries.find((summary) => {
      const statusPhase = phaseFromAuctionStatus(summary.auction.status);
      return statusPhase !== null && statusPhase !== summary.display.phase;
    });

    if (!staleAuction) return;

    const refreshKey = `${staleAuction.auction.id}:${staleAuction.auction.status}:${staleAuction.display.phase}`;
    if (lastLifecycleRefreshKey.current === refreshKey || refreshInFlight.current) return;

    lastLifecycleRefreshKey.current = refreshKey;
    refreshInFlight.current = true;
    loadBrowseData({ showLoading: false })
      .catch(() => undefined)
      .finally(() => {
        refreshInFlight.current = false;
      });
  }, [loadBrowseData, nowMs, summaries]);

  const visibleSummaries = useMemo(
    () => summaries.filter((summary) => matchesBrowseFilters(summary, activeFilter, searchQuery)),
    [activeFilter, searchQuery, summaries],
  );

  const liveCount = summaries.filter((summary) => summary.display.phase === "live").length;
  const upcomingCount = summaries.filter((summary) => summary.display.phase === "scheduled").length;
  const totalLots = summaries.reduce((sum, summary) => sum + summary.lots.length, 0);

  if (isLoading) {
    return (
      <main className="browse-page">
        <div className="browse-container">
          <LoadingState label="Loading auctions" />
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="browse-page">
        <div className="browse-container">
          <ErrorState message={error} />
        </div>
      </main>
    );
  }

  return (
    <main className="browse-page">
      <section className="browse-hero">
        <div className="browse-container">
          <div className="browse-hero-copy">
            <span className="eyebrow browse-eyebrow">Auction floor</span>
            <h1>Browse live auctions</h1>
            <p>
              Discover premium charity auctions, exclusive experiences, and curated lots built for confident,
              backend-authoritative bidding.
            </p>
          </div>

          <dl className="browse-hero-stats" aria-label="Browse summary">
            <div>
              <dt>Live now</dt>
              <dd>{liveCount}</dd>
            </div>
            <div>
              <dt>Upcoming</dt>
              <dd>{upcomingCount}</dd>
            </div>
            <div>
              <dt>Lots visible</dt>
              <dd>{totalLots}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="browse-toolbar" aria-label="Auction search and filters">
        <div className="browse-container">
          <div className="browse-search">
            <Search size={20} aria-hidden="true" />
            <label className="browse-sr-only" htmlFor="browse-auction-search">
              Search auctions
            </label>
            <input
              id="browse-auction-search"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search auctions..."
              type="search"
              value={searchQuery}
            />
          </div>

          <div className="browse-filters" role="list" aria-label="Auction filters">
            {FILTERS.map((filter) => (
              <button
                aria-pressed={activeFilter === filter}
                className={`browse-filter-button ${activeFilter === filter ? "is-active" : ""}`}
                key={filter}
                onClick={() => setActiveFilter(filter)}
                type="button"
              >
                {filter}
              </button>
            ))}
          </div>

          {lotError ? (
            <div className="browse-soft-alert" role="status">
              Lot details could not be loaded, so cards are showing auction-level information only. {lotError}
            </div>
          ) : null}
        </div>
      </section>

      <section className="browse-results" aria-label="Auction results">
        <div className="browse-container">
          {summaries.length === 0 ? (
            <EmptyState title="No auctions yet" message="New auctions will appear here when sellers publish them." />
          ) : visibleSummaries.length === 0 ? (
            <EmptyState title="No matching auctions" message="Adjust your search or filter to see more auctions." />
          ) : (
            <div className="browse-grid">
              {visibleSummaries.map((summary) => (
                <BrowseAuctionCard key={summary.auction.id} summary={summary} />
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function BrowseAuctionCard({ summary }: { summary: AuctionSummary }) {
  const [imageIndex, setImageIndex] = useState(0);
  const minimumBid = summary.currentBid + summary.bidIncrement;
  const [bidAmount, setBidAmount] = useState(minimumBid);

  useEffect(() => {
    setImageIndex(0);
    setBidAmount(minimumBid);
  }, [minimumBid, summary.auction.id]);

  const imageCount = getCardImageCount(summary);
  const activeImageUrl = summary.imageUrls[imageIndex] ?? null;
  const activeLot = summary.lots[imageIndex] ?? summary.featuredLot;
  const mediaLabel = activeLot?.title ?? summary.auction.title;
  const canStepImages = imageCount > 1;
  const canBid = summary.display.phase === "live" && Boolean(summary.featuredLot);
  const bidTargetHref = summary.featuredLot ? `/lots/${summary.featuredLot.id}` : `/auctions/${summary.auction.id}`;

  const handlePreviousImage = () => {
    setImageIndex((current) => (current > 0 ? current - 1 : imageCount - 1));
  };

  const handleNextImage = () => {
    setImageIndex((current) => (current + 1) % imageCount);
  };

  const handleDecreaseBid = () => {
    setBidAmount((current) => Math.max(minimumBid, current - summary.bidIncrement));
  };

  const handleIncreaseBid = () => {
    setBidAmount((current) => current + summary.bidIncrement);
  };

  return (
    <article className="browse-auction-card">
      <div className="browse-card-media">
        {activeImageUrl ? (
          <div
            aria-label={mediaLabel}
            className="browse-card-image"
            role="img"
            style={{ backgroundImage: `url("${activeImageUrl}")` }}
          />
        ) : (
          <div className="browse-card-placeholder" aria-hidden="true">
            <Gavel size={42} aria-hidden="true" />
            <span>{mediaLabel}</span>
          </div>
        )}

        <div className="browse-media-overlay" aria-hidden="true" />

        <span className="browse-lots-badge">{summary.lots.length} lots</span>
        <span className="browse-image-count">
          {imageIndex + 1}/{imageCount}
        </span>
        <span className={`browse-status-badge is-${summary.display.phase}`}>
          {summary.display.phase === "live" ? <span className="browse-live-dot" aria-hidden="true" /> : null}
          {summary.display.badgeLabel}
        </span>

        {canStepImages ? (
          <div className="browse-media-controls">
            <button
              aria-label={`Previous image for ${summary.auction.title}`}
              onClick={handlePreviousImage}
              type="button"
            >
              <ChevronLeft size={18} aria-hidden="true" />
            </button>
            <button
              aria-label={`Next image for ${summary.auction.title}`}
              onClick={handleNextImage}
              type="button"
            >
              <ChevronRight size={18} aria-hidden="true" />
            </button>
          </div>
        ) : null}
      </div>

      <div className="browse-card-body">
        <div className="browse-card-heading">
          <Link className="browse-card-title-link" href={`/auctions/${summary.auction.id}`}>
            <h2>{summary.auction.title}</h2>
          </Link>
          <p>{summary.auction.description || "No description provided."}</p>
        </div>

        <div className="browse-value-row">
          <div>
            <span>{summary.display.phase === "scheduled" ? "Starting value" : "Raised value"}</span>
            <strong>{formatWholeMoney(summary.totalRaised)}</strong>
          </div>
          <div className="browse-time-pill">
            <Clock size={15} aria-hidden="true" />
            <span>{formatAuctionTime(summary.auction, summary.display.phase)}</span>
          </div>
        </div>

        <div className="browse-signal-grid" aria-label={`Auction signals for ${summary.auction.title}`}>
          <span>
            <Users size={14} aria-hidden="true" />
            {summary.bidderCount} bidders
          </span>
          <span>
            <Eye size={14} aria-hidden="true" />
            {summary.watcherCount} watching
          </span>
          <span>
            <TrendingUp size={14} aria-hidden="true" />
            {summary.bidsLastHour} bids/hr
          </span>
          <span className={summary.reserveMet ? "is-accent" : ""}>
            <CheckCircle2 size={14} aria-hidden="true" />
            {summary.reserveMet ? "Reserve met" : "Reserve pending"}
          </span>
          <span className="is-accent">
            <BadgeCheck size={14} aria-hidden="true" />
            Verified seller
          </span>
          {summary.bidsLastHour >= 3 ? (
            <span className="is-accent">
              <Flame size={14} aria-hidden="true" />
              Trending
            </span>
          ) : null}
        </div>

        <div className="browse-bid-module">
          <div className="browse-bid-module-header">
            <span>Quick bid</span>
            <small>Increment {formatWholeMoney(summary.bidIncrement)}</small>
          </div>

          <div className="browse-bid-controls">
            <button
              aria-label={`Decrease bid amount for ${summary.auction.title}`}
              disabled={!canBid || bidAmount <= minimumBid}
              onClick={handleDecreaseBid}
              type="button"
            >
              <Minus size={16} aria-hidden="true" />
            </button>
            <label className="browse-bid-input">
              <span>Bid amount</span>
              <input
                aria-describedby={`browse-bid-note-${summary.auction.id}`}
                inputMode="decimal"
                readOnly
                type="text"
                value={formatWholeMoney(bidAmount)}
              />
            </label>
            <button
              aria-label={`Increase bid amount for ${summary.auction.title}`}
              disabled={!canBid}
              onClick={handleIncreaseBid}
              type="button"
            >
              <Plus size={16} aria-hidden="true" />
            </button>
          </div>

          <small className="browse-bid-note" id={`browse-bid-note-${summary.auction.id}`}>
            Final bid acceptance happens on the secure lot page.
          </small>

          {canBid ? (
            <Link className="browse-primary-bid" href={bidTargetHref}>
              Place bid
            </Link>
          ) : (
            <button className="browse-primary-bid" disabled type="button">
              Place bid
            </button>
          )}
        </div>

        <Link className="browse-open-link" href={`/auctions/${summary.auction.id}`}>
          Open auction
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </div>
    </article>
  );
}

function buildAuctionSummaries({
  auctions,
  bidHistoryByLotId,
  lots,
  nowMs,
}: {
  auctions: Auction[];
  bidHistoryByLotId: Record<number, Bid[]>;
  lots: Lot[];
  nowMs: number | null;
}): AuctionSummary[] {
  return auctions.map((auction) => {
    const auctionLots = lots.filter((lot) => lot.auction === auction.id);
    const featuredLot = chooseFeaturedLot(auctionLots);
    const currentBid = Math.max(0, ...auctionLots.map((lot) => parseMoney(lot.current_price)));
    const totalRaised = auctionLots.reduce((sum, lot) => sum + parseMoney(lot.current_price), 0);
    const bidIncrement = Math.max(1, parseMoney(featuredLot?.bid_increment ?? "50"));
    const acceptedBids = auctionLots.flatMap((lot) => (
      bidHistoryByLotId[lot.id] ?? []
    ).filter((bid) => bid.status === "accepted"));
    const bidderKeys = acceptedBids.map((bid) => String(bid.bidder || bid.bidder_username)).filter(Boolean);
    const bidders = new Set(bidderKeys);
    const display = getAuctionDisplayState(auction, nowMs);
    const bidsLastHour = acceptedBids.filter((bid) => {
      const bidMs = new Date(bid.server_timestamp).getTime();
      return Number.isFinite(bidMs) && Date.now() - bidMs <= ONE_HOUR_MS;
    }).length;
    const watcherCount = Math.max(0, bidders.size + Math.max(0, auctionLots.length - 1));
    const reserveMet = auctionLots.some((lot) => {
      const reserve = lot.reserve_price ? parseMoney(lot.reserve_price) : null;
      return reserve !== null && parseMoney(lot.current_price) >= reserve;
    });
    const imageUrls = auctionLots.flatMap((lot) => getLotImageUrls(lot));

    return {
      auction,
      bidIncrement,
      bidderCount: bidders.size,
      bidsLastHour,
      currentBid,
      display,
      featuredLot,
      imageUrls,
      lots: auctionLots,
      reserveMet,
      totalRaised,
      watcherCount,
    };
  });
}

function chooseFeaturedLot(lots: Lot[]): Lot | null {
  if (lots.length === 0) return null;

  const openLots = lots.filter((lot) => lot.status === "open");
  const candidates = openLots.length > 0 ? openLots : lots;
  return [...candidates].sort((first, second) => parseMoney(second.current_price) - parseMoney(first.current_price))[0] ?? null;
}

function getLotImageUrls(lot: Lot): string[] {
  const uploadedUrls = lot.uploaded_images?.map((image) => image.image_url).filter(Boolean) ?? [];
  const legacyUrls = lot.images?.filter(Boolean) ?? [];
  const primary = getLotPrimaryImageUrl(lot);
  return Array.from(new Set([primary, ...uploadedUrls, ...legacyUrls].filter(Boolean) as string[]));
}

function getCardImageCount(summary: AuctionSummary): number {
  if (summary.imageUrls.length > 0) return summary.imageUrls.length;
  return Math.max(1, Math.min(summary.lots.length || 1, 4));
}

function matchesBrowseFilters(summary: AuctionSummary, activeFilter: string, searchQuery: string): boolean {
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const haystack = [
    summary.auction.title,
    summary.auction.description,
    summary.auction.created_by_username,
    ...summary.lots.flatMap((lot) => [lot.title, lot.description]),
  ].join(" ").toLowerCase();

  if (normalizedSearch && !haystack.includes(normalizedSearch)) {
    return false;
  }

  if (activeFilter === "All") return true;
  if (activeFilter === "Live") return summary.display.phase === "live";
  if (activeFilter === "Upcoming") return summary.display.phase === "scheduled";
  if (activeFilter === "Ending soon") {
    const endMs = new Date(summary.auction.end_time).getTime();
    return summary.display.phase === "live" && Number.isFinite(endMs) && endMs - Date.now() <= ONE_HOUR_MS;
  }

  return haystack.includes(activeFilter.toLowerCase());
}

function formatAuctionTime(auction: Auction, phase: AuctionPhase): string {
  if (phase === "closed") return "Closed";
  if (phase === "cancelled") return "Cancelled";
  if (phase === "draft") return "Draft";

  const target = phase === "scheduled" ? auction.start_time : auction.end_time;
  const prefix = phase === "scheduled" ? "Starts in" : "Ends in";
  const diffMs = new Date(target).getTime() - Date.now();
  if (!Number.isFinite(diffMs) || diffMs <= 0) return phase === "scheduled" ? "Starting soon" : "Closing";

  const totalSeconds = Math.floor(diffMs / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);

  if (days > 0) return `${prefix} ${days}d ${hours}h`;
  if (hours > 0) return `${prefix} ${hours}h ${minutes}m`;
  return `${prefix} ${Math.max(0, minutes)}m`;
}

function parseMoney(value: string | number): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatWholeMoney(value: string | number): string {
  const numeric = parseMoney(value);
  if (!Number.isFinite(numeric)) return formatMoney(value);

  return new Intl.NumberFormat("en-US", {
    currency: "USD",
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
    style: "currency",
  }).format(numeric);
}
