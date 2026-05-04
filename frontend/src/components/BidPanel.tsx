"use client";

import { FormEvent, useState } from "react";
import { CheckCircle2, CircleDollarSign, XCircle } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import { formatMoney, humanBidReason } from "@/lib/format";
import type { BidRejectedResponse, BidResponse, Lot } from "@/lib/types";

export function BidPanel({
  lot,
  onBidSettled,
}: {
  lot: Lot;
  onBidSettled: (response: BidResponse) => Promise<void> | void;
}) {
  const [amount, setAmount] = useState("");
  const [message, setMessage] = useState<BidResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsSubmitting(true);

    try {
      const response = await api.placeBid(lot.id, amount);
      setMessage(response);
      if (response.status === "accepted") {
        setAmount("");
      }
      await onBidSettled(response);
    } catch (err) {
      if (err instanceof ApiError) {
        if (isBidRejectedResponse(err.body)) {
          setMessage(err.body);
          await onBidSettled(err.body);
        } else {
          setError(err.message);
        }
      } else {
        setError("Unable to place bid.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="bid-panel" aria-label="Place bid">
      <div>
        <span className="eyebrow">Current price</span>
        <strong>{formatMoney(lot.current_price)}</strong>
      </div>
      <form onSubmit={handleSubmit} className="bid-form">
        <label htmlFor="bid-amount">Bid amount</label>
        <span className="form-help">Increment: {formatMoney(lot.bid_increment)}</span>
        <div className="bid-input-row">
          <input
            id="bid-amount"
            inputMode="decimal"
            min="0"
            name="amount"
            onChange={(event) => setAmount(event.target.value)}
            placeholder={lot.current_price}
            required
            step="0.01"
            type="number"
            value={amount}
          />
          <button className="primary-button" disabled={isSubmitting} type="submit">
            <CircleDollarSign size={18} aria-hidden="true" />
            {isSubmitting ? "Sending" : "Place bid"}
          </button>
        </div>
      </form>

      {message?.status === "accepted" ? (
        <div className="bid-message accepted" role="status">
          <CheckCircle2 size={18} aria-hidden="true" />
          <span>Bid accepted at {formatMoney(message.current_price)}.</span>
        </div>
      ) : null}

      {message?.status === "rejected" ? (
        <div className="bid-message rejected" role="alert">
          <XCircle size={18} aria-hidden="true" />
          <span>
            {message.message || humanBidReason(message.reason)} <code>{message.reason}</code>
          </span>
        </div>
      ) : null}

      {error ? (
        <div className="bid-message rejected" role="alert">
          <XCircle size={18} aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}
    </section>
  );
}

function isBidRejectedResponse(body: unknown): body is BidRejectedResponse {
  if (!body || typeof body !== "object") return false;
  const record = body as Record<string, unknown>;
  return (
    record.status === "rejected" &&
    typeof record.reason === "string" &&
    typeof record.lot_id === "number" &&
    typeof record.current_price === "string" &&
    typeof record.server_timestamp === "string"
  );
}
