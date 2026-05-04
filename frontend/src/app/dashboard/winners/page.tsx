"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, RefreshCw, Trophy } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, humanWinnerStatus } from "@/lib/format";
import type { LotWinnerStatus, WinnerReviewResponse } from "@/lib/types";

type OutcomeFilter = LotWinnerStatus | "all";

export default function WinnersPage() {
  const [report, setReport] = useState<WinnerReviewResponse | null>(null);
  const [outcomeStatus, setOutcomeStatus] = useState<OutcomeFilter>("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      setReport(
        await api.getWinnerReviews({
          outcome_status: outcomeStatus === "all" ? undefined : outcomeStatus,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load winner review.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [outcomeStatus]);

  const groupedByAuction = useMemo(() => {
    const groups = new Map<number, NonNullable<WinnerReviewResponse["results"]>>();
    for (const item of report?.results ?? []) {
      const group = groups.get(item.auction_id) ?? [];
      group.push(item);
      groups.set(item.auction_id, group);
    }
    return Array.from(groups.entries());
  }, [report]);

  return (
    <ProtectedRoute sellerOnly>
      <DashboardLayout title="Winner review" eyebrow="Seller dashboard">
        <section className="filter-panel operations-filter-panel" aria-label="Winner filters">
          <Trophy size={18} aria-hidden="true" />
          <label>
            Outcome
            <select value={outcomeStatus} onChange={(event) => setOutcomeStatus(event.target.value as OutcomeFilter)}>
              <option value="all">All outcomes</option>
              <option value="winner_assigned">Winner assigned</option>
              <option value="no_bids">No bids</option>
              <option value="reserve_not_met">Reserve not met</option>
            </select>
          </label>
          <button className="secondary-button" type="button" onClick={load} disabled={isLoading}>
            <RefreshCw size={17} aria-hidden="true" />
            Refresh
          </button>
        </section>

        {isLoading ? <LoadingState label="Loading winner outcomes" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!isLoading && !error && report ? (
          <>
            <section className="metric-grid compact" aria-label="Winner review summary">
              <article className="metric-card">
                <Trophy size={18} aria-hidden="true" />
                <span>Total outcomes</span>
                <strong>{report.summary.total_lots}</strong>
              </article>
              <article className="metric-card">
                <Trophy size={18} aria-hidden="true" />
                <span>Winners</span>
                <strong>{report.summary.winner_assigned}</strong>
              </article>
              <article className="metric-card">
                <Trophy size={18} aria-hidden="true" />
                <span>No bids</span>
                <strong>{report.summary.no_bids}</strong>
              </article>
              <article className="metric-card">
                <Trophy size={18} aria-hidden="true" />
                <span>Reserve not met</span>
                <strong>{report.summary.reserve_not_met}</strong>
              </article>
            </section>

            {groupedByAuction.length === 0 ? (
              <EmptyState title="No finalized outcomes" message="Ended auctions will appear here after the backend closing job calculates outcomes." />
            ) : (
              <div className="dashboard-grid">
                {groupedByAuction.map(([auctionId, items]) => (
                  <article className="auction-card management-card" key={auctionId}>
                    <div className="card-topline">
                      <StatusPill status={items[0].auction_status} />
                      <span>{formatDateTime(items[0].auction_end_time)}</span>
                    </div>
                    <h3>{items[0].auction_title}</h3>
                    <div className="management-list compact-list">
                      {items.map((item) => (
                        <div className="management-row" key={item.lot_id}>
                          <div>
                            <StatusPill status={item.outcome_status} />
                            <strong>{item.lot_title}</strong>
                            <span>{outcomeLine(item)}</span>
                          </div>
                          <div className="activity-value">
                            <strong>{item.winning_bid_amount ? formatMoney(item.winning_bid_amount) : "No sale"}</strong>
                            <span>{item.calculated_at ? formatDateTime(item.calculated_at) : "Pending"}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                    <Link className="text-link" href={`/dashboard/auctions/${auctionId}/results`}>
                      Review auction
                      <ArrowRight size={16} aria-hidden="true" />
                    </Link>
                  </article>
                ))}
              </div>
            )}
          </>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}

function outcomeLine(item: WinnerReviewResponse["results"][number]) {
  if (item.outcome_status === "winner_assigned") {
    return `${item.winner_username ?? "Winner"} - ${humanWinnerStatus(item.outcome_status)}`;
  }
  return humanWinnerStatus(item.outcome_status);
}
