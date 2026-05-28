import type { Metadata } from "next";
import { FileCheck2, LockKeyhole, ShieldCheck, Ticket, Trophy } from "lucide-react";

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
  title: "Raffle Fundraising | BIDALS",
  description:
    "BIDALS is designed to support compliant raffle fundraising workflows with careful language, transparent tracking and governed winner draw preparation.",
};

const raffleFeatures = [
  {
    eyebrow: "Careful workflows",
    title: "Designed to support compliant fundraising workflows",
    description:
      "BIDALS can structure raffle-style participation while organisers remain responsible for rules, permissions and disclosures.",
    icon: ShieldCheck,
    items: ["Organiser controls", "Participant information", "Reviewable records"],
  },
  {
    eyebrow: "Tickets",
    title: "Mobile ticket purchase flow",
    description:
      "Supporters can understand the campaign, select entries and see clear next steps in a focused mobile journey.",
    icon: Ticket,
    items: ["Ticket selection", "Campaign context", "Clear purchase state"],
  },
  {
    eyebrow: "Reveal",
    title: "Hidden prize reveal moments",
    description:
      "Premium events can preserve mystery and anticipation while keeping the organiser experience controlled.",
    icon: LockKeyhole,
    items: ["Prize reveal state", "Event-led messaging", "Brand-safe presentation"],
  },
  {
    eyebrow: "Tracking",
    title: "Raffle tracking for event teams",
    description:
      "Give operators an illustrative view of sell-through, raffle income and campaign status without implying guaranteed outcomes.",
    icon: FileCheck2,
    items: ["Ticket sell-through", "Income tracking", "Participant records"],
  },
  {
    eyebrow: "Draw",
    title: "Winner draw confidence",
    description:
      "Position draw handling around governance, review and communication rather than unsupported legal claims.",
    icon: Trophy,
    items: ["Draw preparation", "Admin review", "Outcome communication"],
  },
];

const raffleMetrics = [
  { label: "Ticket sell-through", value: "68%", detail: "Illustrative UI only" },
  { label: "Raffle income", value: "GBP 7.4k", detail: "Sample event metric" },
  { label: "Draw status", value: "Review queued", detail: "Governance view" },
];

const raffleRows = [
  { label: "Prize reveal", value: "Locked", status: "ready" as const },
  { label: "Participant records", value: "Reviewable", status: "live" as const },
  { label: "Winner draw", value: "Prepared", status: "review" as const },
];

const carefulLanguage = [
  "BIDALS is described as designed to support compliant fundraising workflows.",
  "Organisers remain responsible for the rules, permissions and disclosures that apply to their raffle.",
  "The platform language focuses on workflow support, records, review and governance.",
];

export default function RafflesPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Raffles"
        title="Raffle fundraising with careful workflows and confident outcomes."
        description="BIDALS supports raffle-style campaigns through mobile ticket journeys, tracking and draw preparation language that stays precise and compliance-aware."
      />

      <MarketingSection
        eyebrow="Supporter flow"
        title="Ticket entry should feel simple, governed and premium"
        description="The public raffle experience can create anticipation while the operating layer keeps records and draw preparation clear."
      >
        <div className="marketing-showcase-grid">
          <MarketingPhoneMockup variant="raffle" />
          <MarketingDashboardPanel
            title="Raffle tracking panel"
            metrics={raffleMetrics}
            rows={raffleRows}
            note="Illustrative UI only. These figures demonstrate dashboard presentation and are not live platform performance claims."
          />
        </div>
      </MarketingSection>

      <FeatureGrid
        eyebrow="Raffle system"
        title="Support the workflow, respect the rules"
        description="BIDALS avoids claiming licensing or legal guarantees and instead focuses on practical campaign structure."
        features={raffleFeatures}
      />

      <MarketingSection
        eyebrow="Important positioning"
        title="Clear claims, no shortcuts"
        description="Raffle fundraising can be sensitive. BIDALS copy should stay exact, useful and responsible."
        tone="muted"
      >
        <ul className="marketing-statement-list">
          {carefulLanguage.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </MarketingSection>

      <TrustSection
        title="Designed for raffle governance conversations"
        description="The platform story centres on participant clarity, organiser responsibility and reviewable records."
        items={[
          "Designed to support compliant fundraising workflows",
          "No licensing, legal or guaranteed-compliance claims made",
          "Ticket tracking and draw preparation records",
          "Winner communication and admin review language",
        ]}
      />

      <MarketingCTA
        title="Discuss raffle workflows with the right level of care."
        description="Book a demo to explore how BIDALS could support your raffle model, disclosures and event operations."
      />

      <MarketingFooter />
    </main>
  );
}
