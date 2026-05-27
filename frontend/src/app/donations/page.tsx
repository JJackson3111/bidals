import type { Metadata } from "next";

import { FeatureGrid, MarketingCTA, MarketingFooter, MarketingSection, PageHeader } from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Donations | BIDALS",
  description:
    "BIDALS donation journey positioning for mobile-first fundraising campaigns and compliant workflow support.",
};

const donationFeatures = [
  {
    eyebrow: "Giving",
    title: "Donation journeys beside event activity",
    description:
      "Supporters who do not want to bid or enter a raffle should still have a clear route to contribute to the campaign.",
    items: ["Mobile-first giving pages", "Campaign context", "Clear next steps"],
  },
  {
    eyebrow: "Campaigns",
    title: "Totals that help teams understand momentum",
    description:
      "Donation activity can sit alongside auctions and raffles so teams can communicate progress with confidence.",
    items: ["Fundraising totals", "Campaign milestones", "Team reporting foundations"],
  },
  {
    eyebrow: "Governance",
    title: "Designed to support compliant fundraising workflows",
    description:
      "BIDALS donation messaging should stay grounded in workflow support and organiser governance rather than unverified payment or tax claims.",
    items: ["Clear supporter information", "Admin review", "Export-ready records"],
  },
];

const donationPrinciples = [
  "Keep donation copy direct, respectful and specific to the campaign.",
  "Avoid implying tax, payment or regulatory approvals that have not been implemented or verified.",
  "Make donation workflows feel part of the same trusted BIDALS experience.",
];

export default function DonationsPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Donations"
        title="Charitable giving that fits naturally around the campaign."
        description="BIDALS donation pages are positioned as mobile-first fundraising workflows that can sit alongside auctions and raffles without diluting the supporter experience."
      />

      <FeatureGrid title="A direct route for supporters who simply want to give" features={donationFeatures} />

      <MarketingSection
        eyebrow="Careful communication"
        title="Fundraising copy should be trustworthy and precise"
        description="The donation page sets a tone that is confident without drifting into unverified promises."
      >
        <ul className="marketing-statement-list">
          {donationPrinciples.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </MarketingSection>

      <MarketingCTA
        title="Plan giving journeys around your event goals."
        description="Book a demo to discuss how donations could sit alongside the rest of your BIDALS campaign."
      />

      <MarketingFooter />
    </main>
  );
}
