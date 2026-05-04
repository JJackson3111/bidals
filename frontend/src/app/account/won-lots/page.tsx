"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, FileClock, Trophy } from "lucide-react";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, humanFulfillmentStatus, humanTimelineEvent, humanWinnerStatus } from "@/lib/format";
import type { FulfillmentTimelineEvent, WonLot } from "@/lib/types";

export default function WonLotsPage() {
  const [wonLots, setWonLots] = useState<WonLot[]>([]);
  const [timelines, setTimelines] = useState<Record<number, FulfillmentTimelineEvent[]>>({});
  const [timelineLoading, setTimelineLoading] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.getWonLots();
        setWonLots(response.results);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load won lots.");
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, []);

  async function toggleTimeline(itemId: number) {
    if (timelines[itemId]) {
      setTimelines((current) => {
        const next = { ...current };
        delete next[itemId];
        return next;
      });
      return;
    }

    setTimelineLoading(itemId);
    setError(null);
    try {
      const response = await api.getWonLotTimeline(itemId);
      setTimelines((current) => ({ ...current, [itemId]: response.results }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load won-lot timeline.");
    } finally {
      setTimelineLoading(null);
    }
  }

  return (
    <ProtectedRoute>
      <main className="page-shell">
        <section className="page-heading">
          <span className="eyebrow">Account</span>
          <h1>Won lots</h1>
        </section>

        {isLoading ? <LoadingState label="Loading won lots" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!isLoading && !error ? (
          wonLots.length === 0 ? (
            <EmptyState title="No won lots yet" message="Lots you win will appear here after the backend closes auctions and calculates winners." />
          ) : (
            <div className="dashboard-grid">
              {wonLots.map((item) => (
                <article className="auction-card management-card" key={item.id}>
                  <div className="card-topline">
                    <StatusPill status={item.fulfillment_status} />
                    <span>{formatDateTime(item.date_won)}</span>
                  </div>
                  <Trophy size={22} aria-hidden="true" />
                  <h2>{item.lot_title}</h2>
                  <p>{item.auction_title}</p>
                  <dl className="mini-meta horizontal">
                    <div>
                      <dt>Winning bid</dt>
                      <dd>{formatMoney(item.winning_bid_amount)}</dd>
                    </div>
                    <div>
                      <dt>Outcome</dt>
                      <dd>{humanWinnerStatus(item.outcome_status)}</dd>
                    </div>
                    <div>
                      <dt>Fulfillment</dt>
                      <dd>{humanFulfillmentStatus(item.fulfillment_status)}</dd>
                    </div>
                  </dl>
                  {item.public_winner_message ? <p>{item.public_winner_message}</p> : null}
                  <Link className="text-link" href={`/lots/${item.lot_id}`}>
                    View lot
                    <ArrowRight size={16} aria-hidden="true" />
                  </Link>
                  <button className="secondary-button" type="button" onClick={() => void toggleTimeline(item.id)}>
                    <FileClock size={17} aria-hidden="true" />
                    {timelines[item.id] ? "Hide timeline" : "Show timeline"}
                  </button>
                  {timelineLoading === item.id ? <LoadingState label="Loading timeline" /> : null}
                  {timelines[item.id] ? <PublicTimeline events={timelines[item.id]} /> : null}
                </article>
              ))}
            </div>
          )
        ) : null}
      </main>
    </ProtectedRoute>
  );
}

function PublicTimeline({ events }: { events: FulfillmentTimelineEvent[] }) {
  if (events.length === 0) {
    return <EmptyState title="No timeline yet" message="Fulfillment updates will appear here." />;
  }

  return (
    <div className="timeline-list">
      {events.map((event) => (
        <article className="timeline-item" key={event.id}>
          <span>{formatDateTime(event.created_at)}</span>
          <strong>{humanTimelineEvent(event.event_type)}</strong>
          <p>{event.old_status && event.new_status ? `${event.old_status} -> ${event.new_status}` : event.notification_type || "Recorded by BIDALS"}</p>
        </article>
      ))}
    </div>
  );
}
