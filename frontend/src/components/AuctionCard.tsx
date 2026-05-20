"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { CountdownTimer } from "@/components/CountdownTimer";
import { StatusPill } from "@/components/StatusPill";
import { getAuctionDisplayState, phaseFromAuctionStatus, type AuctionPhase } from "@/lib/auctionLifecycle";
import { formatDateTime } from "@/lib/format";
import type { Auction } from "@/lib/types";

export function AuctionCard({
  auction,
  onLifecycleBoundary,
}: {
  auction: Auction;
  onLifecycleBoundary?: (auction: Auction, phase: AuctionPhase) => void;
}) {
  const [nowMs, setNowMs] = useState<number | null>(null);
  const lastObservedPhase = useRef<AuctionPhase | null>(null);
  const lastNotifiedKey = useRef<string | null>(null);

  useEffect(() => {
    setNowMs(Date.now());
    const interval = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);

    return () => window.clearInterval(interval);
  }, []);

  const cardState = useMemo(() => getAuctionDisplayState(auction, nowMs), [auction, nowMs]);

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
