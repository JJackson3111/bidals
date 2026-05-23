import type { BidRejectionReason, FulfillmentStatus, Lot, LotWinnerStatus, OutcomeRepairStatus } from "@/lib/types";

export function formatMoney(value: string | number): string {
  const numeric = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(numeric)) return String(value);

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(numeric);
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function getTimeRemaining(endTime: string): string {
  const diff = new Date(endTime).getTime() - Date.now();
  if (diff <= 0) return "Ended";

  const totalSeconds = Math.floor(diff / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m ${seconds}s`;
}

export function humanBidReason(reason: BidRejectionReason): string {
  const messages: Record<BidRejectionReason, string> = {
    AUCTION_NOT_LIVE: "This auction is not currently live.",
    AUCTION_NOT_STARTED: "This auction has not started yet.",
    AUCTION_ENDED: "This auction has ended.",
    LOT_CLOSED: "This lot is closed.",
    BID_TOO_LOW: "Your bid is too low.",
    INVALID_INCREMENT: "Your bid does not match the required increment.",
    USER_NOT_ALLOWED: "You are not allowed to bid on this lot.",
    UNAUTHENTICATED: "Please log in before bidding.",
    RATE_LIMITED: "Too many bid attempts. Please wait before bidding again.",
    SERVER_ERROR: "The bid could not be processed. Please try again.",
  };

  return messages[reason] ?? "The bid was rejected.";
}

export function getLotPrimaryImageUrl(lot: Lot): string | null {
  return lot.uploaded_images?.[0]?.image_url || lot.images?.[0] || null;
}

export function humanWinnerStatus(status: LotWinnerStatus): string {
  const messages: Record<LotWinnerStatus, string> = {
    pending: "Pending",
    winner_assigned: "Winner assigned",
    no_bids: "No bids",
    reserve_not_met: "Reserve not met",
  };
  return messages[status] ?? status;
}

export function humanFulfillmentStatus(status: FulfillmentStatus): string {
  const messages: Record<FulfillmentStatus, string> = {
    pending_confirmation: "Pending confirmation",
    winner_confirmed: "Winner confirmed",
    seller_contacted: "Seller contacted",
    awaiting_collection_or_delivery: "Awaiting collection or delivery",
    completed: "Completed",
    cancelled: "Cancelled",
    disputed: "Disputed",
  };
  return messages[status] ?? status;
}

export function humanOutcomeRepairStatus(status: OutcomeRepairStatus): string {
  const messages: Record<OutcomeRepairStatus, string> = {
    pending_review: "Pending review",
    approved: "Approved",
    rejected: "Rejected",
    applied: "Applied",
    cancelled: "Cancelled",
  };
  return messages[status] ?? status;
}

export function humanTimelineEvent(eventType: string): string {
  const messages: Record<string, string> = {
    fulfillment_created: "Fulfillment created",
    fulfillment_status_changed: "Status changed",
    fulfillment_invalid_transition: "Invalid transition rejected",
    fulfillment_confirmation_notes_updated: "Confirmation notes updated",
    fulfillment_seller_notes_updated: "Seller notes updated",
    fulfillment_admin_notes_updated: "Admin notes updated",
    fulfillment_completed: "Fulfillment completed",
    fulfillment_cancelled: "Fulfillment cancelled",
    fulfillment_disputed: "Fulfillment disputed",
    notification_event: "Notification recorded",
    winner_calculated: "Winner calculated",
    winner_outcome_backfilled: "Winner outcome backfilled",
    outcome_repair_requested: "Repair requested",
    outcome_repair_approved: "Repair approved",
    outcome_repair_rejected: "Repair rejected",
    outcome_repair_applied: "Repair applied",
    outcome_repair_cancelled: "Repair cancelled",
  };
  return messages[eventType] ?? eventType;
}
