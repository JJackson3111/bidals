import type { Metadata } from "next";

import {
  FeatureGrid,
  MarketingCTA,
  MarketingFooter,
  MarketingHero,
  MarketingSection,
  TrustSection,
} from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "BIDALS | Secure Digital Fundraising Platform",
  description:
    "BIDALS powers auctions, raffles and charitable giving through a secure mobile-first fundraising experience.",
};

const platformFeatures = [
  {
    eyebrow: "Auctions",
    title: "Run serious fundraising auctions",
    description:
      "Build event pages, publish lots, guide mobile bidding and keep outcomes grounded in server-owned records.",
    items: ["Live and silent auction workflows", "Lot management", "Winner and fulfillment paths"],
  },
  {
    eyebrow: "Raffles",
    title: "Support governed raffle campaigns",
    description:
      "Shape raffle journeys around clear organiser controls, transparent draw records and compliance-aware operations.",
    items: ["Entry workflow foundations", "Draw preparation records", "Clear participant communication"],
  },
  {
    eyebrow: "Giving",
    title: "Keep donations close to the event",
    description:
      "Give supporters a straightforward mobile-first way to contribute alongside bids, entries and campaign updates.",
    items: ["Supporter-friendly flows", "Campaign totals", "Team-ready reporting"],
  },
];

const workflowSteps = [
  {
    title: "Plan the campaign",
    description: "Set the event goal, fundraising channels, audience and operating rules before supporters arrive.",
  },
  {
    title: "Launch with confidence",
    description: "Publish a polished mobile experience with clear calls to bid, enter, donate or enquire.",
  },
  {
    title: "Govern the outcome",
    description: "Use admin controls, audit trails and transparent records to close activity cleanly.",
  },
];

export default function HomePage() {
  return (
    <main className="marketing-page">
      <MarketingHero
        eyebrow="BIDALS fundraising platform"
        title="Secure digital fundraising for auctions, raffles and giving."
        description="BIDALS is a digital fundraising platform powering auctions, raffles and charitable giving through a secure mobile-first experience."
        highlights={[
          "Built for charities, churches, schools and fundraising teams",
          "Server-authoritative auction records",
          "Prepared for www, app and API domain separation",
        ]}
      />

      <FeatureGrid
        eyebrow="Platform"
        title="One product-led fundraising stack"
        description="BIDALS gives teams a clean route from campaign setup to supporter participation and governed outcomes."
        features={platformFeatures}
      />

      <MarketingSection
        eyebrow="Workflow"
        title="Designed for the way fundraising teams actually work"
        description="A calm operating model for campaigns that need public momentum and private control."
      >
        <div className="marketing-steps" id="how-it-works">
          {workflowSteps.map((step, index) => (
            <article className="marketing-step" key={step.title}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </article>
          ))}
        </div>
      </MarketingSection>

      <TrustSection
        title="Built around trust, not theatre"
        description="The marketing site now has room to tell the platform story without changing the product app underneath it."
        items={[
          "Mobile-first journeys for supporters",
          "Admin governance for fundraising teams",
          "Audit-friendly records for sensitive outcomes",
          "Clear separation for future www.bidals.co.uk and app.bidals.co.uk routing",
        ]}
      />

      <MarketingCTA
        title="Show your team what BIDALS can become for your next campaign."
        description="Start with a focused demo conversation, then explore the feature set that matters for your event model."
      />

      <MarketingFooter />
    </main>
  );
}
