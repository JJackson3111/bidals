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
  title: "Features | BIDALS",
  description:
    "Explore BIDALS features for auctions, raffles, donations, supporter journeys and admin governance.",
};

const featureGroups = [
  {
    eyebrow: "Campaigns",
    title: "Flexible fundraising channels",
    description: "Support auctions, raffle-style workflows and donations from one product-led experience.",
    items: ["Auction pages", "Raffle workflow support", "Donation journeys"],
  },
  {
    eyebrow: "Supporters",
    title: "Mobile-first participation",
    description: "Give guests and remote supporters a fast, clear route to take part from their own device.",
    items: ["Responsive flows", "Clear calls to action", "Event-friendly browsing"],
  },
  {
    eyebrow: "Operations",
    title: "Seller and admin controls",
    description: "Keep setup, monitoring and close-down work inside governed dashboards for trusted teams.",
    items: ["Dashboard views", "Role-aware access", "Fulfillment workflow foundations"],
  },
  {
    eyebrow: "Records",
    title: "Outcome visibility",
    description: "Keep fundraising records structured so winners, bids, entries and gifts can be reviewed clearly.",
    items: ["Audit trails", "Transparent outcomes", "Admin review paths"],
  },
  {
    eyebrow: "Brand",
    title: "Premium public experience",
    description: "Present serious fundraising campaigns with a clean BIDALS visual system and confident copy.",
    items: ["Off-black and off-white palette", "Acid green brand accents", "SaaS-grade spacing"],
  },
  {
    eyebrow: "Scale",
    title: "Ready for domain separation",
    description: "The route structure supports future marketing, app and API subdomains without page-builder lock-in.",
    items: ["www.bidals.co.uk", "app.bidals.co.uk", "api.bidals.co.uk"],
  },
];

const operatingModel = [
  "Create campaign structure without mixing product admin routes into the sales site.",
  "Give future buyers a dedicated place to understand auctions, raffles, donations, pricing and security.",
  "Keep the app routes available for bidding, dashboards, account work and operational workflows.",
];

export default function FeaturesPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Features"
        title="A fundraising platform built around participation and control."
        description="BIDALS brings the public supporter journey and private fundraising operation into one secure, mobile-first product surface."
      />

      <FeatureGrid title="What BIDALS is designed to support" features={featureGroups} />

      <MarketingSection
        eyebrow="Product structure"
        title="Marketing pages for buyers, app routes for operators"
        description="This structure gives BIDALS a proper sales website while keeping the existing product app intact."
      >
        <ul className="marketing-statement-list">
          {operatingModel.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </MarketingSection>

      <TrustSection
        title="Serious enough for sensitive fundraising"
        description="The platform story is intentionally grounded in governance, records and supporter experience."
        items={[
          "No page-builder dependency",
          "No changes to bidding or authentication logic",
          "Clear content paths for future customers",
          "Consistent BIDALS brand styling",
        ]}
      />

      <MarketingCTA
        title="Explore the parts of BIDALS that matter to your campaign."
        description="Book a demo for a guided walkthrough, or keep reading through the product areas."
      />

      <MarketingFooter />
    </main>
  );
}
