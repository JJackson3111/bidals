"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PackageOpen, Plus } from "lucide-react";

import { CountdownTimer } from "@/components/CountdownTimer";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { LotCard } from "@/components/LotCard";
import { StatusPill } from "@/components/StatusPill";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
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

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const [auctionData, lotData] = await Promise.all([
          api.getAuction(params.id),
          api.getLots({ auction: params.id }),
        ]);
        setAuction(auctionData);
        setLots(lotData);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load auction.");
      } finally {
        setIsLoading(false);
      }
    }

    if (params.id) load();
  }, [params.id]);

  if (isLoading) return <main className="page-shell"><LoadingState label="Loading auction" /></main>;
  if (error) return <main className="page-shell"><ErrorState message={error} /></main>;
  if (!auction) return <main className="page-shell"><EmptyState title="Auction not found" message="This auction is not available." /></main>;

  const isAuctionManager = canManageAuctions(user) && (isPlatformAdmin(user) || auction.created_by === user?.id);
  const hasPreparedPrivateLots = isAuctionManager && lots.length > 0 && auction.status === "draft";

  return (
    <main className="page-shell">
      <section className="detail-hero">
        <div className="detail-topline">
          <StatusPill status={auction.status} />
          <CountdownTimer endTime={auction.end_time} />
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
