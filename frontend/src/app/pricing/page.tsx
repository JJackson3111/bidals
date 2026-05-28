import Link from "next/link";
import type { Metadata } from "next";

import { MarketingCTA, MarketingFooter, MarketingSection, PageHeader } from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Pricing | BIDALS",
  description:
    "BIDALS pricing packages for Starter, Growth and Partner fundraising teams, supporting auctions, raffles, donations and white-label event needs.",
};

const plans = [
  {
    name: "Starter",
    label: "Focused campaign",
    description: "For teams preparing one polished auction, raffle-style campaign or donation-led fundraising moment.",
    features: [
      "Core auction, raffle or donation setup",
      "Mobile-first supporter experience",
      "Event team admin access",
      "Post-event outcome review",
    ],
    cta: "Talk to us about pricing",
  },
  {
    name: "Growth",
    label: "Multi-channel fundraising",
    description: "For charities and event teams running auctions, raffles and donations through the same campaign.",
    features: [
      "Auctions, raffles and donations supported",
      "Expanded admin governance",
      "Campaign reporting foundations",
      "White-label readiness planning",
    ],
    cta: "Book a demo",
    featured: true,
  },
  {
    name: "Partner",
    label: "Operator model",
    description: "For silent auction companies, agencies and fundraising partners supporting multiple client events.",
    features: [
      "Multi-event operating model",
      "Seller and admin separation",
      "Partner workflow consultation",
      "Custom onboarding plan",
    ],
    cta: "Talk to us about pricing",
  },
];

const principles = [
  "Plans can support auctions, raffles, donations and white-label campaign needs.",
  "Final pricing should reflect event complexity, support needs and operating model.",
  "No exact public prices are committed until commercial packaging is approved.",
];

export default function PricingPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Pricing"
        title="SaaS pricing shaped around fundraising operations."
        description="BIDALS packages are intentionally clear without publishing unapproved prices. Choose a starting point, then scope the event model properly."
      />

      <MarketingSection
        eyebrow="Plans"
        title="Starter, Growth and Partner"
        description="Clean packages for teams launching, scaling or operating premium fundraising campaigns."
      >
        <div className="marketing-pricing-grid">
          {plans.map((plan) => (
            <article className={`marketing-pricing-card ${plan.featured ? "marketing-pricing-card-featured" : ""}`} key={plan.name}>
              <span>{plan.label}</span>
              <h2>{plan.name}</h2>
              <p>{plan.description}</p>
              <strong>Pricing confirmed after scoping</strong>
              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              <Link className="secondary-button marketing-button" href={plan.cta === "Book a demo" ? "/book-demo" : "/contact"}>
                {plan.cta}
              </Link>
            </article>
          ))}
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="Commercial clarity"
        title="Flexible enough to fit the event, clear enough to sell"
        description="The public page sets the package structure while leaving room for responsible commercial scoping."
        tone="muted"
      >
        <ul className="marketing-statement-list">
          {principles.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </MarketingSection>

      <MarketingCTA
        title="Find the right BIDALS package for your campaign."
        description="Talk through your fundraising formats, event scale, white-label needs and support expectations."
        primaryCta={{ href: "/contact", label: "Talk to us about pricing" }}
        secondaryCta={{ href: "/book-demo", label: "Book a demo" }}
      />

      <MarketingFooter />
    </main>
  );
}
