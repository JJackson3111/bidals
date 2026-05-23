"use client";

import { useCallback, useEffect, useState } from "react";
import { ActivitySquare, AlertTriangle, Bell, Clock3, Download, FileClock, RefreshCw, ShieldCheck, Trophy } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, humanBidReason } from "@/lib/format";
import type { AuditLog, OperationsBidEvent, OperationsReport, OutboundNotification } from "@/lib/types";

export default function OperationsPage() {
  const [report, setReport] = useState<OperationsReport | null>(null);
  const [windowMinutes, setWindowMinutes] = useState("60");
  const [exportFilters, setExportFilters] = useState({
    date_from: "",
    date_to: "",
    actor: "",
    action_type: "",
    entity_type: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setReport(await api.getOperationsReport({ window_minutes: windowMinutes }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load operations report.");
    } finally {
      setIsLoading(false);
    }
  }, [windowMinutes]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleExport() {
    setIsExporting(true);
    setError(null);
    try {
      const blob = await api.downloadAdminActivityExport({
        date_from: exportFilters.date_from || undefined,
        date_to: exportFilters.date_to || undefined,
        actor: exportFilters.actor || undefined,
        action_type: exportFilters.action_type || undefined,
        entity_type: exportFilters.entity_type || undefined,
      });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `bidals-admin-activity-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to export admin activity.");
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <ProtectedRoute adminOnly>
      <DashboardLayout title="Operations" eyebrow="Admin">
        <section className="filter-panel operations-filter-panel" aria-label="Operations filters">
          <ActivitySquare size={18} aria-hidden="true" />
          <label>
            Window
            <select value={windowMinutes} onChange={(event) => setWindowMinutes(event.target.value)}>
              <option value="15">Last 15 minutes</option>
              <option value="60">Last hour</option>
              <option value="240">Last 4 hours</option>
              <option value="1440">Last 24 hours</option>
            </select>
          </label>
          <button className="secondary-button" type="button" onClick={load} disabled={isLoading}>
            <RefreshCw size={17} aria-hidden="true" />
            Refresh
          </button>
        </section>

        <section className="filter-panel operations-filter-panel" aria-label="Admin activity export">
          <Download size={18} aria-hidden="true" />
          <label>
            From
            <input
              type="datetime-local"
              value={exportFilters.date_from}
              onChange={(event) => setExportFilters((current) => ({ ...current, date_from: event.target.value }))}
            />
          </label>
          <label>
            To
            <input
              type="datetime-local"
              value={exportFilters.date_to}
              onChange={(event) => setExportFilters((current) => ({ ...current, date_to: event.target.value }))}
            />
          </label>
          <label>
            Actor
            <input
              value={exportFilters.actor}
              onChange={(event) => setExportFilters((current) => ({ ...current, actor: event.target.value }))}
              placeholder="Username, email, or id"
            />
          </label>
          <label>
            Action
            <select
              value={exportFilters.action_type}
              onChange={(event) => setExportFilters((current) => ({ ...current, action_type: event.target.value }))}
            >
              <option value="">All actions</option>
              <option value="outcome_repair_requested">Repair requested</option>
              <option value="outcome_repair_approved">Repair approved</option>
              <option value="outcome_repair_applied">Repair applied</option>
              <option value="fulfillment_status_changed">Fulfillment changed</option>
              <option value="admin_activity_exported">Activity exported</option>
            </select>
          </label>
          <label>
            Entity
            <select
              value={exportFilters.entity_type}
              onChange={(event) => setExportFilters((current) => ({ ...current, entity_type: event.target.value }))}
            >
              <option value="">All entities</option>
              <option value="outcome_repair">Outcome repair</option>
              <option value="fulfillment">Fulfillment</option>
              <option value="lot">Lot</option>
              <option value="auction">Auction</option>
              <option value="notification">Notification</option>
            </select>
          </label>
          <button className="primary-button" type="button" onClick={() => void handleExport()} disabled={isExporting}>
            <Download size={17} aria-hidden="true" />
            {isExporting ? "Exporting" : "Export CSV"}
          </button>
        </section>

        {isLoading ? <LoadingState label="Loading operations report" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!isLoading && !error && report ? (
          <>
            <section className="metric-grid operations-metrics" aria-label="Operations summary">
              <article className="metric-card">
                <ShieldCheck size={18} aria-hidden="true" />
                <span>Total bids</span>
                <strong>{report.summary.total_bids}</strong>
              </article>
              <article className="metric-card">
                <ActivitySquare size={18} aria-hidden="true" />
                <span>Recent accepted</span>
                <strong>{report.summary.recent_accepted_bids}</strong>
              </article>
              <article className="metric-card">
                <AlertTriangle size={18} aria-hidden="true" />
                <span>Recent rejected</span>
                <strong>{report.summary.recent_rejected_bids}</strong>
              </article>
              <article className="metric-card">
                <FileClock size={18} aria-hidden="true" />
                <span>Audit events</span>
                <strong>{report.summary.recent_audit_events}</strong>
              </article>
              <article className="metric-card">
                <AlertTriangle size={18} aria-hidden="true" />
                <span>Server bid errors</span>
                <strong>{report.summary.recent_server_bid_errors}</strong>
              </article>
              <article className="metric-card">
                <Clock3 size={18} aria-hidden="true" />
                <span>Repeated failures</span>
                <strong>{report.summary.suspicious_repeated_failures}</strong>
              </article>
              <article className="metric-card">
                <Trophy size={18} aria-hidden="true" />
                <span>Winner calculations</span>
                <strong>{report.summary.winner_calculations}</strong>
              </article>
              <article className="metric-card">
                <Clock3 size={18} aria-hidden="true" />
                <span>Close runs</span>
                <strong>{report.summary.auction_close_runs}</strong>
              </article>
              <article className="metric-card">
                <Bell size={18} aria-hidden="true" />
                <span>Alert events</span>
                <strong>{report.summary.alert_events}</strong>
              </article>
              <article className="metric-card">
                <AlertTriangle size={18} aria-hidden="true" />
                <span>Bid anomalies</span>
                <strong>{report.summary.bid_anomalies}</strong>
              </article>
              <article className="metric-card">
                <AlertTriangle size={18} aria-hidden="true" />
                <span>Job failures</span>
                <strong>{report.summary.job_failures}</strong>
              </article>
              <article className="metric-card">
                <Bell size={18} aria-hidden="true" />
                <span>Pending email</span>
                <strong>{report.summary.pending_notifications}</strong>
              </article>
              <article className="metric-card">
                <Bell size={18} aria-hidden="true" />
                <span>Sent email</span>
                <strong>{report.summary.sent_notifications}</strong>
              </article>
              <article className="metric-card">
                <AlertTriangle size={18} aria-hidden="true" />
                <span>Failed email</span>
                <strong>{report.summary.failed_notifications}</strong>
              </article>
              <article className="metric-card">
                <Bell size={18} aria-hidden="true" />
                <span>Notification events</span>
                <strong>{report.summary.notification_events}</strong>
              </article>
              <article className="metric-card">
                <ActivitySquare size={18} aria-hidden="true" />
                <span>Fulfillment pending</span>
                <strong>{report.summary.fulfillment_pending_confirmation}</strong>
              </article>
              <article className="metric-card">
                <ActivitySquare size={18} aria-hidden="true" />
                <span>Fulfillment completed</span>
                <strong>{report.summary.fulfillment_completed}</strong>
              </article>
              <article className="metric-card">
                <AlertTriangle size={18} aria-hidden="true" />
                <span>Fulfillment disputed</span>
                <strong>{report.summary.fulfillment_disputed}</strong>
              </article>
            </section>

            <p className="ops-generated">Generated {formatDateTime(report.generated_at)} over a {report.window_minutes} minute window.</p>
            <p className="ops-generated">Anomaly thresholds: {report.thresholds.bid_anomaly_reject_threshold} rejected bids, {report.thresholds.bid_anomaly_rate_limit_threshold} rate-limit hits.</p>

            <section className="dashboard-two-column">
              <div className="dashboard-section">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">Bidding</span>
                    <h2>Recent accepted bids</h2>
                  </div>
                </div>
                {report.recent_accepted_bids.length === 0 ? (
                  <EmptyState title="No accepted bids" message="Accepted bid activity will appear here." />
                ) : (
                  <div className="activity-list">
                    {report.recent_accepted_bids.map((bid) => (
                      <BidActivityRow key={bid.id} bid={bid} />
                    ))}
                  </div>
                )}
              </div>

              <div className="dashboard-section">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">Bidding</span>
                    <h2>Recent rejected bids</h2>
                  </div>
                </div>
                {report.recent_rejected_bids.length === 0 ? (
                  <EmptyState title="No rejected bids" message="Rejected bid activity will appear here." />
                ) : (
                  <div className="activity-list">
                    {report.recent_rejected_bids.map((bid) => (
                      <BidActivityRow key={bid.id} bid={bid} />
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="dashboard-two-column">
              <div className="dashboard-section">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">Signals</span>
                    <h2>Repeated failures</h2>
                  </div>
                </div>
                {report.suspicious_repeated_failures.length === 0 ? (
                  <EmptyState
                    title="No repeated failures"
                    message={`No bidder has repeated the same rejection reason ${report.thresholds.bid_anomaly_reject_threshold} or more times in this window.`}
                  />
                ) : (
                  <div className="activity-list">
                    {report.suspicious_repeated_failures.map((failure) => (
                      <div className="activity-row" key={`${failure.bidder_id}-${failure.rejection_reason}`}>
                        <div>
                          <strong>{failure.bidder_username}</strong>
                          <span>{failure.rejection_reason ? humanBidReason(failure.rejection_reason) : "Unknown rejection reason"}</span>
                        </div>
                        <strong>{failure.count}</strong>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="dashboard-section">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">Audit</span>
                    <h2>Recent activity</h2>
                  </div>
                </div>
                {report.recent_audit_events.length === 0 ? (
                  <EmptyState title="No audit activity" message="Audit activity will appear here." />
                ) : (
                  <div className="audit-list">
                    {report.recent_audit_events.map((log) => (
                      <article className="audit-row" key={log.id}>
                        <strong>{log.action}</strong>
                        <div className="audit-meta">
                          <span>{log.actor_username || "System"}</span>
                          <span>{log.entity_type}:{log.entity_id}</span>
                          <span>{formatDateTime(log.server_timestamp)}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="dashboard-two-column">
              <AuditEventList
                eyebrow="Jobs"
                title="Auction closing runs"
                emptyTitle="No closing runs"
                emptyMessage="The scheduled auction close command has not reported in this window."
                logs={report.recent_auction_close_runs}
              />
              <AuditEventList
                eyebrow="Winners"
                title="Recent winner calculations"
                emptyTitle="No winner calculations"
                emptyMessage="Winner calculation events will appear after expired auctions are processed."
                logs={report.recent_winner_calculations}
              />
            </section>

            <section className="dashboard-two-column">
              <AuditEventList
                eyebrow="Alerts"
                title="Recent alert hooks"
                emptyTitle="No alert hooks"
                emptyMessage="Alert hook attempts will appear when anomaly or job-failure thresholds fire."
                logs={report.recent_alerts}
              />
              <AuditEventList
                eyebrow="Signals"
                title="Recent anomalies"
                emptyTitle="No anomalies"
                emptyMessage="Bid anomaly signals will appear here when thresholds are crossed."
                logs={report.recent_anomalies}
              />
            </section>

            <section className="dashboard-two-column">
              <AuditEventList
                eyebrow="Failures"
                title="Recent job failures"
                emptyTitle="No job failures"
                emptyMessage="Operational job failures will appear here if a scheduled command fails."
                logs={report.recent_job_failures}
              />
              <AuditEventList
                eyebrow="Notifications"
                title="Notification placeholders"
                emptyTitle="No notification events"
                emptyMessage="Placeholder notification events will appear here until delivery providers are added."
                logs={report.recent_notifications}
              />
            </section>

            <section className="dashboard-two-column">
              <NotificationList
                eyebrow="Email"
                title="Outbound notifications"
                emptyTitle="No outbound notifications"
                emptyMessage="Queued, sent, skipped, and failed email-ready notifications will appear here."
                notifications={report.recent_outbound_notifications}
              />
              <NotificationList
                eyebrow="Email"
                title="Failed notifications"
                emptyTitle="No failed notifications"
                emptyMessage="Failed delivery attempts will appear here for operational follow-up."
                notifications={report.recent_failed_notifications}
              />
            </section>

            <section className="dashboard-two-column">
              <AuditEventList
                eyebrow="Fulfillment"
                title="Recent fulfillment updates"
                emptyTitle="No fulfillment updates"
                emptyMessage="Seller/admin fulfillment workflow changes will appear here."
                logs={report.recent_fulfillment_updates}
              />
            </section>
          </>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}

function NotificationList({
  eyebrow,
  title,
  emptyTitle,
  emptyMessage,
  notifications,
}: {
  eyebrow: string;
  title: string;
  emptyTitle: string;
  emptyMessage: string;
  notifications: OutboundNotification[];
}) {
  return (
    <div className="dashboard-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
        </div>
      </div>
      {notifications.length === 0 ? (
        <EmptyState title={emptyTitle} message={emptyMessage} />
      ) : (
        <div className="management-list">
          {notifications.map((notification) => (
            <article className="management-row" key={notification.id}>
              <div>
                <strong>{notification.subject}</strong>
                <span>{notification.notification_type} - {notification.recipient_email || "No recipient email"}</span>
                <span>{formatDateTime(notification.created_at)}</span>
              </div>
              <div className="activity-value">
                <strong>{notification.status}</strong>
                {notification.error_message ? <span>{notification.error_message}</span> : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function AuditEventList({
  eyebrow,
  title,
  emptyTitle,
  emptyMessage,
  logs,
}: {
  eyebrow: string;
  title: string;
  emptyTitle: string;
  emptyMessage: string;
  logs: AuditLog[];
}) {
  return (
    <div className="dashboard-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
        </div>
      </div>
      {logs.length === 0 ? (
        <EmptyState title={emptyTitle} message={emptyMessage} />
      ) : (
        <div className="audit-list">
          {logs.map((log) => (
            <article className="audit-row" key={log.id}>
              <strong>{log.action}</strong>
              <div className="audit-meta">
                <span>{log.entity_type}:{log.entity_id}</span>
                <span>{formatDateTime(log.server_timestamp)}</span>
              </div>
              <pre className="audit-json">{JSON.stringify(log.metadata, null, 2)}</pre>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function BidActivityRow({ bid }: { bid: OperationsBidEvent }) {
  return (
    <div className="activity-row">
      <div>
        <strong>{bid.lot_title}</strong>
        <span>{bid.auction_title}</span>
        <span>{bid.bidder_username} - {formatDateTime(bid.server_timestamp)}</span>
      </div>
      <div className="activity-value">
        <strong>{formatMoney(bid.amount)}</strong>
        {bid.rejection_reason ? <span>{bid.rejection_reason}</span> : <span>{bid.status}</span>}
      </div>
    </div>
  );
}
