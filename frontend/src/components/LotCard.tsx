import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { StatusPill } from "@/components/StatusPill";
import { formatMoney, getLotPrimaryImageUrl } from "@/lib/format";
import type { Lot } from "@/lib/types";

export function LotCard({ lot }: { lot: Lot }) {
  const imageUrl = getLotPrimaryImageUrl(lot);

  return (
    <article className="lot-card">
      {imageUrl ? (
        <div
          aria-label={lot.uploaded_images?.[0]?.alt_text || lot.title}
          className="lot-card-image"
          role="img"
          style={{ backgroundImage: `url("${imageUrl}")` }}
        />
      ) : (
        <div className="lot-image-placeholder" aria-hidden="true">
          <span>{lot.title.slice(0, 1).toUpperCase()}</span>
        </div>
      )}
      <div className="lot-card-body">
        <div className="card-topline">
          <StatusPill status={lot.status} />
          <span>{formatMoney(lot.current_price)}</span>
        </div>
        <Link href={`/lots/${lot.id}`} className="card-title-link">
          <h3>{lot.title}</h3>
        </Link>
        <p>{lot.description || lot.auction_title}</p>
        <Link className="text-link" href={`/lots/${lot.id}`}>
          View lot
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </div>
    </article>
  );
}
