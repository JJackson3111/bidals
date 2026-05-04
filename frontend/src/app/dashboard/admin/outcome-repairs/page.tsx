"use client";

import { FormEvent, useEffect, useState } from "react";
import { AlertTriangle, FileClock, MessageSquare, RefreshCw, ShieldCheck } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { StatusPill } from "@/components/StatusPill";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, humanOutcomeRepairStatus, humanWinnerStatus } from "@/lib/format";
import type { AuditLog, OutcomeRepairComment, OutcomeRepairRequest } from "@/lib/types";

export default function OutcomeRepairsPage() {
  const { user } = useAuth();
  const [repairs, setRepairs] = useState<OutcomeRepairRequest[]>([]);
  const [comments, setComments] = useState<Record<number, OutcomeRepairComment[]>>({});
  const [visibleComments, setVisibleComments] = useState<Record<number, boolean>>({});
  const [auditEvents, setAuditEvents] = useState<Record<number, AuditLog[]>>({});
  const [visibleAudit, setVisibleAudit] = useState<Record<number, boolean>>({});
  const [commentDrafts, setCommentDrafts] = useState<Record<number, string>>({});
  const [approvalNotes, setApprovalNotes] = useState<Record<number, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionId, setActionId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.getOutcomeRepairs();
      setRepairs(response.results);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load repair requests.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);
    const formData = new FormData(event.currentTarget);
    try {
      const repair = await api.createOutcomeRepair({
        lot: String(formData.get("lot") ?? ""),
        requested_winning_bid: String(formData.get("requested_winning_bid") ?? ""),
        reason: String(formData.get("reason") ?? ""),
      });
      setRepairs((current) => [repair, ...current]);
      setSuccess("Repair request created for review.");
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create repair request.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleAction(repair: OutcomeRepairRequest, action: "approve" | "reject" | "apply") {
    setError(null);
    setSuccess(null);
    setActionId(repair.id);
    try {
      const saved = action === "approve"
        ? await api.approveOutcomeRepair(repair.id, { approval_notes: approvalNotes[repair.id] ?? "" })
        : action === "reject"
          ? await api.rejectOutcomeRepair(repair.id)
          : await api.applyOutcomeRepair(repair.id);
      setRepairs((current) => current.map((item) => (item.id === saved.id ? saved : item)));
      setSuccess(`Repair ${humanOutcomeRepairStatus(saved.status).toLowerCase()}.`);
      if (action === "approve") {
        setApprovalNotes((current) => ({ ...current, [repair.id]: "" }));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to update repair request.");
    } finally {
      setActionId(null);
    }
  }

  async function loadComments(repairId: number) {
    setError(null);
    try {
      const response = await api.getOutcomeRepairComments(repairId);
      setComments((current) => ({ ...current, [repairId]: response.results }));
      setVisibleComments((current) => ({ ...current, [repairId]: true }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load repair comments.");
    }
  }

  async function toggleComments(repairId: number) {
    if (visibleComments[repairId]) {
      setVisibleComments((current) => ({ ...current, [repairId]: false }));
      return;
    }

    if (comments[repairId]) {
      setVisibleComments((current) => ({ ...current, [repairId]: true }));
      return;
    }

    await loadComments(repairId);
  }

  async function handleAddComment(event: FormEvent<HTMLFormElement>, repairId: number) {
    event.preventDefault();
    const commentText = (commentDrafts[repairId] ?? "").trim();
    if (!commentText) return;

    setError(null);
    setSuccess(null);
    setActionId(repairId);
    try {
      const comment = await api.createOutcomeRepairComment(repairId, commentText);
      setComments((current) => ({ ...current, [repairId]: [...(current[repairId] ?? []), comment] }));
      setVisibleComments((current) => ({ ...current, [repairId]: true }));
      setCommentDrafts((current) => ({ ...current, [repairId]: "" }));
      setSuccess("Repair comment added.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to add repair comment.");
    } finally {
      setActionId(null);
    }
  }

  async function loadRepairAudit(repairId: number) {
    setError(null);
    try {
      const response = await api.getOutcomeRepairAudit(repairId);
      setAuditEvents((current) => ({ ...current, [repairId]: response.results }));
      setVisibleAudit((current) => ({ ...current, [repairId]: true }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load repair audit.");
    }
  }

  async function toggleRepairAudit(repairId: number) {
    if (visibleAudit[repairId]) {
      setVisibleAudit((current) => ({ ...current, [repairId]: false }));
      return;
    }

    if (auditEvents[repairId]) {
      setVisibleAudit((current) => ({ ...current, [repairId]: true }));
      return;
    }

    await loadRepairAudit(repairId);
  }

  return (
    <ProtectedRoute adminOnly>
      <DashboardLayout title="Outcome repairs" eyebrow="Admin operations">
        <section className="fulfillment-card">
          <div className="card-topline">
            <StatusPill status="admin-only" />
            <span>Reviewed corrections only</span>
          </div>
          <h2>Create repair request</h2>
          <form className="form-grid" onSubmit={(event) => void handleCreate(event)}>
            <label>
              Lot ID
              <input name="lot" inputMode="numeric" required />
            </label>
            <label>
              Accepted winning bid ID
              <input name="requested_winning_bid" inputMode="numeric" required />
            </label>
            <label>
              Reason
              <textarea name="reason" rows={3} required />
            </label>
            <button className="primary-button" type="submit" disabled={isSubmitting}>
              <ShieldCheck size={17} aria-hidden="true" />
              {isSubmitting ? "Creating" : "Create request"}
            </button>
          </form>
        </section>

        <section className="filter-panel operations-filter-panel" aria-label="Repair controls">
          <ShieldCheck size={18} aria-hidden="true" />
          <button className="secondary-button" type="button" onClick={load} disabled={isLoading}>
            <RefreshCw size={17} aria-hidden="true" />
            Refresh
          </button>
        </section>

        {isLoading ? <LoadingState label="Loading repair requests" /> : null}
        {error ? <ErrorState message={error} /> : null}
        {success ? <div className="state-panel success">{success}</div> : null}

        {!isLoading && !error ? (
          repairs.length === 0 ? (
            <EmptyState title="No repair requests" message="Exceptional outcome corrections will appear here." />
          ) : (
            <div className="dashboard-grid">
              {repairs.map((repair) => (
                <article className="auction-card management-card" key={repair.id}>
                  {(() => {
                    const requesterIsCurrentUser = user?.id === repair.requested_by;
                    const canApprove = repair.status === "pending_review" && !requesterIsCurrentUser;
                    const canApply = repair.status === "approved";
                    return (
                      <>
                  <div className="card-topline">
                    <StatusPill status={repair.status} />
                    <span>{formatDateTime(repair.created_at)}</span>
                  </div>
                  <h2>{repair.lot_title}</h2>
                  <p>{repair.auction_title}</p>
                  <dl className="mini-meta horizontal">
                    <div>
                      <dt>Current outcome</dt>
                      <dd>{humanWinnerStatus(repair.current_outcome)}</dd>
                    </div>
                    <div>
                      <dt>Requested winner</dt>
                      <dd>{repair.requested_winner_username}</dd>
                    </div>
                    <div>
                      <dt>Requested bid</dt>
                      <dd>{formatMoney(repair.requested_winning_bid_amount)}</dd>
                    </div>
                    <div>
                      <dt>Status</dt>
                      <dd>{humanOutcomeRepairStatus(repair.status)}</dd>
                    </div>
                    <div>
                      <dt>Requested by</dt>
                      <dd>{repair.requested_by_username}</dd>
                    </div>
                    <div>
                      <dt>Approved by</dt>
                      <dd>{repair.reviewed_by_username ?? "Not approved"}</dd>
                    </div>
                  </dl>
                  <p>{repair.reason}</p>
                  {repair.approval_notes ? (
                    <div className="state-panel">
                      <strong>Approval notes</strong>
                      <p>{repair.approval_notes}</p>
                    </div>
                  ) : null}
                  {repair.status === "applied" ? (
                    <div className="state-panel warning">
                      <AlertTriangle size={18} aria-hidden="true" />
                      This repair changed a finalized outcome. Review the audit chain before relying on the corrected winner state.
                    </div>
                  ) : null}
                  {repair.status === "pending_review" ? (
                    <label className="compact-field">
                      Approval notes
                      <textarea
                        rows={2}
                        value={approvalNotes[repair.id] ?? ""}
                        onChange={(event) => setApprovalNotes((current) => ({ ...current, [repair.id]: event.target.value }))}
                        placeholder="Optional reviewer note for the audit trail"
                      />
                    </label>
                  ) : null}
                  {requesterIsCurrentUser && repair.status === "pending_review" ? (
                    <div className="state-panel error">A different admin must approve this request.</div>
                  ) : null}
                  <div className="button-row">
                    {repair.status === "pending_review" ? (
                      <>
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => void handleAction(repair, "approve")}
                          disabled={!canApprove || actionId === repair.id}
                        >
                          Approve
                        </button>
                        <button
                          className="secondary-button danger"
                          type="button"
                          onClick={() => void handleAction(repair, "reject")}
                          disabled={actionId === repair.id}
                        >
                          Reject
                        </button>
                      </>
                    ) : null}
                    {canApply ? (
                      <button
                        className="primary-button"
                        type="button"
                        onClick={() => void handleAction(repair, "apply")}
                        disabled={actionId === repair.id}
                      >
                        Apply repair
                      </button>
                    ) : null}
                  </div>
                  <section className="repair-comments" aria-label={`Comments for repair ${repair.id}`}>
                    <button className="secondary-button" type="button" onClick={() => void toggleComments(repair.id)}>
                      <MessageSquare size={17} aria-hidden="true" />
                      {visibleComments[repair.id] ? "Hide comments" : "Show comments"}
                    </button>
                    {visibleComments[repair.id] ? (
                      <div className="comment-thread">
                        {(comments[repair.id] ?? []).length === 0 ? (
                          <p>No comments yet.</p>
                        ) : (
                          comments[repair.id].map((comment) => (
                            <article className="comment-item" key={comment.id}>
                              <div className="card-topline">
                                <strong>{comment.author_username}</strong>
                                <span>{formatDateTime(comment.created_at)}</span>
                              </div>
                              <p>{comment.comment_text}</p>
                            </article>
                          ))
                        )}
                        <form className="comment-form" onSubmit={(event) => void handleAddComment(event, repair.id)}>
                          <label>
                            Add comment
                            <textarea
                              rows={3}
                              value={commentDrafts[repair.id] ?? ""}
                              onChange={(event) => setCommentDrafts((current) => ({ ...current, [repair.id]: event.target.value }))}
                              required
                            />
                          </label>
                          <button className="secondary-button" type="submit" disabled={actionId === repair.id}>
                            Add comment
                          </button>
                        </form>
                      </div>
                    ) : null}
                  </section>
                  <section className="repair-comments" aria-label={`Audit for repair ${repair.id}`}>
                    <button className="secondary-button" type="button" onClick={() => void toggleRepairAudit(repair.id)}>
                      <FileClock size={17} aria-hidden="true" />
                      {visibleAudit[repair.id] ? "Hide audit" : "Show audit"}
                    </button>
                    {visibleAudit[repair.id] ? (
                      <div className="timeline-list">
                        {(auditEvents[repair.id] ?? []).length === 0 ? (
                          <p>No repair audit events yet.</p>
                        ) : (
                          auditEvents[repair.id].map((event) => (
                            <article className="timeline-item" key={event.id}>
                              <strong>{event.action}</strong>
                              <span>{event.actor_username || "System"} - {formatDateTime(event.server_timestamp)}</span>
                              <span>{event.entity_type}:{event.entity_id}</span>
                              <pre className="audit-json">{JSON.stringify(event.metadata, null, 2)}</pre>
                            </article>
                          ))
                        )}
                      </div>
                    ) : null}
                  </section>
                      </>
                    );
                  })()}
                </article>
              ))}
            </div>
          )
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}
