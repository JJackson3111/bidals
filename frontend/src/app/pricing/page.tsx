import type { Metadata } from "next";

import { MarketingCTA, MarketingFooter, MarketingSection, PageHeader } from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Pricing | BIDALS",
  description:
    "Indicative BIDALS pricing structure for fundraising teams, campaign operators and partner organisations.",
};

const plans = [
  {
    name: "Launch",
    label: "Single campaign setup",
    description: "For teams preparing a focused auction, raffle-style campaign or donation-led event.",
    features: ["Campaign setup support", "Core public fundraising pages", "Admin access for the event team", "Post-event outcome review"],
  },
  {
    name: "Growth",
    label: "Multi-channel fundraising",
    description: "For organisations running several fundraising formats or repeat campaigns through the year.",
    features: ["Auction, raffle and donation workflows", "Expanded admin governance", "Supporter journey review", "Campaign reporting foundations"],
  },
  {
    name: "Partner",
    label: "Operator and agency model",
    description: "For silent auction companies and fundraising partners supporting multiple client events.",
    features: ["Multi-event operating model", "Seller and admin separation", "Workflow consultation", "Custom onboarding plan"],
  },
];

const principles = [
  "Pricing should reflect event complexity, fundraising model and support needs.",
  "No exact public prices are committed here until the commercial packaging is final.",
  "BIDALS should stay transparent about what is included before a customer launches.",
];

export default function PricingPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Pricing"
        title="SaaS-style pricing shaped around real fundraising operations."
        description="BIDALS pricing is structured as clear packages for launch, growth and partner use cases. Final pricing can be confirmed during onboarding rather than guessed too early."
      />

      <MarketingSection
        eyebrow="Plans"
        title="Indicative packaging"
        description="These placeholders create a proper sales-page structure without committing to final prices before they are approved."
      >
        <div className="marketing-pricing-grid">
          {plans.map((plan) => (
            <article className="marketing-pricing-card" key={plan.name}>
              <span>{plan.label}</span>
              <h2>{plan.name}</h2>
              <p>{plan.description}</p>
              <strong>Pricing confirmed after scoping</strong>
              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="Principles"
        title="Clear enough to sell, careful enough to evolve"
        description="The public pricing page should help buyers understand fit while leaving room for final commercial decisions."
      >
        <ul className="marketing-statement-list">
          {principles.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </MarketingSection>

      <MarketingCTA
        title="Find the right BIDALS package for your campaign."
        description="A short demo call can map your event model to the most sensible launch path."
      />

      <MarketingFooter />
    </main>
  );
}
