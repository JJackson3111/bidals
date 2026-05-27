import type { Metadata } from "next";

import { FeatureGrid, MarketingCTA, MarketingFooter, PageHeader, TrustSection } from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Security | BIDALS",
  description:
    "How BIDALS communicates server-authoritative bidding, audit trails, admin governance and transparent fundraising outcomes.",
};

const securityFeatures = [
  {
    eyebrow: "Bidding",
    title: "Server-authoritative bidding",
    description:
      "BIDALS keeps bid acceptance and auction truth on the server side so the public interface is not the source of record.",
    items: ["Backend-owned validation", "Controlled bid acceptance", "Consistent bidder state"],
  },
  {
    eyebrow: "Audit",
    title: "Audit trails",
    description:
      "Important actions should leave a reviewable record for sellers, admins and trusted operational users.",
    items: ["Timestamped records", "Outcome review", "Operational traceability"],
  },
  {
    eyebrow: "Governance",
    title: "Admin governance",
    description:
      "Role-aware dashboards help teams separate public participation from internal campaign control.",
    items: ["Admin views", "Seller workflows", "Controlled close-down"],
  },
  {
    eyebrow: "Outcomes",
    title: "Transparent results",
    description:
      "Fundraising outcomes need to be explainable, especially when supporters, bidders and organisers are all involved.",
    items: ["Winner visibility", "Fulfillment workflow support", "Clear status changes"],
  },
  {
    eyebrow: "Foundation",
    title: "Secure platform foundations",
    description:
      "The marketing site can explain the platform security posture without changing existing authentication or API logic.",
    items: ["Secure account model", "API-backed product routes", "Operational separation"],
  },
];

export default function SecurityPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Security"
        title="Trustworthy fundraising needs more than a polished front end."
        description="BIDALS is positioned around secure participation, governed administration and transparent outcomes for campaigns where records matter."
      />

      <FeatureGrid title="Security themes buyers need to understand" features={securityFeatures} />

      <TrustSection
        eyebrow="Platform posture"
        title="Clear boundaries between public pages and product logic"
        description="These marketing pages describe security and governance without altering the systems that already power bidding, accounts and dashboards."
        items={[
          "Bidding engine untouched",
          "Authentication flow untouched",
          "Backend API untouched",
          "Dashboard behavior untouched",
        ]}
      />

      <MarketingCTA
        title="Talk through security expectations before launch."
        description="BIDALS can be evaluated against the governance needs of your event, team and supporter audience."
      />

      <MarketingFooter />
    </main>
  );
}
