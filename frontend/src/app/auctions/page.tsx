import Link from "next/link";
import type { Metadata } from "next";

import {
  FeatureGrid,
  MarketingCTA,
  MarketingFooter,
  MarketingSection,
  PageHeader,
  TrustSection,
} from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Auction Fundraising | BIDALS",
  description:
    "BIDALS auction fundraising pages for secure mobile bidding, lot management, transparent outcomes and admin governance.",
};

const auctionFeatures = [
  {
    eyebrow: "Lots",
    title: "Present lots with clarity",
    description:
      "Give supporters enough context to browse, compare and bid without making the public experience feel cluttered.",
    items: ["Images and descriptions", "Current bid visibility", "Mobile browsing"],
  },
  {
    eyebrow: "Bids",
    title: "Keep bidding server-authoritative",
    description:
      "Auction bidding should rely on backend validation, not client-side assumptions or fragile public state.",
    items: ["Bid increments", "Accepted bid records", "Outbid feedback"],
  },
  {
    eyebrow: "Close",
    title: "Close events with confidence",
    description:
      "After the final bid, teams need governed results, winner review and fulfillment workflows they can trust.",
    items: ["Winner records", "Audit trails", "Fulfillment support"],
  },
];

const eventTypes = [
  "Charity galas and annual appeals",
  "Church and school fundraising events",
  "Silent auction companies supporting client campaigns",
  "Hybrid events with in-room and remote supporters",
];

export default function AuctionsMarketingPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Auctions"
        title="Auction fundraising built for mobile supporters and serious operators."
        description="BIDALS gives auction teams a secure, product-led foundation for lot browsing, live bidding, admin oversight and transparent close-down."
      />

      <FeatureGrid title="A cleaner way to run fundraising auctions" features={auctionFeatures} />

      <MarketingSection
        eyebrow="Use cases"
        title="Built for professional fundraising events"
        description="The auction page gives future customers a focused route into BIDALS without replacing the existing product browse experience."
      >
        <div className="marketing-two-column">
          <ul className="marketing-statement-list">
            {eventTypes.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <div className="marketing-note-panel">
            <h3>Preview the supporter experience</h3>
            <p>
              A live browsing preview remains available for demos and internal review while this page stays focused on auction buyers.
            </p>
            <Link href="/browse">Open browsing preview</Link>
          </div>
        </div>
      </MarketingSection>

      <TrustSection
        title="Auction trust is operational"
        description="BIDALS is positioned around the records and controls that fundraising teams need once bids start moving."
        items={[
          "Server-authoritative bid acceptance",
          "Admin review and governance",
          "Transparent winner outcomes",
          "Fulfillment workflow foundations",
        ]}
      />

      <MarketingCTA
        title="See how a BIDALS auction could fit your next event."
        description="Book a demo for the auction workflow, or explore the full platform feature set."
      />

      <MarketingFooter />
    </main>
  );
}
