"use client";

import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  Camera,
  ChevronLeft,
  ChevronRight,
  Clock,
  Gift,
  Heart,
  Minus,
  Plus,
  Share2,
  Sparkles,
  Ticket,
  Trophy,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MutableRefObject } from "react";

import { useAuth } from "@/components/AuthProvider";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { api, ApiError } from "@/lib/api";
import { getAuctionDisplayState, phaseFromAuctionStatus, type AuctionPhase } from "@/lib/auctionLifecycle";
import { formatMoney } from "@/lib/format";
import type { Auction, Bid, Lot } from "@/lib/types";

const ONE_HOUR_MS = 60 * 60 * 1000;
const DEFAULT_TARGET_AMOUNT = 10000;
const DEMO_LOT_IMAGE_BASE_PATH = "/demo-lots";
const API_LOT_IMAGE_FIELD_KEYS = [
  "image_url",
  "imageUrl",
  "cover_image",
  "coverImage",
  "cover_image_url",
  "coverImageUrl",
  "image",
  "primary_image",
  "primaryImage",
  "primary_image_url",
  "primaryImageUrl",
  "hero_image",
  "heroImage",
  "media_url",
  "mediaUrl",
  "thumbnail_url",
  "thumbnailUrl",
] as const;
const API_LOT_IMAGE_COLLECTION_KEYS = [
  "uploaded_images",
  "images",
  "media",
  "photos",
  "gallery",
  "image_urls",
  "imageUrls",
  "lot_images",
  "lotImages",
] as const;
const API_LOT_IMAGE_OBJECT_KEYS = [
  "image_url",
  "imageUrl",
  "url",
  "src",
  "source",
  "cover_image",
  "coverImage",
  "media_url",
  "mediaUrl",
  "thumbnail_url",
  "thumbnailUrl",
] as const;
const STAGING_DEMO_LOT_IMAGE_FALLBACKS = [
  {
    titleFragment: "starter",
    imageUrls: [
      `${DEMO_LOT_IMAGE_BASE_PATH}/wine-hero.webp`,
      `${DEMO_LOT_IMAGE_BASE_PATH}/wine-detail.webp`,
      `${DEMO_LOT_IMAGE_BASE_PATH}/wine-lifestyle.webp`,
    ],
  },
  {
    titleFragment: "reserve",
    imageUrls: [
      `${DEMO_LOT_IMAGE_BASE_PATH}/watch-hero.webp`,
      `${DEMO_LOT_IMAGE_BASE_PATH}/watch-detail.webp`,
      `${DEMO_LOT_IMAGE_BASE_PATH}/watch-box.webp`,
    ],
  },
  {
    titleFragment: "increment",
    imageUrls: [
      `${DEMO_LOT_IMAGE_BASE_PATH}/vacation-resort.webp`,
      `${DEMO_LOT_IMAGE_BASE_PATH}/vacation-room.webp`,
      `${DEMO_LOT_IMAGE_BASE_PATH}/vacation-spa.webp`,
      `${DEMO_LOT_IMAGE_BASE_PATH}/vacation-dinner.webp`,
    ],
  },
] as const;

type LotBidState = {
  acceptedBids: Bid[];
  bidderCount: number;
  hasUserBid: boolean;
  highestBid: Bid | null;
  isOutbid: boolean;
  userBidCount: number;
  watcherCount: number;
};

type EventHub = {
  amountRemaining: number;
  auction: Auction;
  bidCount: number;
  bidderCount: number;
  bidsLastHour: number;
  bidsMade: number;
  display: ReturnType<typeof getAuctionDisplayState>;
  lotBidStates: Record<number, LotBidState>;
  lots: Lot[];
  progressPercent: number;
  raffleTickets: number;
  targetAmount: number;
  totalRaised: number;
  watcherCount: number;
  wonLots: number;
};

export function BrowseAuctionsExperience() {
  const { user } = useAuth();
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [lots, setLots] = useState<Lot[]>([]);
  const [bidHistoryByLotId, setBidHistoryByLotId] = useState<Record<number, Bid[]>>({});
  const [likedLotIds, setLikedLotIds] = useState<number[]>([]);
  const [selectedLotId, setSelectedLotId] = useState<number | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [actionMessage, setActionMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lotError, setLotError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState<number | null>(null);
  const detailRef = useRef<HTMLElement | null>(null);
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

  const selectedAuction = useMemo(
    () => selectPrimaryAuction(auctions, nowMs),
    [auctions, nowMs],
  );

  const eventHub = useMemo(
    () => selectedAuction
      ? buildEventHub({
        auction: selectedAuction,
        bidHistoryByLotId,
        lots: lots.filter((lot) => lot.auction === selectedAuction.id),
        nowMs,
        userId: user?.id ?? null,
      })
      : null,
    [bidHistoryByLotId, lots, nowMs, selectedAuction, user?.id],
  );
  const selectedAuctionId = selectedAuction?.id ?? null;

  useEffect(() => {
    if (selectedAuctionId === null) {
      setLikedLotIds([]);
      return;
    }

    setLikedLotIds(readLikedLots(selectedAuctionId));
  }, [selectedAuctionId]);

  useEffect(() => {
    if (!eventHub) {
      setSelectedLotId(null);
      return;
    }

    const selectedStillVisible = selectedLotId !== null && eventHub.lots.some((lot) => lot.id === selectedLotId);
    if (!selectedStillVisible) {
      setSelectedLotId(eventHub.lots[0]?.id ?? null);
    }
  }, [eventHub, selectedLotId]);

  useEffect(() => {
    if (!eventHub || nowMs === null) return;

    const statusPhase = phaseFromAuctionStatus(eventHub.auction.status);
    const backendLooksStale = statusPhase !== null && statusPhase !== eventHub.display.phase;
    if (!backendLooksStale) return;

    const refreshKey = `${eventHub.auction.id}:${eventHub.auction.status}:${eventHub.display.phase}`;
    if (lastLifecycleRefreshKey.current === refreshKey || refreshInFlight.current) return;

    lastLifecycleRefreshKey.current = refreshKey;
    refreshInFlight.current = true;
    loadBrowseData({ showLoading: false })
      .catch(() => undefined)
      .finally(() => {
        refreshInFlight.current = false;
      });
  }, [eventHub, loadBrowseData, nowMs]);

  const selectedLot = useMemo(
    () => eventHub?.lots.find((lot) => lot.id === selectedLotId) ?? eventHub?.lots[0] ?? null,
    [eventHub, selectedLotId],
  );

  const likedLots = useMemo(
    () => eventHub?.lots.filter((lot) => likedLotIds.includes(lot.id)) ?? [],
    [eventHub, likedLotIds],
  );

  const handleSelectLot = useCallback((lotId: number) => {
    setSelectedLotId(lotId);
    setSelectedImageIndex(0);
    window.requestAnimationFrame(() => {
      detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      detailRef.current?.focus({ preventScroll: true });
    });
  }, []);

  const handleToggleLikedLot = useCallback((lotId: number) => {
    if (!eventHub) return;

    setLikedLotIds((current) => {
      const next = current.includes(lotId)
        ? current.filter((id) => id !== lotId)
        : [...current, lotId];
      writeLikedLots(eventHub.auction.id, next);
      return next;
    });
  }, [eventHub]);

  const handleShare = useCallback(async () => {
    if (!eventHub) return;

    const shareUrl = `${window.location.origin}/auctions/${eventHub.auction.id}`;
    try {
      if (navigator.share) {
        await navigator.share({
          title: eventHub.auction.title,
          text: eventHub.auction.description || "View this BIDALS event.",
          url: shareUrl,
        });
        setActionMessage("Event shared.");
        return;
      }

      await navigator.clipboard?.writeText(shareUrl);
      setActionMessage("Event link copied.");
    } catch {
      setActionMessage("Share was not completed.");
    }
  }, [eventHub]);

  if (isLoading) {
    return (
      <main className="browse-page">
        <div className="browse-container">
          <LoadingState label="Loading event" />
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

  if (!eventHub) {
    return (
      <main className="browse-page">
        <div className="browse-container">
          <EmptyState title="No active event" message="A live or scheduled auction event will appear here." />
        </div>
      </main>
    );
  }

  const eventLogoUrl = getOptionalStringField(eventHub.auction, ["logo_url", "event_logo", "customer_logo_url"]);

  return (
    <main className="browse-page browse-event-page">
      <section className="browse-event-hero">
        <div className="browse-container">
          <div className="browse-event-summary">
            <section className="browse-event-summary-top" aria-label="Your event stats">
              <div className="browse-event-logo" aria-label={`${eventHub.auction.title} logo`}>
                {eventLogoUrl ? (
                  <span style={{ backgroundImage: `url("${eventLogoUrl}")` }} />
                ) : (
                  <Camera size={30} strokeWidth={1.7} aria-hidden="true" />
                )}
              </div>

              <EventStat icon={Sparkles} label="Bids made" value={eventHub.bidsMade} />
              <EventStat icon={Ticket} label="Raffles" value={eventHub.raffleTickets} />
              <EventStat icon={Trophy} label="Won lots" value={eventHub.wonLots} />
            </section>

            <section className="browse-progress-compact" aria-label="Fundraising progress">
              <div className="browse-progress-compact-header">
                <span>Donation target</span>
                <strong>{formatWholeMoney(eventHub.targetAmount)}</strong>
              </div>
              <div className="browse-progress-compact-track" aria-hidden="true">
                <span style={{ width: `${eventHub.progressPercent}%` }} />
              </div>
              <div className="browse-progress-compact-footer">
                <span>{formatWholeMoney(eventHub.totalRaised)} raised</span>
                <strong>{formatWholeMoney(eventHub.amountRemaining)} remaining</strong>
              </div>
            </section>

            <div className="browse-event-copy">
              <span className={`browse-event-status is-${eventHub.display.phase}`}>
                {eventHub.display.phase === "live" ? <i aria-hidden="true" /> : null}
                {eventHub.display.badgeLabel}
              </span>
              <h1>{eventHub.auction.title}</h1>
              <p>{eventHub.auction.description || "Bid generously across curated lots supporting this fundraising event."}</p>
            </div>
          </div>
        </div>
      </section>

      <div className="browse-container browse-event-stack">
        <section className="browse-event-actions" aria-label="Event actions">
          <button type="button" onClick={() => setActionMessage("Donation checkout is not enabled for this event yet.")}>
            <Gift size={18} aria-hidden="true" />
            Donate
          </button>
          <button type="button" onClick={() => setActionMessage("Raffle tickets are not enabled for this event yet.")}>
            <Ticket size={18} aria-hidden="true" />
            Raffle Tickets
          </button>
          <button type="button" onClick={handleShare}>
            <Share2 size={18} aria-hidden="true" />
            Share
          </button>
          <span className="browse-action-status" role="status">{actionMessage}</span>
        </section>

        {lotError ? (
          <div className="browse-soft-alert" role="status">
            Lot details could not be loaded. {lotError}
          </div>
        ) : null}

        <section className="browse-liked-section" aria-labelledby="browse-liked-title">
          <div className="browse-section-heading">
            <span>Saved for later</span>
            <h2 id="browse-liked-title">Liked lots</h2>
          </div>
          <div className="browse-liked-strip">
            {likedLots.length > 0 ? (
              likedLots.map((lot) => (
                <LikedLotCard
                  bidState={eventHub.lotBidStates[lot.id]}
                  key={lot.id}
                  lot={lot}
                  onSelect={handleSelectLot}
                />
              ))
            ) : (
              <div className="browse-liked-empty">
                <Heart size={18} aria-hidden="true" />
                <span>Tap hearts on lots to build your shortlist.</span>
              </div>
            )}
          </div>
        </section>

        {selectedLot ? (
          <SelectedLotPanel
            bidState={eventHub.lotBidStates[selectedLot.id]}
            detailRef={detailRef}
            imageIndex={selectedImageIndex}
            lot={selectedLot}
            onImageIndexChange={setSelectedImageIndex}
            phase={eventHub.display.phase}
            timeLabel={formatAuctionTime(eventHub.auction, eventHub.display.phase)}
          />
        ) : null}

        <section className="browse-lot-feed" aria-labelledby="browse-lot-feed-title">
          <div className="browse-section-heading">
            <span>{eventHub.lots.length} lots in this event</span>
            <h2 id="browse-lot-feed-title">Bid the room</h2>
          </div>

          {eventHub.lots.length === 0 ? (
            <EmptyState title="No lots visible" message="Lots will appear here when this event opens them." />
          ) : (
            <div className="browse-lot-grid">
              {eventHub.lots.map((lot) => (
                <LotTile
                  bidState={eventHub.lotBidStates[lot.id]}
                  isLiked={likedLotIds.includes(lot.id)}
                  isSelected={selectedLot?.id === lot.id}
                  key={lot.id}
                  lot={lot}
                  onSelect={handleSelectLot}
                  onToggleLiked={handleToggleLikedLot}
                  timeLabel={formatAuctionTime(eventHub.auction, eventHub.display.phase)}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function EventStat({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
}) {
  return (
    <div className="browse-stat-card">
      <strong>{value}</strong>
      <span>{label}</span>
      <Icon size={16} aria-hidden="true" />
    </div>
  );
}

function LikedLotCard({
  bidState,
  lot,
  onSelect,
}: {
  bidState: LotBidState;
  lot: Lot;
  onSelect: (lotId: number) => void;
}) {
  const imageUrl = getResolvedLotPrimaryImageUrl(lot);

  return (
    <button className={`browse-liked-card ${bidState.isOutbid ? "is-outbid" : ""}`} onClick={() => onSelect(lot.id)} type="button">
      <LotImage imageUrl={imageUrl} isOutbid={bidState.isOutbid} label={lot.title} />
      {bidState.isOutbid ? <span className="browse-outbid-badge browse-liked-outbid-badge">Outbid</span> : null}
      <span className="browse-liked-title">{lot.title}</span>
      <strong>{formatWholeMoney(lot.current_price)}</strong>
    </button>
  );
}

function LotTile({
  bidState,
  isLiked,
  isSelected,
  lot,
  onSelect,
  onToggleLiked,
  timeLabel,
}: {
  bidState: LotBidState;
  isLiked: boolean;
  isSelected: boolean;
  lot: Lot;
  onSelect: (lotId: number) => void;
  onToggleLiked: (lotId: number) => void;
  timeLabel: string;
}) {
  const imageUrl = getResolvedLotPrimaryImageUrl(lot);

  return (
    <article className={`browse-lot-tile ${bidState.isOutbid ? "is-outbid" : ""} ${isSelected ? "is-selected" : ""}`}>
      <button className="browse-lot-tile-button" onClick={() => onSelect(lot.id)} type="button">
        <LotImage imageUrl={imageUrl} isOutbid={bidState.isOutbid} label={lot.title} />
        <span className={`browse-lot-status ${bidState.isOutbid ? "status-outbid" : `status-${lot.status}`}`}>
          {bidState.isOutbid ? "Outbid" : lot.status}
        </span>
        <div className="browse-lot-tile-body">
          <h3>{lot.title}</h3>
          <div>
            <strong>{formatWholeMoney(lot.current_price)}</strong>
            <span>
              <Clock size={12} aria-hidden="true" />
              {timeLabel}
            </span>
          </div>
        </div>
      </button>
      <button
        aria-label={`${isLiked ? "Remove" : "Save"} ${lot.title}`}
        aria-pressed={isLiked}
        className={`browse-save-lot ${isLiked ? "is-liked" : ""}`}
        onClick={() => onToggleLiked(lot.id)}
        type="button"
      >
        <Heart size={16} aria-hidden="true" />
      </button>
    </article>
  );
}

function SelectedLotPanel({
  bidState,
  detailRef,
  imageIndex,
  lot,
  onImageIndexChange,
  phase,
  timeLabel,
}: {
  bidState: LotBidState;
  detailRef: MutableRefObject<HTMLElement | null>;
  imageIndex: number;
  lot: Lot;
  onImageIndexChange: (index: number) => void;
  phase: AuctionPhase;
  timeLabel: string;
}) {
  const imageUrls = getResolvedLotImageUrls(lot);
  const imageCount = Math.max(1, imageUrls.length);
  const activeImageIndex = imageUrls.length > 0 ? Math.min(imageIndex, imageUrls.length - 1) : 0;
  const activeImageUrl = imageUrls[activeImageIndex] ?? null;
  const minimumBid = parseMoney(lot.current_price) + parseMoney(lot.bid_increment);
  const [bidAmount, setBidAmount] = useState(minimumBid);
  const buyNowPrice = getOptionalMoneyField(lot, ["buy_now_price", "buyNowPrice", "buy_now"]);
  const canBid = phase === "live" && lot.status === "open";

  useEffect(() => {
    onImageIndexChange(0);
    setBidAmount(minimumBid);
  }, [lot.id, minimumBid, onImageIndexChange]);

  const handlePreviousImage = () => {
    onImageIndexChange(imageIndex > 0 ? imageIndex - 1 : imageCount - 1);
  };

  const handleNextImage = () => {
    onImageIndexChange((imageIndex + 1) % imageCount);
  };

  return (
    <section
      className={`browse-lot-detail ${bidState.isOutbid ? "is-outbid" : ""}`}
      ref={detailRef}
      tabIndex={-1}
      aria-label={`Selected lot: ${lot.title}`}
    >
      <div className="browse-detail-media">
        <LotImage imageUrl={activeImageUrl} isOutbid={bidState.isOutbid} label={lot.title} />
        <span className="browse-image-counter">
          {activeImageIndex + 1}/{imageCount}
        </span>
        {bidState.isOutbid ? <span className="browse-outbid-badge">Outbid</span> : null}
        {imageCount > 1 ? (
          <div className="browse-detail-carousel">
            <button aria-label={`Previous image for ${lot.title}`} onClick={handlePreviousImage} type="button">
              <ChevronLeft size={18} aria-hidden="true" />
            </button>
            <button aria-label={`Next image for ${lot.title}`} onClick={handleNextImage} type="button">
              <ChevronRight size={18} aria-hidden="true" />
            </button>
          </div>
        ) : null}
      </div>

      <div className="browse-detail-body">
        <div className="browse-detail-heading">
          <span className="browse-detail-kicker">Selected lot</span>
          <h2>{lot.title}</h2>
          <p>{lot.description || lot.auction_title}</p>
        </div>

        <dl className="browse-detail-metrics">
          <div>
            <dt>Current bid</dt>
            <dd>{formatWholeMoney(lot.current_price)}</dd>
          </div>
          {buyNowPrice !== null ? (
            <div>
              <dt>Buy now</dt>
              <dd>{formatWholeMoney(buyNowPrice)}</dd>
            </div>
          ) : null}
          <div>
            <dt>Timer</dt>
            <dd>{timeLabel}</dd>
          </div>
          <div>
            <dt>Bidders</dt>
            <dd>{bidState.bidderCount}</dd>
          </div>
          <div>
            <dt>Watching</dt>
            <dd>{bidState.watcherCount}</dd>
          </div>
        </dl>

        {bidState.isOutbid ? (
          <p className="browse-outbid-note">You have been outbid. Open the secure lot page to place your next bid.</p>
        ) : null}

        <div className="browse-detail-bid">
          <div className="browse-detail-bid-header">
            <span>Bid amount</span>
            <small>Increment {formatWholeMoney(lot.bid_increment)}</small>
          </div>
          <div className="browse-detail-bid-row">
            <button
              aria-label={`Decrease bid amount for ${lot.title}`}
              disabled={!canBid || bidAmount <= minimumBid}
              onClick={() => setBidAmount((current) => Math.max(minimumBid, current - parseMoney(lot.bid_increment)))}
              type="button"
            >
              <Minus size={16} aria-hidden="true" />
            </button>
            <label>
              <span>Bid amount</span>
              <input inputMode="decimal" readOnly type="text" value={formatWholeMoney(bidAmount)} />
            </label>
            <button
              aria-label={`Increase bid amount for ${lot.title}`}
              disabled={!canBid}
              onClick={() => setBidAmount((current) => current + parseMoney(lot.bid_increment))}
              type="button"
            >
              <Plus size={16} aria-hidden="true" />
            </button>
          </div>
          <Link className="browse-place-bid" href={`/lots/${lot.id}`}>
            Place bid
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </div>
    </section>
  );
}

function LotImage({
  imageUrl,
  isOutbid,
  label,
}: {
  imageUrl: string | null;
  isOutbid?: boolean;
  label: string;
}) {
  return imageUrl ? (
    <span className={`browse-lot-image ${isOutbid ? "is-outbid" : ""}`}>
      <Image
        alt={label}
        className="browse-lot-image-fill"
        fill
        sizes="(min-width: 1080px) 25vw, (min-width: 720px) 50vw, 100vw"
        src={imageUrl}
        unoptimized
      />
    </span>
  ) : (
    <span className={`browse-lot-image browse-lot-placeholder ${isOutbid ? "is-outbid" : ""}`} aria-hidden="true">
      <BadgeCheck size={26} aria-hidden="true" />
      <span>{label.slice(0, 1).toUpperCase()}</span>
    </span>
  );
}

function selectPrimaryAuction(auctions: Auction[], nowMs: number | null): Auction | null {
  if (auctions.length === 0) return null;

  return [...auctions].sort((first, second) => {
    const firstDisplay = getAuctionDisplayState(first, nowMs);
    const secondDisplay = getAuctionDisplayState(second, nowMs);
    const phaseDelta = phaseRank(firstDisplay.phase) - phaseRank(secondDisplay.phase);
    if (phaseDelta !== 0) return phaseDelta;

    const firstTime = new Date(firstDisplay.phase === "scheduled" ? first.start_time : first.end_time).getTime();
    const secondTime = new Date(secondDisplay.phase === "scheduled" ? second.start_time : second.end_time).getTime();
    return safeTime(firstTime) - safeTime(secondTime);
  })[0] ?? null;
}

function buildEventHub({
  auction,
  bidHistoryByLotId,
  lots,
  nowMs,
  userId,
}: {
  auction: Auction;
  bidHistoryByLotId: Record<number, Bid[]>;
  lots: Lot[];
  nowMs: number | null;
  userId: number | null;
}): EventHub {
  const display = getAuctionDisplayState(auction, nowMs);
  const lotBidStates: Record<number, LotBidState> = {};
  const acceptedBids = lots.flatMap((lot) => {
    const bidState = getLotBidStatus(lot, bidHistoryByLotId[lot.id] ?? [], userId);
    lotBidStates[lot.id] = bidState;
    return bidState.acceptedBids;
  });
  const bidderCount = new Set(acceptedBids.map((bid) => bid.bidder || bid.bidder_username).filter(Boolean)).size;
  const totalRaised = lots.reduce((sum, lot) => sum + parseMoney(lot.current_price), 0);
  const providedTargetAmount = getOptionalMoneyField(auction, ["donation_target", "fundraising_target", "target_amount"]);
  // TODO: Remove this derived display fallback once every event exposes a fundraising target.
  const targetAmount = providedTargetAmount && providedTargetAmount > 0 ? providedTargetAmount : deriveTargetAmount(lots, totalRaised);
  const amountRemaining = Math.max(0, targetAmount - totalRaised);
  const progressPercent = targetAmount > 0 ? Math.min(100, Math.round((totalRaised / targetAmount) * 100)) : 0;
  const userAcceptedBids = userId === null ? [] : acceptedBids.filter((bid) => bid.bidder === userId);
  const bidsLastHour = acceptedBids.filter((bid) => {
    const bidMs = new Date(bid.server_timestamp).getTime();
    return Number.isFinite(bidMs) && (nowMs ?? Date.now()) - bidMs <= ONE_HOUR_MS;
  }).length;

  return {
    amountRemaining,
    auction,
    bidCount: acceptedBids.length,
    bidderCount,
    bidsLastHour,
    bidsMade: userAcceptedBids.length,
    display,
    lotBidStates,
    lots,
    progressPercent,
    // TODO: Replace with API-provided raffle tickets sold/purchased for this bidder/event.
    raffleTickets: 0,
    targetAmount,
    totalRaised,
    watcherCount: lots.reduce((sum, lot) => sum + (lotBidStates[lot.id]?.watcherCount ?? 0), 0),
    wonLots: userId === null ? 0 : lots.filter((lot) => lot.winner === userId).length,
  };
}

function getLotBidStatus(lot: Lot, bids: Bid[], userId: number | null): LotBidState {
  const acceptedBids = bids.filter((bid) => bid.status === "accepted");
  const highestBid = getHighestAcceptedBid(acceptedBids);
  const userBids = userId === null ? [] : acceptedBids.filter((bid) => bid.bidder === userId);
  const userHighestBid = Math.max(0, ...userBids.map((bid) => parseMoney(bid.amount)));
  const highestAmount = Math.max(highestBid ? parseMoney(highestBid.amount) : 0, parseMoney(lot.current_price));
  const bidderCount = new Set(acceptedBids.map((bid) => bid.bidder || bid.bidder_username).filter(Boolean)).size;
  // TODO: If bid history becomes unavailable or partial, prefer backend fields such as
  // has_user_bid, is_user_highest_bidder, user_highest_bid_amount, current_highest_bidder_id,
  // and current_bid_amount instead of guessing an outbid state.

  return {
    acceptedBids,
    bidderCount,
    hasUserBid: userBids.length > 0,
    highestBid,
    isOutbid: isLotOutbidForCurrentUser({
      highestAmount,
      highestBid,
      userBids,
      userHighestBid,
      userId,
    }),
    userBidCount: userBids.length,
    watcherCount: Math.max(1, bidderCount * 2 + (acceptedBids.length > 0 ? 1 : 0)),
  };
}

function getHighestAcceptedBid(acceptedBids: Bid[]): Bid | null {
  return [...acceptedBids].sort(compareBidsByRank)[0] ?? null;
}

function compareBidsByRank(first: Bid, second: Bid): number {
  const amountDelta = parseMoney(second.amount) - parseMoney(first.amount);
  if (amountDelta !== 0) return amountDelta;

  const firstMs = new Date(first.server_timestamp).getTime();
  const secondMs = new Date(second.server_timestamp).getTime();
  if (Number.isFinite(firstMs) && Number.isFinite(secondMs) && secondMs !== firstMs) {
    return secondMs - firstMs;
  }

  return second.id - first.id;
}

function isLotOutbidForCurrentUser({
  highestAmount,
  highestBid,
  userBids,
  userHighestBid,
  userId,
}: {
  highestAmount: number;
  highestBid: Bid | null;
  userBids: Bid[];
  userHighestBid: number;
  userId: number | null;
}): boolean {
  if (userId === null || userBids.length === 0) return false;

  const currentBidIsHigherThanUserBid = highestAmount > userHighestBid;
  const highestBidBelongsToAnotherBidder = highestBid !== null && highestBid.bidder !== userId;
  return currentBidIsHigherThanUserBid || highestBidBelongsToAnotherBidder;
}

function phaseRank(phase: AuctionPhase): number {
  if (phase === "live") return 0;
  if (phase === "scheduled") return 1;
  if (phase === "closed") return 2;
  if (phase === "draft") return 3;
  return 4;
}

function safeTime(value: number): number {
  return Number.isFinite(value) ? value : Number.MAX_SAFE_INTEGER;
}

function deriveTargetAmount(lots: Lot[], totalRaised: number): number {
  const reserveTotal = lots.reduce((sum, lot) => sum + parseMoney(lot.reserve_price ?? 0), 0);
  const startingTotal = lots.reduce((sum, lot) => sum + parseMoney(lot.starting_price), 0);
  const base = Math.max(reserveTotal, startingTotal, totalRaised * 1.5, DEFAULT_TARGET_AMOUNT);
  return Math.ceil(base / 1000) * 1000;
}

function getResolvedLotPrimaryImageUrl(lot: Lot): string | null {
  return getResolvedLotImageUrls(lot)[0] ?? null;
}

function getResolvedLotImageUrls(lot: Lot): string[] {
  const apiImageUrls = getApiProvidedLotImageUrls(lot);
  if (apiImageUrls.length > 0) return apiImageUrls;

  return getStagingDemoFallbackLotImageUrls(lot);
}

function getApiProvidedLotImageUrls(lot: Lot): string[] {
  const record = lot as unknown as Record<string, unknown>;
  const urls: string[] = [];

  for (const key of API_LOT_IMAGE_FIELD_KEYS) {
    addImageUrlCandidate(record[key], urls);
  }

  for (const key of API_LOT_IMAGE_COLLECTION_KEYS) {
    addImageCollectionUrls(record[key], urls);
  }

  return Array.from(new Set(urls));
}

function getStagingDemoFallbackLotImageUrls(lot: Lot): string[] {
  const normalizedTitle = lot.title.toLowerCase();
  const fallback = STAGING_DEMO_LOT_IMAGE_FALLBACKS.find(({ titleFragment }) => normalizedTitle.includes(titleFragment));
  return fallback ? [...fallback.imageUrls] : [];
}

function addImageCollectionUrls(value: unknown, urls: string[]) {
  if (Array.isArray(value)) {
    for (const item of value) {
      addImageCollectionUrls(item, urls);
    }
    return;
  }

  if (!isRecord(value)) {
    addImageUrlCandidate(value, urls);
    return;
  }

  const initialUrlCount = urls.length;
  for (const key of API_LOT_IMAGE_OBJECT_KEYS) {
    addImageUrlCandidate(value[key], urls);
  }
  if (urls.length === initialUrlCount) {
    addImageUrlCandidate(value.image, urls);
  }
}

function addImageUrlCandidate(value: unknown, urls: string[]) {
  const normalizedUrl = normalizeLotImageUrl(value);
  if (normalizedUrl) {
    urls.push(normalizedUrl);
  }
}

function normalizeLotImageUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;

  const trimmed = value.trim();
  if (!trimmed) return null;
  if (/^(https?:|data:|\/)/i.test(trimmed)) return trimmed;

  return `/${trimmed.replace(/^\.?\//, "")}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getOptionalStringField(source: unknown, keys: string[]): string | null {
  const record = source as Record<string, unknown>;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return null;
}

function getOptionalMoneyField(source: unknown, keys: string[]): number | null {
  const record = source as Record<string, unknown>;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" || typeof value === "number") {
      const parsed = parseMoney(value);
      if (parsed > 0) return parsed;
    }
  }
  return null;
}

function readLikedLots(auctionId: number): number[] {
  try {
    const raw = window.localStorage.getItem(likedLotsStorageKey(auctionId));
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((value): value is number => Number.isInteger(value)) : [];
  } catch {
    return [];
  }
}

function writeLikedLots(auctionId: number, lotIds: number[]) {
  try {
    window.localStorage.setItem(likedLotsStorageKey(auctionId), JSON.stringify(lotIds));
  } catch {
    // Saving a shortlist is optional; browsing should continue if storage is unavailable.
  }
}

function likedLotsStorageKey(auctionId: number): string {
  return `bidals:liked-lots:${auctionId}`;
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
