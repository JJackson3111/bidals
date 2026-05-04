"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { BidPanel } from "@/components/BidPanel";
import { CountdownTimer } from "@/components/CountdownTimer";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, getLotPrimaryImageUrl } from "@/lib/format";
import type { Auction, Bid, BidResponse, Lot } from "@/lib/types";

export default function LotDetailPage() {
  const params = useParams<{ id: string }>();
  const [lot, setLot] = useState<Lot | null>(null);
  const [auction, setAuction] = useState<Auction | null>(null);
  const [bids, setBids] = useState<Bid[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLot = useCallback(async () => {
    const lotData = await api.getLot(params.id);
    setLot(lotData);
    const [auctionData, bidData] = await Promise.all([
      api.getAuction(lotData.auction),
      api.getBidHistory(lotData.id),
    ]);
    setAuction(auctionData);
    setBids(bidData);
    return lotData;
  }, [params.id]);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        await loadLot();
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load lot.");
      } finally {
        setIsLoading(false);
      }
    }

    if (params.id) load();
  }, [params.id, loadLot]);

  useEffect(() => {
    if (!params.id) return;
    const interval = window.setInterval(() => {
      loadLot().catch(() => undefined);
    }, 8000);

    return () => window.clearInterval(interval);
  }, [params.id, loadLot]);

  async function handleBidSettled(response: BidResponse) {
    setLot((current) => {
      if (!current) return current;
      return { ...current, current_price: response.current_price };
    });
    await loadLot();
  }

  if (isLoading) return <main className="page-shell"><LoadingState label="Loading lot" /></main>;
  if (error) return <main className="page-shell"><ErrorState message={error} /></main>;
  if (!lot) return <main className="page-shell"><EmptyState title="Lot not found" message="This lot is not available." /></main>;

  const primaryImageUrl = getLotPrimaryImageUrl(lot);

  return (
    <main className="page-shell lot-detail-grid">
      <section className="detail-hero">
        {primaryImageUrl ? (
          <div
            aria-label={lot.uploaded_images?.[0]?.alt_text || lot.title}
            className="lot-detail-image"
            role="img"
            style={{ backgroundImage: `url("${primaryImageUrl}")` }}
          />
        ) : (
          <div className="lot-image-placeholder" style={{ minHeight: 260 }}>
            <span>{lot.title.slice(0, 1).toUpperCase()}</span>
          </div>
        )}
        <div className="detail-topline">
          <StatusPill status={lot.status} />
          {auction ? <StatusPill status={auction.status} /> : null}
          {auction ? <CountdownTimer endTime={auction.end_time} /> : null}
        </div>
        <div className="page-heading">
          <span className="eyebrow">{lot.auction_title}</span>
          <h1>{lot.title}</h1>
          <p>{lot.description || "No description provided."}</p>
        </div>
        <div className="detail-panel">
          <div className="price-display">
            <span className="eyebrow">Current price</span>
            <strong>{formatMoney(lot.current_price)}</strong>
          </div>
          <dl className="mini-meta">
            <div>
              <dt>Bid increment</dt>
              <dd>{formatMoney(lot.bid_increment)}</dd>
            </div>
            <div>
              <dt>Auction status</dt>
              <dd>{lot.auction_status}</dd>
            </div>
            <div>
              <dt>Lot status</dt>
              <dd>{lot.status}</dd>
            </div>
            <div>
              <dt>Reserve</dt>
              <dd>{lot.reserve_price ? formatMoney(lot.reserve_price) : "Not set"}</dd>
            </div>
            {auction ? (
              <>
                <div>
                  <dt>Starts</dt>
                  <dd>{formatDateTime(auction.start_time)}</dd>
                </div>
                <div>
                  <dt>Ends</dt>
                  <dd>{formatDateTime(auction.end_time)}</dd>
                </div>
              </>
            ) : null}
          </dl>
        </div>

        <section className="detail-panel">
          <div className="page-heading">
            <span className="eyebrow">Bid history</span>
            <h2>Recent bids</h2>
          </div>
          {bids.length === 0 ? (
            <EmptyState title="No bids yet" message="Accepted bids will appear here." />
          ) : (
            <div className="bid-list">
              {bids.slice(0, 8).map((bid) => (
                <div className="bid-row" key={bid.id}>
                  <div>
                    <span>{bid.bidder_username || `Bidder ${bid.bidder}`}</span>
                    <small>{formatDateTime(bid.server_timestamp)}</small>
                  </div>
                  <div className="bid-row-value">
                    <StatusPill status={bid.status} />
                    <strong>{formatMoney(bid.amount)}</strong>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </section>

      <BidPanel lot={lot} onBidSettled={handleBidSettled} />
    </main>
  );
}
