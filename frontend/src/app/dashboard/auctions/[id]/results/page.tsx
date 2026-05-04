"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Trophy } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, humanWinnerStatus } from "@/lib/format";
import type { AuctionResultsResponse, WinnerReviewItem } from "@/lib/types";

export default function AuctionResultsPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<AuctionResultsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        setReport(await api.getAuctionResults(params.id));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load auction results.");
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [params.id]);

  return (
    <ProtectedRoute sellerOnly>
      <DashboardLayout title="Auction results" eyebrow="Winner review">
        <Link className="text-link" href="/dashboard/winners">
          <ArrowLeft size={16} aria-hidden="true" />
          Back to winners
        </Link>

        {isLoading ? <LoadingState label="Loading auction results" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!isLoading && !error && report ? (
          <>
            <section className="detail-panel">
              <div className="card-topline">
                <StatusPill status={report.auction.status} />
                <span>{formatDateTime(report.auction.end_time)}</span>
              </div>
              <h2>{report.auction.title}</h2>
              <p>{report.auction.description || "No description provided."}</p>
            </section>

            <section className="metric-grid compact" aria-label="Auction result summary">
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

            {report.results.length === 0 ? (
              <EmptyState title="No calculated outcomes" message="Run the backend auction closing job after this auction ends." />
            ) : (
              <section className="management-list">
                {report.results.map((item) => (
                  <ResultRow item={item} key={item.lot_id} />
                ))}
              </section>
            )}
          </>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}

function ResultRow({ item }: { item: WinnerReviewItem }) {
  return (
    <article className="management-row winner-row">
      <div>
        <StatusPill status={item.outcome_status} />
        <strong>{item.lot_title}</strong>
        <span>{humanWinnerStatus(item.outcome_status)}</span>
        {item.calculated_at ? <span>Calculated {formatDateTime(item.calculated_at)}</span> : null}
      </div>
      <div className="winner-detail-grid">
        <div>
          <span>Winner</span>
          <strong>{item.winner_username ?? "None"}</strong>
        </div>
        <div>
          <span>Winning bid</span>
          <strong>{item.winning_bid_amount ? formatMoney(item.winning_bid_amount) : "No sale"}</strong>
        </div>
        <div>
          <span>Reserve</span>
          <strong>{item.reserve_price ? formatMoney(item.reserve_price) : "None"}</strong>
        </div>
      </div>
    </article>
  );
}
