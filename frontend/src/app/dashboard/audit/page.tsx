"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, FileClock, Filter } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AuditLog } from "@/lib/types";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [actionFilter, setActionFilter] = useState("all");
  const [entityFilter, setEntityFilter] = useState("all");
  const [actorFilter, setActorFilter] = useState("");
  const [entityIdFilter, setEntityIdFilter] = useState("");
  const [bidStatusFilter, setBidStatusFilter] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [metadataSearch, setMetadataSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        setLogs(
          await api.getAuditLogs({
            action: actionFilter === "all" ? undefined : actionFilter,
            entity_type: entityFilter === "all" ? undefined : entityFilter,
            actor: actorFilter || undefined,
            entity_id: entityIdFilter || undefined,
            bid_status: bidStatusFilter === "all" ? undefined : bidStatusFilter,
            date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
            date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
            metadata_search: metadataSearch || undefined,
          }),
        );
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load audit logs.");
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [actionFilter, actorFilter, bidStatusFilter, dateFrom, dateTo, entityFilter, entityIdFilter, metadataSearch]);

  const actionOptions = useMemo(
    () => [
      "user_registered",
      "auction_created",
      "auction_updated",
      "lot_created",
      "lot_updated",
      "bid_accepted",
      "bid_rejected",
      "auction_ended",
      "winner_calculated",
      "admin_action",
    ],
    [],
  );
  const entityOptions = useMemo(() => ["auction", "lot", "bid", "user", "demo_seed"], []);
  const hasActiveFilters =
    actionFilter !== "all" ||
    entityFilter !== "all" ||
    actorFilter ||
    entityIdFilter ||
    bidStatusFilter !== "all" ||
    dateFrom ||
    dateTo ||
    metadataSearch;

  return (
    <ProtectedRoute adminOnly>
      <DashboardLayout title="Audit log" eyebrow="Admin">
        {!isLoading && !error ? (
          <section className="metric-grid compact" aria-label="Audit summary">
            <article className="metric-card">
              <FileClock size={18} aria-hidden="true" />
              <span>Total events</span>
              <strong>{logs.length}</strong>
            </article>
            <article className="metric-card">
              <Activity size={18} aria-hidden="true" />
              <span>Bid events</span>
              <strong>{logs.filter((log) => log.action.startsWith("bid_")).length}</strong>
            </article>
          </section>
        ) : null}

        <section className="filter-panel audit-filter-panel" aria-label="Audit filters">
          <Filter size={18} aria-hidden="true" />
          <label>
            Action
            <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)}>
              <option value="all">All actions</option>
              {actionOptions.map((action) => (
                <option key={action} value={action}>
                  {action}
                </option>
              ))}
            </select>
          </label>
          <label>
            Entity
            <select value={entityFilter} onChange={(event) => setEntityFilter(event.target.value)}>
              <option value="all">All entities</option>
              {entityOptions.map((entity) => (
                <option key={entity} value={entity}>
                  {entity}
                </option>
              ))}
            </select>
          </label>
          <label>
            Actor
            <input value={actorFilter} onChange={(event) => setActorFilter(event.target.value)} placeholder="username, email, or id" />
          </label>
          <label>
            Entity ID
            <input value={entityIdFilter} onChange={(event) => setEntityIdFilter(event.target.value)} placeholder="123" />
          </label>
          <label>
            Bid status
            <select value={bidStatusFilter} onChange={(event) => setBidStatusFilter(event.target.value)}>
              <option value="all">Any bid event</option>
              <option value="accepted">Accepted bids</option>
              <option value="rejected">Rejected bids</option>
            </select>
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
            Metadata
            <input value={metadataSearch} onChange={(event) => setMetadataSearch(event.target.value)} placeholder="amount, reason, lot id" />
          </label>
        </section>

        {isLoading ? <LoadingState label="Loading audit logs" /> : null}
        {error ? <ErrorState message={error} /> : null}
        {!isLoading && !error && logs.length === 0 && !hasActiveFilters ? (
          <EmptyState title="No audit logs" message="Critical activity will appear here." />
        ) : null}
        {!isLoading && !error && logs.length === 0 && hasActiveFilters ? (
          <EmptyState title="No matching activity" message="Change the filters to view more audit events." />
        ) : null}
        {!isLoading && !error && logs.length > 0 ? (
          <div className="audit-list">
            {logs.map((log) => (
              <article className="audit-row" key={log.id}>
                <strong>{log.action}</strong>
                <div className="audit-meta">
                  <span>{log.actor_username || "System"}</span>
                  <span>{log.entity_type}:{log.entity_id}</span>
                  <span>{formatDateTime(log.server_timestamp)}</span>
                </div>
                <pre className="audit-json">{JSON.stringify(log.metadata, null, 2)}</pre>
              </article>
            ))}
          </div>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}
