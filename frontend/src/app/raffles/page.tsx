import type { Metadata } from "next";

import { FeatureGrid, MarketingCTA, MarketingFooter, MarketingSection, PageHeader } from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Raffle Fundraising | BIDALS",
  description:
    "BIDALS raffle fundraising positioning for compliant workflow support, transparent records and mobile-first participation.",
};

const raffleFeatures = [
  {
    eyebrow: "Compliance-aware",
    title: "Designed to support compliant fundraising workflows",
    description:
      "BIDALS can provide structure for raffle-style campaigns while organisers remain responsible for the rules, permissions and disclosures that apply to them.",
    items: ["Clear organiser controls", "Participant-facing information", "Reviewable records"],
  },
  {
    eyebrow: "Participation",
    title: "Mobile-first supporter entry",
    description:
      "Supporters should understand what they are entering, how the campaign works and where to go next without friction.",
    items: ["Clean entry journeys", "Campaign context", "Accessible layouts"],
  },
  {
    eyebrow: "Outcomes",
    title: "Transparent draw administration",
    description:
      "Fundraising teams need careful result handling, internal review and clear communications around draw outcomes.",
    items: ["Draw preparation records", "Admin review", "Outcome communication"],
  },
];

const carefulLanguage = [
  "BIDALS should not be described as fully licensed or legally guaranteed.",
  "Organisers should confirm raffle rules, permissions and disclosures for their own jurisdiction.",
  "The platform language should focus on workflow support, records and governance.",
];

export default function RafflesPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Raffles"
        title="Raffle workflows with careful governance language."
        description="BIDALS is designed to support compliant fundraising workflows for raffle-style campaigns without making unverified legal or licensing claims."
      />

      <FeatureGrid title="Support the workflow, respect the rules" features={raffleFeatures} />

      <MarketingSection
        eyebrow="Important positioning"
        title="Clear claims, no shortcuts"
        description="The raffle page is intentionally written to avoid overclaiming on licensing, gambling regulation or legal guarantees."
      >
        <ul className="marketing-statement-list">
          {carefulLanguage.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </MarketingSection>

      <MarketingCTA
        title="Discuss raffle workflows with the right level of care."
        description="Book a demo to explore how BIDALS could support your fundraising model and governance process."
      />

      <MarketingFooter />
    </main>
  );
}
