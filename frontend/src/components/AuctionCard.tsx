"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { CountdownTimer } from "@/components/CountdownTimer";
import { StatusPill } from "@/components/StatusPill";
import { formatDateTime } from "@/lib/format";
import type { Auction, AuctionStatus } from "@/lib/types";

type AuctionCardPhase = "scheduled" | "live" | "closed" | "cancelled" | "draft";

type AuctionCardState = {
  badgeLabel: string;
  badgeStatus: string;
  countdownLabel: "Starts in" | "Ends in" | null;
  ctaLabel: string;
  phase: AuctionCardPhase;
  targetTime: string | null;
};

export function AuctionCard({
  auction,
  onLifecycleBoundary,
}: {
  auction: Auction;
  onLifecycleBoundary?: (auction: Auction, phase: AuctionCardPhase) => void;
}) {
  const [nowMs, setNowMs] = useState<number | null>(null);
  const lastObservedPhase = useRef<AuctionCardPhase | null>(null);
  const lastNotifiedKey = useRef<string | null>(null);

  useEffect(() => {
    setNowMs(Date.now());
    const interval = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);

    return () => window.clearInterval(interval);
  }, []);

  const cardState = useMemo(() => getAuctionCardState(auction, nowMs), [auction, nowMs]);

  useEffect(() => {
    if (nowMs === null) return;

    const previousPhase = lastObservedPhase.current;
    lastObservedPhase.current = cardState.phase;

    const statusPhase = phaseFromAuctionStatus(auction.status);
    const crossedBoundary = previousPhase !== null && previousPhase !== cardState.phase;
    const backendLooksStale = statusPhase !== null && statusPhase !== cardState.phase;
    const notifyKey = `${auction.id}:${auction.status}:${cardState.phase}`;

    if ((crossedBoundary || backendLooksStale) && lastNotifiedKey.current !== notifyKey) {
      lastNotifiedKey.current = notifyKey;
      onLifecycleBoundary?.(auction, cardState.phase);
    }
  }, [auction, cardState.phase, nowMs, onLifecycleBoundary]);

  return (
    <article className="auction-card">
      <div className="card-topline">
        <StatusPill label={cardState.badgeLabel} status={cardState.badgeStatus} />
        {cardState.targetTime && cardState.countdownLabel ? (
          <CountdownTimer
            label={cardState.countdownLabel}
            nowMs={nowMs}
            targetTime={cardState.targetTime}
          />
        ) : null}
      </div>
      <Link href={`/auctions/${auction.id}`} className="card-title-link">
        <h2>{auction.title}</h2>
      </Link>
      <p>{auction.description || "No description provided."}</p>
      <dl className="mini-meta">
        <div>
          <dt>Starts</dt>
          <dd>{formatDateTime(auction.start_time)}</dd>
        </div>
        <div>
          <dt>Ends</dt>
          <dd>{formatDateTime(auction.end_time)}</dd>
        </div>
      </dl>
      <Link
        aria-label={`${cardState.ctaLabel}: ${auction.title}`}
        className={`text-link auction-card-cta ${cardState.phase === "scheduled" ? "is-preview" : ""}`}
        href={`/auctions/${auction.id}`}
      >
        {cardState.ctaLabel}
        <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </article>
  );
}

function getAuctionCardState(auction: Auction, nowMs: number | null): AuctionCardState {
  const phase = getAuctionPhase(auction, nowMs);

  if (phase === "scheduled") {
    return {
      badgeLabel: "Scheduled",
      badgeStatus: "scheduled",
      countdownLabel: "Starts in",
      ctaLabel: "Preview auction",
      phase,
      targetTime: auction.start_time,
    };
  }

  if (phase === "live") {
    return {
      badgeLabel: "Live",
      badgeStatus: "live",
      countdownLabel: "Ends in",
      ctaLabel: "Open auction",
      phase,
      targetTime: auction.end_time,
    };
  }

  if (phase === "closed") {
    return {
      badgeLabel: "Closed",
      badgeStatus: "closed",
      countdownLabel: null,
      ctaLabel: "View auction",
      phase,
      targetTime: null,
    };
  }

  if (phase === "cancelled") {
    return {
      badgeLabel: "Cancelled",
      badgeStatus: "cancelled",
      countdownLabel: null,
      ctaLabel: "View auction",
      phase,
      targetTime: null,
    };
  }

  return {
    badgeLabel: "Draft",
    badgeStatus: "draft",
    countdownLabel: null,
    ctaLabel: "View auction",
    phase,
    targetTime: null,
  };
}

function getAuctionPhase(auction: Auction, nowMs: number | null): AuctionCardPhase {
  const statusPhase = phaseFromAuctionStatus(auction.status);
  if (statusPhase === "cancelled" || statusPhase === "draft" || statusPhase === "closed") {
    return statusPhase;
  }

  const startMs = new Date(auction.start_time).getTime();
  const endMs = new Date(auction.end_time).getTime();
  if (nowMs === null || !Number.isFinite(startMs) || !Number.isFinite(endMs)) {
    return statusPhase ?? "closed";
  }

  if (nowMs >= endMs) return "closed";
  if (nowMs >= startMs) return "live";
  return "scheduled";
}

function phaseFromAuctionStatus(status: AuctionStatus | string): AuctionCardPhase | null {
  if (status === "scheduled") return "scheduled";
  if (status === "live" || status === "open") return "live";
  if (status === "ended" || status === "closed") return "closed";
  if (status === "cancelled") return "cancelled";
  if (status === "draft") return "draft";
  return null;
}
