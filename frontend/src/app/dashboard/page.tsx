"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  FileClock,
  Gavel,
  Layers,
  ListChecks,
  Pencil,
  PlusCircle,
  Radio,
  Trophy,
} from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { StatusPill } from "@/components/StatusPill";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney } from "@/lib/format";
import type { Auction, AuctionStatus, Bid, FulfillmentSummary, Lot, LotStatus } from "@/lib/types";

type StatusFilter<T extends string> = T | "all";

function toIsoDateTime(value: string): string | undefined {
  return value ? new Date(value).toISOString() : undefined;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [lots, setLots] = useState<Lot[]>([]);
  const [recentBids, setRecentBids] = useState<Bid[]>([]);
  const [bidTotal, setBidTotal] = useState(0);
  const [fulfillmentSummary, setFulfillmentSummary] = useState<FulfillmentSummary | null>(null);
  const [auctionStatus, setAuctionStatus] = useState<StatusFilter<AuctionStatus>>("all");
  const [lotStatus, setLotStatus] = useState<StatusFilter<LotStatus>>("all");
  const [auctionSearch, setAuctionSearch] = useState("");
  const [lotSearch, setLotSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sort, setSort] = useState("newest");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!user) return;
      setIsLoading(true);
      setError(null);
      try {
        const starts_after = toIsoDateTime(dateFrom);
        const ends_before = toIsoDateTime(dateTo);
        const [auctionData, lotData, fulfillmentData] = await Promise.all([
          api.getAuctions({
            status: auctionStatus === "all" ? undefined : auctionStatus,
            search: auctionSearch || undefined,
            starts_after,
            ends_before,
            sort,
          }),
          api.getLots({
            status: lotStatus === "all" ? undefined : lotStatus,
            search: lotSearch || undefined,
            auction_search: auctionSearch || undefined,
            starts_after,
            ends_before,
            sort,
          }),
          api.getFulfillmentRecords().catch(() => null),
        ]);
        setAuctions(auctionData);
        setLots(lotData);
        setFulfillmentSummary(fulfillmentData?.summary ?? null);

        const ownedAuctionIds = new Set(
          auctionData
            .filter((auction) => user.role === "admin" || auction.created_by === user.id)
            .map((auction) => auction.id),
        );
        const ownedLots = lotData.filter((lot) => ownedAuctionIds.has(lot.auction));
        const bidResults = await Promise.all(
          ownedLots.map((lot) => api.getBidHistory(lot.id).catch(() => [] as Bid[])),
        );
        const allBids = bidResults.flat();
        setBidTotal(allBids.length);
        setRecentBids(
          allBids
            .sort((a, b) => new Date(b.server_timestamp).getTime() - new Date(a.server_timestamp).getTime())
            .slice(0, 8),
        );
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load dashboard.");
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [auctionSearch, auctionStatus, dateFrom, dateTo, lotSearch, lotStatus, sort, user]);

  const ownedAuctions = useMemo(() => {
    if (!user) return [];
    if (user.role === "admin") return auctions;
    return auctions.filter((auction) => auction.created_by === user.id);
  }, [auctions, user]);

  const ownedAuctionIds = useMemo(() => new Set(ownedAuctions.map((auction) => auction.id)), [ownedAuctions]);
  const ownedLots = useMemo(() => lots.filter((lot) => ownedAuctionIds.has(lot.auction)), [lots, ownedAuctionIds]);
  const lotLookup = useMemo(() => new Map(ownedLots.map((lot) => [lot.id, lot])), [ownedLots]);
  const stats = [
    { label: "Total auctions", value: ownedAuctions.length, icon: Gavel },
    { label: "Live", value: ownedAuctions.filter((auction) => auction.status === "live").length, icon: Radio },
    { label: "Scheduled", value: ownedAuctions.filter((auction) => auction.status === "scheduled").length, icon: CalendarClock },
    { label: "Ended", value: ownedAuctions.filter((auction) => auction.status === "ended").length, icon: CheckCircle2 },
    { label: "Lots", value: ownedLots.length, icon: Layers },
    { label: "Total bids", value: bidTotal, icon: ListChecks },
    { label: "Pending fulfillment", value: fulfillmentSummary?.pending_confirmation ?? 0, icon: ClipboardCheck },
    { label: "Awaiting handoff", value: fulfillmentSummary?.awaiting_collection_or_delivery ?? 0, icon: ClipboardCheck },
    { label: "Completed", value: fulfillmentSummary?.completed ?? 0, icon: ClipboardCheck },
    { label: "Disputed", value: fulfillmentSummary?.disputed ?? 0, icon: ClipboardCheck },
  ];

  return (
    <ProtectedRoute sellerOnly>
      <DashboardLayout title="Manage auctions">
        <div className="button-row dashboard-actions">
          <Link className="primary-button" href="/dashboard/auctions/new">
            <PlusCircle size={18} aria-hidden="true" />
            Create auction
          </Link>
          <Link className="secondary-button" href="/dashboard/lots/new">
            <PlusCircle size={18} aria-hidden="true" />
            Create lot
          </Link>
          <Link className="secondary-button" href="/auctions">
            <Gavel size={18} aria-hidden="true" />
            View feed
          </Link>
          <Link className="secondary-button" href="/dashboard/winners">
            <Trophy size={18} aria-hidden="true" />
            Winner review
          </Link>
          <Link className="secondary-button" href="/dashboard/fulfillment">
            <ClipboardCheck size={18} aria-hidden="true" />
            Fulfillment
          </Link>
          {user?.role === "admin" ? (
            <Link className="secondary-button" href="/dashboard/audit">
              <FileClock size={18} aria-hidden="true" />
              Audit log
            </Link>
          ) : null}
        </div>

        {isLoading ? <LoadingState label="Loading dashboard" /> : null}
        {error ? <ErrorState message={error} /> : null}
        {!isLoading && !error ? (
          <>
            <section className="filter-panel dashboard-filter-panel" aria-label="Dashboard filters">
              <label>
                Auction status
                <select value={auctionStatus} onChange={(event) => setAuctionStatus(event.target.value as StatusFilter<AuctionStatus>)}>
                  <option value="all">All auctions</option>
                  <option value="draft">Draft</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="live">Live</option>
                  <option value="ended">Ended</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>
              <label>
                Lot status
                <select value={lotStatus} onChange={(event) => setLotStatus(event.target.value as StatusFilter<LotStatus>)}>
                  <option value="all">All lots</option>
                  <option value="draft">Draft</option>
                  <option value="open">Open</option>
                  <option value="closed">Closed</option>
                  <option value="sold">Sold</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>
              <label>
                Auction search
                <input value={auctionSearch} onChange={(event) => setAuctionSearch(event.target.value)} placeholder="Auction title" />
              </label>
              <label>
                Lot search
                <input value={lotSearch} onChange={(event) => setLotSearch(event.target.value)} placeholder="Lot title" />
              </label>
              <label>
                From
                <input type="datetime-local" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
              </label>
              <label>
                To
                <input type="datetime-local" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
              </label>
              <label>
                Sort
                <select value={sort} onChange={(event) => setSort(event.target.value)}>
                  <option value="newest">Newest</option>
                  <option value="oldest">Oldest</option>
                  <option value="ending_soon">Ending soon</option>
                </select>
              </label>
            </section>

            <section className="metric-grid" aria-label="Auction metrics">
              {stats.map((stat) => {
                const Icon = stat.icon;
                return (
                  <article className="metric-card" key={stat.label}>
                    <Icon size={18} aria-hidden="true" />
                    <span>{stat.label}</span>
                    <strong>{stat.value}</strong>
                  </article>
                );
              })}
            </section>

            <section className="dashboard-two-column">
              <div className="dashboard-section">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">Seller workspace</span>
                    <h2>Your auctions</h2>
                  </div>
                  <Link className="text-link" href="/dashboard/auctions/new">
                    New
                    <ArrowRight size={16} aria-hidden="true" />
                  </Link>
                </div>
                {ownedAuctions.length === 0 ? (
                  <EmptyState title="No auctions yet" message="Create an auction to start adding lots." />
                ) : (
                  <div className="dashboard-grid">
                    {ownedAuctions.map((auction) => {
                      const lotCount = ownedLots.filter((lot) => lot.auction === auction.id).length;
                      return (
                        <article className="auction-card management-card" key={auction.id}>
                          <div className="card-topline">
                            <StatusPill status={auction.status} />
                            <span>{formatDateTime(auction.end_time)}</span>
                          </div>
                          <h3>{auction.title}</h3>
                          <p>{auction.description || "No description provided."}</p>
                          <dl className="mini-meta horizontal">
                            <div>
                              <dt>Lots</dt>
                              <dd>{lotCount}</dd>
                            </div>
                            <div>
                              <dt>Owner</dt>
                              <dd>{auction.created_by_username}</dd>
                            </div>
                          </dl>
                          <div className="link-row">
                            <Link className="text-link" href={`/auctions/${auction.id}`}>
                              Open
                              <ArrowRight size={16} aria-hidden="true" />
                            </Link>
                            <Link className="text-link" href={`/dashboard/auctions/${auction.id}/edit`}>
                              Edit
                              <Pencil size={16} aria-hidden="true" />
                            </Link>
                            <Link className="text-link" href={`/dashboard/auctions/${auction.id}/results`}>
                              Results
                              <Trophy size={16} aria-hidden="true" />
                            </Link>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}

                <div className="section-heading">
                  <div>
                    <span className="eyebrow">Lot management</span>
                    <h2>Your lots</h2>
                  </div>
                  <Link className="text-link" href="/dashboard/lots/new">
                    New
                    <ArrowRight size={16} aria-hidden="true" />
                  </Link>
                </div>
                {ownedLots.length === 0 ? (
                  <EmptyState title="No lots yet" message="Create lots under one of your auctions." />
                ) : (
                  <div className="management-list">
                    {ownedLots.map((lot) => (
                      <article className="management-row" key={lot.id}>
                        <div>
                          <StatusPill status={lot.status} />
                          <strong>{lot.title}</strong>
                          <span>{lot.auction_title}</span>
                        </div>
                        <div className="management-actions">
                          <span>{formatMoney(lot.current_price)}</span>
                          <Link className="text-link" href={`/lots/${lot.id}`}>
                            View
                          </Link>
                          <Link className="text-link" href={`/dashboard/lots/${lot.id}/edit`}>
                            Edit
                          </Link>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </div>

              <aside className="detail-panel activity-panel">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">Activity</span>
                    <h2>Recent bids</h2>
                  </div>
                </div>
                {recentBids.length === 0 ? (
                  <EmptyState title="No bid activity" message="Accepted and rejected bid attempts will appear after bidding starts." />
                ) : (
                  <div className="activity-list">
                    {recentBids.map((bid) => {
                      const bidLot = lotLookup.get(bid.lot);
                      return (
                        <div className="activity-row" key={bid.id}>
                          <div>
                            <strong>{bid.bidder_username || `Bidder ${bid.bidder}`}</strong>
                            <span>{bidLot?.title || `Lot ${bid.lot}`}</span>
                          </div>
                          <div className="activity-value">
                            <StatusPill status={bid.status} />
                            <span>{formatMoney(bid.amount)}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </aside>
            </section>
          </>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}
