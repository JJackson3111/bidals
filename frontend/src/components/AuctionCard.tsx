import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { CountdownTimer } from "@/components/CountdownTimer";
import { StatusPill } from "@/components/StatusPill";
import { formatDateTime } from "@/lib/format";
import type { Auction } from "@/lib/types";

export function AuctionCard({ auction }: { auction: Auction }) {
  return (
    <article className="auction-card">
      <div className="card-topline">
        <StatusPill status={auction.status} />
        <CountdownTimer endTime={auction.end_time} />
      </div>
      <Link href={`/auctions/${auction.id}`} className="card-title-link">
        <h2>{auction.title}</h2>
      </Link>
      <p>{auction.description || "No description provided."}</p>
      <dl className="mini-meta">
        <div>
          <dt>Starts</dt>
          <dd>{formatDateTime(auction.start_time)}</dd>
        </div>
        <div>
          <dt>Ends</dt>
          <dd>{formatDateTime(auction.end_time)}</dd>
        </div>
      </dl>
      <Link className="text-link" href={`/auctions/${auction.id}`}>
        Open auction
        <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </article>
  );
}

