"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Save } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ErrorState, LoadingState } from "@/components/StateViews";
import { api, ApiError } from "@/lib/api";
import type { AuctionStatus } from "@/lib/types";

const LIVE_START_TIME_LOCKED_ERROR = "Live auction start time cannot be changed.";

function toDateTimeLocal(value: string): string {
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function toIsoDateTime(value: string): string {
  return new Date(value).toISOString();
}

function loadErrorMessage(error: unknown): string {
  if (error instanceof ApiError && [403, 404].includes(error.status)) {
    return "Auction not found or you do not have access to edit it.";
  }

  return error instanceof ApiError ? error.message : "Unable to load auction.";
}

function errorValueIncludes(value: unknown, expectedMessage: string): boolean {
  if (typeof value === "string") return value === expectedMessage;
  if (Array.isArray(value)) return value.some((item) => errorValueIncludes(item, expectedMessage));
  if (value && typeof value === "object") {
    return Object.values(value).some((item) => errorValueIncludes(item, expectedMessage));
  }
  return false;
}

function isLiveStartTimeLockedError(error: unknown): error is ApiError {
  return error instanceof ApiError && errorValueIncludes(error.body.start_time, LIVE_START_TIME_LOCKED_ERROR);
}

function isAuctionStatus(value: unknown): value is AuctionStatus {
  return ["draft", "scheduled", "live", "ended", "cancelled"].includes(String(value));
}

export default function EditAuctionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [auctionStatus, setAuctionStatus] = useState<AuctionStatus>("draft");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveTimingNotice, setLiveTimingNotice] = useState(false);
  const [isStartTimeLocked, setIsStartTimeLocked] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      setLiveTimingNotice(false);
      try {
        const auction = await api.getManageAuction(params.id);
        const effectiveStatusValue = (auction as { effective_status?: unknown }).effective_status;
        const effectiveStatus = isAuctionStatus(effectiveStatusValue) ? effectiveStatusValue : auction.status;
        setTitle(auction.title);
        setDescription(auction.description);
        setStartTime(toDateTimeLocal(auction.start_time));
        setEndTime(toDateTimeLocal(auction.end_time));
        setAuctionStatus(auction.status);
        setIsStartTimeLocked(effectiveStatus === "live");
      } catch (err) {
        setError(loadErrorMessage(err));
        setIsStartTimeLocked(false);
      } finally {
        setIsLoading(false);
      }
    }

    if (params.id) load();
  }, [params.id]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLiveTimingNotice(false);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      const auction = await api.updateAuction(params.id, {
        title,
        description,
        ...(isStartTimeLocked ? {} : { start_time: toIsoDateTime(startTime) }),
        end_time: toIsoDateTime(endTime),
        status: auctionStatus,
      });
      setSuccess("Auction saved.");
      router.push(`/auctions/${auction.id}`);
    } catch (err) {
      if (isLiveStartTimeLockedError(err)) {
        setLiveTimingNotice(true);
      } else {
        setError(err instanceof ApiError ? err.message : "Unable to save auction.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedRoute sellerOnly>
      <DashboardLayout title="Edit auction">
        {isLoading ? <LoadingState label="Loading auction" /> : null}
        {!isLoading && error ? <ErrorState message={error} /> : null}
        {!isLoading && !error ? (
          <form className="form-panel" onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-field">
                <label htmlFor="title">Title</label>
                <input id="title" required value={title} onChange={(event) => setTitle(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="description">Description</label>
                <textarea id="description" value={description} onChange={(event) => setDescription(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="start-time">Start time</label>
                <span className="form-help">
                  {isStartTimeLocked ? "Start time is locked once bidding is live." : "Server time remains the authority for live bidding."}
                </span>
                <input
                  id="start-time"
                  required
                  disabled={isStartTimeLocked}
                  type="datetime-local"
                  value={startTime}
                  onChange={(event) => setStartTime(event.target.value)}
                />
              </div>
              <div className="form-field">
                <label htmlFor="end-time">End time</label>
                <span className="form-help">End time must be after the start time.</span>
                <input id="end-time" required type="datetime-local" value={endTime} onChange={(event) => setEndTime(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="status">Status</label>
                <select id="status" value={auctionStatus} onChange={(event) => setAuctionStatus(event.target.value as AuctionStatus)}>
                  <option value="draft">Draft</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="live">Live</option>
                  <option value="ended">Ended</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </div>
            {success ? <div className="form-success" role="status">{success}</div> : null}
            {liveTimingNotice ? (
              <div className="form-error" role="alert">
                Auction timing is locked once bidding is live.
                <br />
                You can still edit permitted lot details.
              </div>
            ) : null}
            {error ? <div className="form-error" role="alert">{error}</div> : null}
            <button className="primary-button" disabled={isSubmitting} type="submit">
              <Save size={18} aria-hidden="true" />
              {isSubmitting ? "Saving" : "Save auction"}
            </button>
          </form>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}
