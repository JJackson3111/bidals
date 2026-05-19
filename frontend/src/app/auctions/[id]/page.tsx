"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PackageOpen, Plus } from "lucide-react";

import { CountdownTimer } from "@/components/CountdownTimer";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { LotCard } from "@/components/LotCard";
import { StatusPill } from "@/components/StatusPill";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import { getAuctionDisplayState, phaseFromAuctionStatus, type AuctionPhase } from "@/lib/auctionLifecycle";
import { canManageAuctions, isPlatformAdmin } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import type { Auction, Lot } from "@/lib/types";

export default function AuctionDetailPage() {
  const params = useParams<{ id: string }>();
  const { user } = useAuth();
  const [auction, setAuction] = useState<Auction | null>(null);
  const [lots, setLots] = useState<Lot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState<number | null>(null);
  const refreshInFlight = useRef(false);
  const lastObservedPhase = useRef<AuctionPhase | null>(null);
  const lastNotifiedKey = useRef<string | null>(null);

  const loadAuction = useCallback(async ({ showLoading = true }: { showLoading?: boolean } = {}) => {
    if (showLoading) {
      setIsLoading(true);
      setError(null);
    }
    try {
      const [auctionData, lotData] = await Promise.all([
        api.getAuction(params.id),
        api.getLots({ auction: params.id }),
      ]);
      setAuction(auctionData);
      setLots(lotData);
    } catch (err) {
      if (showLoading) {
        setError(err instanceof ApiError ? err.message : "Unable to load auction.");
      }
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  }, [params.id]);

  useEffect(() => {
    if (params.id) void loadAuction();
  }, [params.id, loadAuction]);

  useEffect(() => {
    setNowMs(Date.now());
    const interval = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);

    return () => window.clearInterval(interval);
  }, []);

  const auctionDisplay = useMemo(
    () => auction ? getAuctionDisplayState(auction, nowMs) : null,
    [auction, nowMs],
  );

  const refreshLifecycleData = useCallback(() => {
    if (refreshInFlight.current) return;

    refreshInFlight.current = true;
    loadAuction({ showLoading: false })
      .catch(() => undefined)
      .finally(() => {
        refreshInFlight.current = false;
      });
  }, [loadAuction]);

  useEffect(() => {
    if (!auction || !auctionDisplay || nowMs === null) return;

    const previousPhase = lastObservedPhase.current;
    lastObservedPhase.current = auctionDisplay.phase;

    const statusPhase = phaseFromAuctionStatus(auction.status);
    const crossedBoundary = previousPhase !== null && previousPhase !== auctionDisplay.phase;
    const backendLooksStale = statusPhase !== null && statusPhase !== auctionDisplay.phase;
    const notifyKey = `${auction.id}:${auction.status}:${auctionDisplay.phase}`;

    if ((crossedBoundary || backendLooksStale) && lastNotifiedKey.current !== notifyKey) {
      lastNotifiedKey.current = notifyKey;
      refreshLifecycleData();
    }
  }, [auction, auctionDisplay, nowMs, refreshLifecycleData]);

  if (isLoading) return <main className="page-shell"><LoadingState label="Loading auction" /></main>;
  if (error) return <main className="page-shell"><ErrorState message={error} /></main>;
  if (!auction) return <main className="page-shell"><EmptyState title="Auction not found" message="This auction is not available." /></main>;

  const isAuctionManager = canManageAuctions(user) && (isPlatformAdmin(user) || auction.created_by === user?.id);
  const hasPreparedPrivateLots = isAuctionManager && lots.length > 0 && auction.status === "draft";
  const display = auctionDisplay ?? getAuctionDisplayState(auction, nowMs);

  return (
    <main className="page-shell">
      <section className="detail-hero">
        <div className="detail-topline">
          <StatusPill label={display.badgeLabel} status={display.badgeStatus} />
          {display.targetTime && display.countdownLabel ? (
            <CountdownTimer
              label={display.countdownLabel}
              nowMs={nowMs}
              onElapsed={refreshLifecycleData}
              targetTime={display.targetTime}
            />
          ) : null}
        </div>
        <div className="page-heading">
          <span className="eyebrow">Auction #{auction.id}</span>
          <h1>{auction.title}</h1>
          <p>{auction.description || "No description provided."}</p>
        </div>
        <dl className="mini-meta detail-panel">
          <div>
            <dt>Starts</dt>
            <dd>{formatDateTime(auction.start_time)}</dd>
          </div>
          <div>
            <dt>Ends</dt>
            <dd>{formatDateTime(auction.end_time)}</dd>
          </div>
          <div>
            <dt>Seller</dt>
            <dd>{auction.created_by_username}</dd>
          </div>
        </dl>
      </section>

      <section className="page-heading" style={{ marginTop: 28 }}>
        <span className="eyebrow">Lots</span>
        <h2>Lots in this auction</h2>
      </section>
      {lots.length === 0 ? (
        isAuctionManager ? (
          <div className="state-panel">
            <PackageOpen size={24} aria-hidden="true" />
            <strong>No lots added yet</strong>
            <span>Add your first lot to prepare this auction.</span>
            <Link className="primary-button" href={`/dashboard/lots/new?auction=${auction.id}`}>
              <Plus size={18} aria-hidden="true" />
              Create lot for this auction
            </Link>
          </div>
        ) : (
          <EmptyState title="No lots visible" message="Lots will appear here when they are open or published." />
        )
      ) : (
        <>
          {hasPreparedPrivateLots ? (
            <div className="state-panel warning" style={{ minHeight: 0, marginBottom: 14 }}>
              <strong>Lots are prepared but not public yet</strong>
              <span>Draft auction lots remain hidden from public bidding until the auction is live.</span>
            </div>
          ) : null}
          <div className="lot-grid">
            {lots.map((lot) => (
              <LotCard key={lot.id} lot={lot} />
            ))}
          </div>
        </>
      )}
    </main>
  );
}
