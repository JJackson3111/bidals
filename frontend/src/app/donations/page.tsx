import type { Metadata } from "next";
import { BarChart3, HandHeart, HeartHandshake, Smartphone, UsersRound, WalletCards } from "lucide-react";

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
  title: "Donations | BIDALS",
  description:
    "BIDALS donation journeys support simple mobile giving, one-off and monthly options, impact messaging and donor recognition beside fundraising events.",
};

const donationFeatures = [
  {
    eyebrow: "Giving",
    title: "Simple one-off and monthly giving",
    description:
      "Give supporters a direct route to contribute even when they are not bidding or entering a raffle.",
    icon: WalletCards,
    items: ["One-off options", "Monthly option language", "Clear confirmation state"],
  },
  {
    eyebrow: "Impact",
    title: "Impact-led donation moments",
    description:
      "Connect each gift to the campaign story with concise impact prompts and respectful donor recognition.",
    icon: HandHeart,
    items: ["Donation impact", "Campaign context", "Recognition choices"],
  },
  {
    eyebrow: "Mobile",
    title: "Designed for the phone in hand",
    description:
      "Keep the form short, readable and premium so supporters can give during the event without friction.",
    icon: Smartphone,
    items: ["Focused fields", "Fast amount selection", "Accessible form layout"],
  },
  {
    eyebrow: "Teams",
    title: "Donation totals for operators",
    description:
      "Let teams see donation momentum alongside auction and raffle activity as part of the same fundraising picture.",
    icon: BarChart3,
    items: ["Campaign totals", "Impact metrics", "Team reporting foundations"],
  },
  {
    eyebrow: "Donors",
    title: "Recognition without pressure",
    description:
      "Support donor acknowledgement while preserving a simple, respectful path for private giving.",
    icon: UsersRound,
    items: ["Optional recognition", "Supporter-friendly copy", "Event wall readiness"],
  },
  {
    eyebrow: "Governance",
    title: "Careful fundraising claims",
    description:
      "Donation copy stays grounded in workflow support and avoids unverified payment, tax or regulatory promises.",
    icon: HeartHandshake,
    items: ["Clear supporter information", "Admin review", "Export-ready records"],
  },
];

const impactMetrics = [
  { label: "Donation total", value: "GBP 18.6k", detail: "Illustrative event UI" },
  { label: "Monthly gifts", value: "42", detail: "Sample recurring intent" },
  { label: "Impact funded", value: "372 meals", detail: "Example campaign mapping" },
];

const impactRows = [
  { label: "One-off giving", value: "Active", status: "live" as const },
  { label: "Monthly option", value: "Visible", status: "ready" as const },
  { label: "Donor recognition", value: "Optional", status: "review" as const },
];

const donationPrinciples = [
  "Keep giving copy direct, respectful and specific to the campaign.",
  "Use one-off and monthly options without implying tax or payment approvals that are not verified.",
  "Show impact and recognition in a way that supports donors without pressuring them.",
];

export default function DonationsPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Donations"
        title="Simple giving that belongs beside the event."
        description="BIDALS donation journeys help supporters contribute through a premium mobile-first experience that can sit naturally alongside auctions and raffles."
      />

      <MarketingSection
        eyebrow="Donation flow"
        title="Make giving feel immediate, respectful and clear"
        description="A focused donation form can show amounts, one-off or monthly intent, impact and recognition choices without overwhelming the supporter."
      >
        <div className="marketing-showcase-grid">
          <MarketingPhoneMockup variant="donation" />
          <MarketingDashboardPanel
            title="Impact metrics panel"
            metrics={impactMetrics}
            rows={impactRows}
            note="Illustrative UI only. Donation totals and impact numbers are sample interface content, not live fundraising claims."
          />
        </div>
      </MarketingSection>

      <FeatureGrid
        eyebrow="Giving system"
        title="A direct route for supporters who simply want to give"
        description="BIDALS donation pages are positioned as trusted event giving workflows, not generic checkout pages."
        features={donationFeatures}
      />

      <MarketingSection
        eyebrow="Careful communication"
        title="Confident copy, precise promises"
        description="The donation page sets a tone that is premium and specific without drifting into unverified payment, tax or regulatory claims."
        tone="muted"
      >
        <ul className="marketing-statement-list">
          {donationPrinciples.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </MarketingSection>

      <TrustSection
        title="Donation trust sits in clarity and control"
        description="Supporters should understand what they are giving to. Teams should understand how donation momentum contributes to the event."
        items={[
          "One-off and monthly donation options presented clearly",
          "Impact metrics and donor recognition shown as campaign UI",
          "Admin review and export-ready records for operators",
          "No unverified tax, payment or regulatory claims made",
        ]}
      />

      <MarketingCTA
        title="Plan giving journeys around your event goals."
        description="Book a demo to explore how donations could sit alongside your auction, raffle and supporter recognition strategy."
      />

      <MarketingFooter />
    </main>
  );
}
