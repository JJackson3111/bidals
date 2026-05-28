import type { Metadata } from "next";
import { Gavel, HeartHandshake, ShieldCheck, Ticket } from "lucide-react";

import {
  FeatureGrid,
  MarketingCTA,
  MarketingDashboardPanel,
  MarketingFooter,
  MarketingHero,
  MarketingMetricStrip,
  MarketingSection,
  TrustSection,
} from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "BIDALS | Modern Fundraising Operating System",
  description:
    "BIDALS powers auctions, raffles and charitable giving through a secure mobile-first fundraising platform for premium event teams.",
};

const platformFeatures = [
  {
    eyebrow: "Auctions",
    title: "Auction momentum, governed properly",
    description:
      "Create live and silent auction moments with mobile bidding, watchlists, controlled close-down and backend-owned bid records.",
    icon: Gavel,
    items: ["Live lot visibility", "Server-authoritative bidding", "Winner and fulfillment paths"],
  },
  {
    eyebrow: "Raffles",
    title: "Raffle workflows with careful controls",
    description:
      "Support raffle-style fundraising with clear participant flows, organiser review and language designed around compliant workflows.",
    icon: Ticket,
    items: ["Ticket purchase flow", "Hidden prize reveal support", "Reviewable draw records"],
  },
  {
    eyebrow: "Donations",
    title: "Giving that belongs in the event",
    description:
      "Let supporters give in the same premium mobile experience with simple one-off or monthly donation paths.",
    icon: HeartHandshake,
    items: ["Donation forms", "Impact messaging", "Donor recognition options"],
  },
];

const clarityMetrics = [
  { label: "Event health", value: "Live", detail: "Bids, entries and gifts in one view" },
  { label: "Activity", value: "2.4k", detail: "Illustrative supporter actions" },
  { label: "Progress", value: "86%", detail: "Sample campaign target" },
];

const clarityRows = [
  { label: "Bidder activity", value: "Rising", status: "live" as const },
  { label: "Donation total", value: "On track", status: "ready" as const },
  { label: "Outcome review", value: "Governed", status: "review" as const },
];

const operatingSignals = [
  "A mobile-first supporter layer for bids, raffle entries and donations.",
  "A serious admin layer for audit trails, transparent outcomes and team governance.",
  "White-label readiness so charity and event branding can lead the campaign.",
];

export default function HomePage() {
  return (
    <main className="marketing-page">
      <MarketingHero
        eyebrow="BIDALS fundraising platform"
        title="Power every bid."
        description="BIDALS is the modern fundraising operating system for auctions, raffles, donations, event teams and charity-led campaigns."
        highlights={[
          "Mobile-first fundraising journeys",
          "Server-authoritative auction records",
          "Built for premium events and governed outcomes",
        ]}
        primaryCta={{ href: "/book-demo", label: "Book a demo" }}
        secondaryCta={{ href: "/features", label: "Explore the platform" }}
      />

      <FeatureGrid
        eyebrow="Fundraising OS"
        title="One platform for every fundraising moment"
        description="BIDALS brings public participation and private control into one calm operating layer."
        features={platformFeatures}
      />

      <MarketingSection
        eyebrow="Operations"
        title="Manage with clarity."
        description="Event teams need more than a beautiful public page. They need the confidence to see what is happening, what needs attention and what record will stand behind the outcome."
      >
        <div className="marketing-showcase-grid">
          <div className="marketing-copy-stack">
            <span className="marketing-inline-icon">
              <ShieldCheck size={19} aria-hidden="true" />
              Operational control
            </span>
            <ul className="marketing-statement-list">
              {operatingSignals.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <MarketingDashboardPanel
            title="Campaign command centre"
            metrics={clarityMetrics}
            rows={clarityRows}
            note="Illustrative dashboard UI showing event health, bidder activity, donation totals and outcome review."
          />
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="Signals"
        title="Premium outside, serious underneath"
        description="BIDALS is designed to feel refined for supporters while staying precise for the people accountable for the event."
        tone="muted"
      >
        <MarketingMetricStrip
          metrics={[
            { label: "Supporter experience", value: "Mobile first", detail: "Auction, raffle and donation flows" },
            { label: "Admin confidence", value: "Governed", detail: "Roles, records and review paths" },
            { label: "Brand fit", value: "White-label ready", detail: "Charity and event branding supported" },
          ]}
        />
      </MarketingSection>

      <TrustSection
        title="Trusted fundraising is designed into the operation"
        description="BIDALS speaks to the parts of fundraising that matter after the room gets busy: records, permissions, outcomes and transparent administration."
        items={[
          "Audit-friendly records for sensitive fundraising outcomes",
          "Backend-controlled bidding and clear accepted-bid state",
          "Admin governance for sellers, event teams and trusted operators",
          "Clear data ownership language for future customer conversations",
        ]}
      />

      <MarketingCTA
        title="Ready to modernise your next fundraiser?"
        description="Bring auctions, raffles and giving into a mobile-first experience that feels premium to supporters and serious to operators."
      />

      <MarketingFooter />
    </main>
  );
}
