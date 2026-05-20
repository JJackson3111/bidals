"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AuctionCard } from "@/components/AuctionCard";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { LotCard } from "@/components/LotCard";
import { api, ApiError } from "@/lib/api";
import type { Auction, Lot } from "@/lib/types";

export default function AuctionsPage() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [lots, setLots] = useState<Lot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lotPreviewError, setLotPreviewError] = useState<string | null>(null);
  const auctionRefreshInFlight = useRef(false);

  const refreshAuctions = useCallback(async () => {
    const auctionData = await api.getAuctions();
    setAuctions(auctionData);
  }, []);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      setLotPreviewError(null);
      try {
        await refreshAuctions();
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load auctions.");
        setIsLoading(false);
        return;
      }

      try {
        const lotData = await api.getLots();
        setLots(lotData);
      } catch (err) {
        setLots([]);
        setLotPreviewError(err instanceof ApiError ? err.message : "Unable to load lot previews.");
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [refreshAuctions]);

  const handleAuctionLifecycleBoundary = useCallback(() => {
    if (auctionRefreshInFlight.current) return;

    auctionRefreshInFlight.current = true;
    refreshAuctions()
      .catch(() => undefined)
      .finally(() => {
        auctionRefreshInFlight.current = false;
      });
  }, [refreshAuctions]);

  const featuredLots = useMemo(() => lots.slice(0, 8), [lots]);

  if (isLoading) return <main className="page-shell"><LoadingState label="Loading auctions" /></main>;
  if (error) return <main className="page-shell"><ErrorState message={error} /></main>;

  return (
    <main className="page-shell feed-layout">
      <section>
        <div className="page-heading">
          <span className="eyebrow">Auction feed</span>
          <h1>Live and upcoming auctions</h1>
        </div>
        {auctions.length === 0 ? (
          <EmptyState title="No auctions yet" message="New auctions will appear here when sellers publish them." />
        ) : (
          <div className="feed-grid">
            {auctions.map((auction) => (
              <AuctionCard
                key={auction.id}
                auction={auction}
                onLifecycleBoundary={handleAuctionLifecycleBoundary}
              />
            ))}
          </div>
        )}
      </section>

      <aside>
        <div className="page-heading">
          <span className="eyebrow">Lots</span>
          <h2>Browse the floor</h2>
        </div>
        {lotPreviewError ? (
          <ErrorState message={lotPreviewError} />
        ) : featuredLots.length === 0 ? (
          <EmptyState title="No lots visible" message="Open lots will appear here." />
        ) : (
          <div className="lot-grid">
            {featuredLots.map((lot) => (
              <LotCard key={lot.id} lot={lot} />
            ))}
          </div>
        )}
      </aside>
    </main>
  );
}
