import type { Metadata } from "next";
import {
  Activity,
  BarChart3,
  Bell,
  Gavel,
  History,
  LockKeyhole,
  Settings2,
  Smartphone,
  Ticket,
  WalletCards,
} from "lucide-react";

import {
  FeatureGrid,
  MarketingCTA,
  MarketingFooter,
  MarketingMetricStrip,
  MarketingSection,
  PageHeader,
  TrustSection,
} from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Features | BIDALS Fundraising Platform",
  description:
    "Explore BIDALS features for live auctions, raffles, donations, watchlists, bid history, reporting, integrations and secure admin governance.",
};

const featureGroups = [
  {
    eyebrow: "Auctions",
    title: "Live auction workflows",
    description: "Publish lots, guide mobile bidding and keep accepted bids grounded in server-owned records.",
    icon: Gavel,
    items: ["Live and silent lots", "Quick bid actions", "Controlled close-down"],
  },
  {
    eyebrow: "Raffles",
    title: "Raffle workflow support",
    description: "Support careful ticket journeys, prize reveal moments and organiser review without overclaiming legal coverage.",
    icon: Ticket,
    items: ["Ticket purchase flow", "Draw preparation", "Outcome records"],
  },
  {
    eyebrow: "Giving",
    title: "Donations and impact",
    description: "Give supporters a clear route to one-off or monthly contributions alongside the event experience.",
    icon: WalletCards,
    items: ["Mobile donation forms", "Impact messaging", "Recognition options"],
  },
  {
    eyebrow: "Supporters",
    title: "Watchlists and notifications",
    description: "Help bidders track lots and return at the right moment through clean mobile-first participation cues.",
    icon: Bell,
    items: ["Lot watchlists", "Outbid feedback", "Event reminders"],
  },
  {
    eyebrow: "Records",
    title: "Bid history and outcomes",
    description: "Make activity reviewable with structured records for bids, winners, fulfillment and supporter journeys.",
    icon: History,
    items: ["Accepted bid history", "Winner review", "Transparent statuses"],
  },
  {
    eyebrow: "Reports",
    title: "Operational reporting",
    description: "Give teams the information they need to understand event health, fundraising totals and follow-up work.",
    icon: BarChart3,
    items: ["Campaign totals", "Bidder activity", "Donation progress"],
  },
  {
    eyebrow: "Experience",
    title: "Mobile-first interface",
    description: "Keep bidding, raffle entry and donation flows clear on the devices supporters already have in hand.",
    icon: Smartphone,
    items: ["Responsive layouts", "Fast supporter actions", "Premium event feel"],
  },
  {
    eyebrow: "Trust",
    title: "Secure platform posture",
    description: "Position the platform around backend control, audit trails, roles and data ownership conversations.",
    icon: LockKeyhole,
    items: ["Server-authoritative bidding", "Admin permissions", "Audit-friendly records"],
  },
  {
    eyebrow: "Operations",
    title: "Integrations and readiness",
    description: "Leave room for payment, CRM and event partner integrations to be scoped carefully as the platform grows.",
    icon: Settings2,
    items: ["Integration planning", "White-label needs", "Event operator workflows"],
  },
];

const ecosystemSignals = [
  { label: "Public flows", value: "Unified", detail: "Auctions, raffles and donations" },
  { label: "Private controls", value: "Governed", detail: "Admin, seller and review paths" },
  { label: "Brand model", value: "Flexible", detail: "White-label campaign readiness" },
  { label: "Data posture", value: "Clear", detail: "Ownership and export conversations" },
];

export default function FeaturesPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Features"
        title="The full BIDALS fundraising ecosystem."
        description="BIDALS combines auction momentum, raffle workflows, donation journeys and operational governance in one secure mobile-first platform."
      />

      <FeatureGrid
        eyebrow="Platform capabilities"
        title="Everything a premium fundraising operation expects"
        description="Concise public flows for supporters, precise private controls for the teams accountable for the outcome."
        features={featureGroups}
      />

      <MarketingSection
        eyebrow="Operating model"
        title="Built as a fundraising operating system"
        description="BIDALS keeps the public sales story, supporter experience and product administration aligned without blurring their responsibilities."
        tone="muted"
      >
        <div className="marketing-showcase-grid">
          <MarketingMetricStrip metrics={ecosystemSignals} />
          <div className="marketing-note-panel">
            <span className="marketing-inline-icon">
              <Activity size={19} aria-hidden="true" />
              Product-led structure
            </span>
            <h3>One serious system, multiple fundraising formats</h3>
            <p>
              The platform can support auctions, raffles, donations, reports, mobile participation and white-label event needs while keeping governance language precise.
            </p>
          </div>
        </div>
      </MarketingSection>

      <TrustSection
        title="Serious enough for sensitive fundraising"
        description="BIDALS is intentionally positioned around governance, records and technical clarity, not generic charity-site promises."
        items={[
          "Server-authoritative bidding and accepted-bid state",
          "Audit trails, bid history and outcome review paths",
          "Role-aware admin access for event and seller teams",
          "Careful integration and payment readiness language",
        ]}
      />

      <MarketingCTA
        title="See how the BIDALS ecosystem fits your campaign."
        description="Book a demo for a guided walkthrough across auctions, raffles, donations, governance and white-label needs."
      />

      <MarketingFooter />
    </main>
  );
}
