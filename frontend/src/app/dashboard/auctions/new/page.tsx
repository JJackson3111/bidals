"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Save } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { api, ApiError } from "@/lib/api";
import type { AuctionStatus } from "@/lib/types";

function toIsoDateTime(value: string): string {
  return new Date(value).toISOString();
}

export default function NewAuctionPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [status, setStatus] = useState<AuctionStatus>("draft");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const auction = await api.createAuction({
        title,
        description,
        start_time: toIsoDateTime(startTime),
        end_time: toIsoDateTime(endTime),
        status,
      });
      router.push(`/auctions/${auction.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create auction.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedRoute sellerOnly>
      <DashboardLayout title="Create auction">
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
              <span className="form-help">Server time decides whether bidding is allowed.</span>
              <input id="start-time" required type="datetime-local" value={startTime} onChange={(event) => setStartTime(event.target.value)} />
            </div>
            <div className="form-field">
              <label htmlFor="end-time">End time</label>
              <span className="form-help">End time must be after the start time.</span>
              <input id="end-time" required type="datetime-local" value={endTime} onChange={(event) => setEndTime(event.target.value)} />
            </div>
            <div className="form-field">
              <label htmlFor="status">Status</label>
              <span className="form-help">Use draft for private setup, scheduled or live for visible sales.</span>
              <select id="status" value={status} onChange={(event) => setStatus(event.target.value as AuctionStatus)}>
                <option value="draft">Draft</option>
                <option value="scheduled">Scheduled</option>
                <option value="live">Live</option>
              </select>
            </div>
          </div>
          {error ? <div className="form-error" role="alert">{error}</div> : null}
          <button className="primary-button" disabled={isSubmitting} type="submit">
            <Save size={18} aria-hidden="true" />
            {isSubmitting ? "Creating" : "Create auction"}
          </button>
        </form>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
