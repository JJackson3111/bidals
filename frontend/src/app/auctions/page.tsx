import Link from "next/link";
import type { Metadata } from "next";
import { Bell, FileCheck2, Gavel, History, ShieldCheck, Trophy } from "lucide-react";

import {
  FeatureGrid,
  MarketingCTA,
  MarketingDashboardPanel,
  MarketingFooter,
  MarketingPhoneMockup,
  MarketingSection,
  PageHeader,
  TrustSection,
} from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Auction Fundraising | BIDALS",
  description:
    "BIDALS auction fundraising supports secure mobile bidding, live lot momentum, controlled closing, watchlists, notifications and audit trails.",
};

const auctionFeatures = [
  {
    eyebrow: "Momentum",
    title: "Bidder confidence in motion",
    description:
      "Make every lot feel live, legible and worth returning to with quick bid actions, status cues and mobile-first browsing.",
    icon: Gavel,
    items: ["Current bid visibility", "Quick bid buttons", "Outbid feedback"],
  },
  {
    eyebrow: "Control",
    title: "Seller control at close",
    description:
      "Support closing rules, review paths and fulfillment handoff so the auction does not lose discipline at the most important moment.",
    icon: Trophy,
    items: ["Controlled closing", "Extension support", "Winner review"],
  },
  {
    eyebrow: "Records",
    title: "Audit trails by design",
    description:
      "Keep accepted bids, bidder state and outcome decisions grounded in backend-owned records that operators can review.",
    icon: History,
    items: ["Bid history", "Accepted bid records", "Transparent outcomes"],
  },
  {
    eyebrow: "Engagement",
    title: "Watchlists and notifications",
    description:
      "Let supporters track the lots they care about and return when momentum changes without making the experience noisy.",
    icon: Bell,
    items: ["Watchlist state", "Activity cues", "Return-to-bid moments"],
  },
  {
    eyebrow: "Governance",
    title: "Server-authoritative bidding",
    description:
      "BIDALS positioning is clear: the backend controls bid acceptance and the public UI reflects the trusted record.",
    icon: ShieldCheck,
    items: ["Backend validation", "Accepted/rejected bid state", "Consistent winner logic"],
  },
  {
    eyebrow: "Close-down",
    title: "Fulfillment-ready outcomes",
    description:
      "Move from final bids to clear winner records, seller review and event-team follow-up without guesswork.",
    icon: FileCheck2,
    items: ["Winner records", "Payment handoff planning", "Post-event review"],
  },
];

const auctionMetrics = [
  { label: "Active bidders", value: "128", detail: "Illustrative live event UI" },
  { label: "Watched lots", value: "42", detail: "Sample dashboard metric" },
  { label: "Close status", value: "Controlled", detail: "Operator review ready" },
];

const auctionRows = [
  { label: "Server bid validation", value: "Authoritative", status: "live" as const },
  { label: "Anti-sniping extension", value: "Configured", status: "ready" as const },
  { label: "Winner audit trail", value: "Reviewable", status: "review" as const },
];

export default function AuctionsMarketingPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Auctions"
        title="Auction momentum with bidder confidence and seller control."
        description="BIDALS gives fundraising auction teams a mobile-first experience for supporters and a technically serious operating layer for bids, close-down and outcomes."
      />

      <MarketingSection
        eyebrow="Live lot experience"
        title="Make the auction feel alive without losing control"
        description="Supporters see the lot, current bid, quick bid action and bid history. Operators keep the accepted record on the server."
      >
        <div className="marketing-showcase-grid">
          <div className="marketing-copy-stack">
            <ul className="marketing-statement-list">
              <li>Current bid and quick bid actions are presented as clear mobile UI.</li>
              <li>Watchlists, notifications and bid history help supporters stay engaged.</li>
              <li>Controlled closing, extensions and outcome review support serious event operations.</li>
            </ul>
            <div className="marketing-note-panel">
              <h3>Preview the product browse route</h3>
              <p>The existing product browsing experience remains available separately from this sales page.</p>
              <Link href="/browse">Open browsing preview</Link>
            </div>
          </div>
          <MarketingPhoneMockup variant="auction" />
        </div>
      </MarketingSection>

      <FeatureGrid
        eyebrow="Auction operating system"
        title="Built for public momentum and private certainty"
        description="Every auction interaction should feel simple to the bidder and precise to the event team."
        features={auctionFeatures}
      />

      <MarketingSection
        eyebrow="Trust panel"
        title="Server-authoritative bidding is the centre of auction trust"
        description="Auction integrity depends on the backend record, not client-side optimism."
        tone="muted"
      >
        <MarketingDashboardPanel
          title="Bid governance panel"
          metrics={auctionMetrics}
          rows={auctionRows}
          note="Illustrative UI only. Values show how auction health and governance can be communicated without changing bidding engine logic."
        />
      </MarketingSection>

      <TrustSection
        title="Auction trust is operational"
        description="BIDALS is positioned around the controls fundraising teams need once bids start moving."
        items={[
          "Server-authoritative bid acceptance and rejected-bid handling",
          "Controlled closing, extension rules and winner review",
          "Watchlists, notifications and bid history for bidder confidence",
          "Audit trails for admins, sellers and trusted event operators",
        ]}
      />

      <MarketingCTA
        title="Run your next auction like a serious fundraising operation."
        description="Book a demo to walk through live lots, mobile bidding, close-down, audit trails and fulfillment planning."
      />

      <MarketingFooter />
    </main>
  );
}
