"use client";

import { useEffect, useMemo, useState } from "react";
import { ClipboardCheck, FileClock, RefreshCw, Search } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, humanFulfillmentStatus, humanTimelineEvent } from "@/lib/format";
import type { FulfillmentRecord, FulfillmentStatus, FulfillmentSummary, FulfillmentTimelineEvent } from "@/lib/types";

type FulfillmentFilter = FulfillmentStatus | "all";

const fulfillmentStatuses: FulfillmentStatus[] = [
  "pending_confirmation",
  "winner_confirmed",
  "seller_contacted",
  "awaiting_collection_or_delivery",
  "completed",
  "cancelled",
  "disputed",
];

const emptySummary: FulfillmentSummary = {
  total: 0,
  pending_confirmation: 0,
  winner_confirmed: 0,
  seller_contacted: 0,
  awaiting_collection_or_delivery: 0,
  completed: 0,
  cancelled: 0,
  disputed: 0,
};

function statusOptions(record: FulfillmentRecord): FulfillmentStatus[] {
  return [record.status, ...record.allowed_next_statuses.filter((status) => status !== record.status)];
}

export default function FulfillmentPage() {
  const [records, setRecords] = useState<FulfillmentRecord[]>([]);
  const [summary, setSummary] = useState<FulfillmentSummary>(emptySummary);
  const [statusFilter, setStatusFilter] = useState<FulfillmentFilter>("all");
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [timelines, setTimelines] = useState<Record<number, FulfillmentTimelineEvent[]>>({});
  const [timelineLoading, setTimelineLoading] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.getFulfillmentRecords({
        status: statusFilter === "all" ? undefined : statusFilter,
        search: search || undefined,
      });
      setRecords(response.results);
      setSummary(response.summary);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load fulfillment records.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const metrics = useMemo(
    () => [
      ["Pending", summary.pending_confirmation ?? 0],
      ["Contacted", summary.seller_contacted ?? 0],
      ["Awaiting", summary.awaiting_collection_or_delivery ?? 0],
      ["Completed", summary.completed ?? 0],
      ["Disputed", summary.disputed ?? 0],
    ],
    [summary],
  );

  async function handleSave(record: FulfillmentRecord, formData: FormData) {
    setSuccess(null);
    setError(null);
    try {
      const saved = await api.updateFulfillmentRecord(record.id, {
        status: formData.get("status") as FulfillmentStatus,
        confirmation_notes: String(formData.get("confirmation_notes") ?? ""),
        seller_notes: String(formData.get("seller_notes") ?? ""),
        admin_notes: String(formData.get("admin_notes") ?? ""),
        public_winner_message: String(formData.get("public_winner_message") ?? ""),
      });
      setRecords((current) => current.map((item) => (item.id === saved.id ? saved : item)));
      setSuccess(`Saved fulfillment for ${saved.lot_title}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to update fulfillment.");
    }
  }

  async function toggleTimeline(recordId: number) {
    if (timelines[recordId]) {
      setTimelines((current) => {
        const next = { ...current };
        delete next[recordId];
        return next;
      });
      return;
    }

    setTimelineLoading(recordId);
    setError(null);
    try {
      const response = await api.getFulfillmentTimeline(recordId);
      setTimelines((current) => ({ ...current, [recordId]: response.results }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load fulfillment timeline.");
    } finally {
      setTimelineLoading(null);
    }
  }

  return (
    <ProtectedRoute sellerOnly>
      <DashboardLayout title="Fulfillment" eyebrow="Seller dashboard">
        <section className="filter-panel operations-filter-panel" aria-label="Fulfillment filters">
          <ClipboardCheck size={18} aria-hidden="true" />
          <label>
            Status
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as FulfillmentFilter)}>
              <option value="all">All statuses</option>
              {fulfillmentStatuses.map((status) => (
                <option key={status} value={status}>{humanFulfillmentStatus(status)}</option>
              ))}
            </select>
          </label>
          <label>
            Search
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Auction, lot, winner" />
          </label>
          <button className="secondary-button" type="button" onClick={load} disabled={isLoading}>
            <Search size={17} aria-hidden="true" />
            Search
          </button>
          <button className="secondary-button" type="button" onClick={load} disabled={isLoading}>
            <RefreshCw size={17} aria-hidden="true" />
            Refresh
          </button>
        </section>

        {isLoading ? <LoadingState label="Loading fulfillment records" /> : null}
        {error ? <ErrorState message={error} /> : null}
        {success ? <div className="state-panel success">{success}</div> : null}

        {!isLoading && !error ? (
          <>
            <section className="metric-grid compact" aria-label="Fulfillment summary">
              {metrics.map(([label, value]) => (
                <article className="metric-card" key={label}>
                  <ClipboardCheck size={18} aria-hidden="true" />
                  <span>{label}</span>
                  <strong>{value}</strong>
                </article>
              ))}
            </section>

            {records.length === 0 ? (
              <EmptyState title="No fulfillment records" message="Won lots will appear here after the backend calculates winners." />
            ) : (
              <div className="fulfillment-list">
                {records.map((record) => (
                  <form
                    className="fulfillment-card"
                    key={record.id}
                    onSubmit={(event) => {
                      event.preventDefault();
                      void handleSave(record, new FormData(event.currentTarget));
                    }}
                  >
                    <div className="card-topline">
                      <StatusPill status={record.status} />
                      <span>{record.last_follow_up_at ? `Followed up ${formatDateTime(record.last_follow_up_at)}` : "No follow-up yet"}</span>
                    </div>
                    <div>
                      <h3>{record.lot_title}</h3>
                      <p>{record.auction_title}</p>
                    </div>
                    <dl className="mini-meta horizontal">
                      <div>
                        <dt>Winner</dt>
                        <dd>{record.winner_username}</dd>
                      </div>
                      <div>
                        <dt>Bid</dt>
                        <dd>{formatMoney(record.winning_bid_amount)}</dd>
                      </div>
                      <div>
                        <dt>Status</dt>
                        <dd>{humanFulfillmentStatus(record.status)}</dd>
                      </div>
                    </dl>
                    <label>
                      Fulfillment status
                      <select name="status" defaultValue={record.status}>
                        {statusOptions(record).map((status) => (
                          <option key={status} value={status}>{humanFulfillmentStatus(status)}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Confirmation notes
                      <textarea name="confirmation_notes" defaultValue={record.confirmation_notes} rows={3} />
                    </label>
                    <label>
                      Seller notes
                      <textarea name="seller_notes" defaultValue={record.seller_notes} rows={3} />
                    </label>
                    <label>
                      Admin notes
                      <textarea name="admin_notes" defaultValue={record.admin_notes} rows={3} />
                    </label>
                    <label>
                      Winner-visible message
                      <textarea name="public_winner_message" defaultValue={record.public_winner_message} rows={2} />
                    </label>
                    <button className="primary-button" type="submit">Save fulfillment</button>
                    <button className="secondary-button" type="button" onClick={() => void toggleTimeline(record.id)}>
                      <FileClock size={17} aria-hidden="true" />
                      {timelines[record.id] ? "Hide timeline" : "Show timeline"}
                    </button>
                    {timelineLoading === record.id ? <LoadingState label="Loading timeline" /> : null}
                    {timelines[record.id] ? <Timeline events={timelines[record.id]} /> : null}
                  </form>
                ))}
              </div>
            )}
          </>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}

function Timeline({ events }: { events: FulfillmentTimelineEvent[] }) {
  if (events.length === 0) {
    return <EmptyState title="No timeline yet" message="Fulfillment events will appear after updates are recorded." />;
  }

  return (
    <div className="timeline-list">
      {events.map((event) => (
        <article className="timeline-item" key={event.id}>
          <span>{formatDateTime(event.created_at)}</span>
          <strong>{humanTimelineEvent(event.event_type)}</strong>
          <p>
            {event.old_status && event.new_status
              ? `${event.old_status} -> ${event.new_status}`
              : event.notification_type || event.note_field || event.actor_username || "Recorded by BIDALS"}
          </p>
        </article>
      ))}
    </div>
  );
}
