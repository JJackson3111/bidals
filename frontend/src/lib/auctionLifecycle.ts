import type { Auction, AuctionStatus, Lot, LotStatus } from "@/lib/types";

export type AuctionPhase = "scheduled" | "live" | "closed" | "cancelled" | "draft";

export type AuctionDisplayState = {
  badgeLabel: string;
  badgeStatus: string;
  countdownLabel: "Starts in" | "Ends in" | null;
  ctaLabel: string;
  phase: AuctionPhase;
  targetTime: string | null;
};

type AuctionTiming = Pick<Auction, "end_time" | "start_time" | "status">;

export function getAuctionPhase(auction: AuctionTiming, nowMs: number | null): AuctionPhase {
  const statusPhase = phaseFromAuctionStatus(auction.status);
  if (statusPhase === "cancelled" || statusPhase === "draft") {
    return statusPhase;
  }

  const startMs = new Date(auction.start_time).getTime();
  const endMs = new Date(auction.end_time).getTime();
  if (nowMs === null || !Number.isFinite(startMs) || !Number.isFinite(endMs)) {
    return statusPhase ?? "closed";
  }

  if (nowMs >= endMs) return "closed";
  if (nowMs >= startMs) return "live";
  return "scheduled";
}

export function getAuctionDisplayState(auction: AuctionTiming, nowMs: number | null): AuctionDisplayState {
  const phase = getAuctionPhase(auction, nowMs);

  if (phase === "scheduled") {
    return {
      badgeLabel: "Scheduled",
      badgeStatus: "scheduled",
      countdownLabel: "Starts in",
      ctaLabel: "Preview auction",
      phase,
      targetTime: auction.start_time,
    };
  }

  if (phase === "live") {
    return {
      badgeLabel: "Live",
      badgeStatus: "live",
      countdownLabel: "Ends in",
      ctaLabel: "Open auction",
      phase,
      targetTime: auction.end_time,
    };
  }

  if (phase === "closed") {
    return {
      badgeLabel: "Closed",
      badgeStatus: "closed",
      countdownLabel: null,
      ctaLabel: "View auction",
      phase,
      targetTime: null,
    };
  }

  if (phase === "cancelled") {
    return {
      badgeLabel: "Cancelled",
      badgeStatus: "cancelled",
      countdownLabel: null,
      ctaLabel: "View auction",
      phase,
      targetTime: null,
    };
  }

  return {
    badgeLabel: "Draft",
    badgeStatus: "draft",
    countdownLabel: null,
    ctaLabel: "View auction",
    phase,
    targetTime: null,
  };
}

export function phaseFromAuctionStatus(status: AuctionStatus | string): AuctionPhase | null {
  if (status === "scheduled") return "scheduled";
  if (status === "live" || status === "open") return "live";
  if (status === "ended" || status === "closed") return "closed";
  if (status === "cancelled") return "cancelled";
  if (status === "draft") return "draft";
  return null;
}

export function getDisplayLotStatus(lot: Pick<Lot, "status">, auctionPhase: AuctionPhase | null): LotStatus | "closed" {
  if (auctionPhase === "closed" && lot.status === "open") {
    return "closed";
  }
  return lot.status;
}

export function canBidOnLot(lot: Pick<Lot, "status">, auction: AuctionTiming | null, nowMs: number | null): boolean {
  if (!auction) return false;
  return getAuctionPhase(auction, nowMs) === "live" && lot.status === "open";
}
