import type { Metadata } from "next";
import { BadgeCheck, FileCheck2, LockKeyhole, Settings2, ShieldCheck, Trophy, UsersRound } from "lucide-react";

import {
  FeatureGrid,
  MarketingCTA,
  MarketingDashboardPanel,
  MarketingFooter,
  MarketingSection,
  PageHeader,
  TrustSection,
} from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Security and Governance | BIDALS",
  description:
    "BIDALS security positioning covers server-authoritative bidding, immutable audit trails, admin roles, repair controls, secure winner selection and payment readiness planning.",
};

const securityFeatures = [
  {
    eyebrow: "Bidding",
    title: "Server-authoritative bidding",
    description:
      "Bid acceptance belongs to the backend so the public interface reflects the trusted record rather than becoming it.",
    icon: ShieldCheck,
    items: ["Backend validation", "Accepted and rejected bid state", "Consistent bidder feedback"],
  },
  {
    eyebrow: "Audit",
    title: "Immutable audit trails",
    description:
      "Important actions should leave timestamped, reviewable records for event operators and trusted admins.",
    icon: FileCheck2,
    items: ["Timestamped activity", "Outcome traceability", "Operational investigation support"],
  },
  {
    eyebrow: "Access",
    title: "Admin roles and permissions",
    description:
      "Separate public participation from private campaign administration with role-aware access patterns.",
    icon: UsersRound,
    items: ["Seller workflows", "Admin review", "Permission boundaries"],
  },
  {
    eyebrow: "Governance",
    title: "Repair and governance controls",
    description:
      "Sensitive outcomes need controlled repair paths, review visibility and clear accountability when exceptions arise.",
    icon: Settings2,
    items: ["Outcome repair controls", "Admin review paths", "Governed status changes"],
  },
  {
    eyebrow: "Winners",
    title: "Secure winner selection",
    description:
      "Winner handling should be explainable, reviewable and connected to the records that produced the result.",
    icon: Trophy,
    items: ["Winner records", "Draw preparation language", "Fulfillment handoff"],
  },
  {
    eyebrow: "Payments",
    title: "PCI and payment readiness planning",
    description:
      "Payment-provider and PCI requirements can be assessed during implementation without claiming certification that has not been verified.",
    icon: BadgeCheck,
    items: ["Processor scoping", "PCI readiness language", "No unverified compliance claims"],
  },
];

const securityMetrics = [
  { label: "Bid truth", value: "Server-owned", detail: "Backend record as authority" },
  { label: "Admin access", value: "Role-aware", detail: "Operational permission model" },
  { label: "Outcome state", value: "Reviewable", detail: "Audit and repair controls" },
];

const securityRows = [
  { label: "Bidding engine", value: "Untouched", status: "live" as const },
  { label: "Auth flow", value: "Untouched", status: "ready" as const },
  { label: "Dashboard behavior", value: "Untouched", status: "review" as const },
];

export default function SecurityPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Security"
        title="Trust infrastructure for serious fundraising."
        description="BIDALS is positioned around secure participation, server-authoritative records, admin governance and transparent outcomes for campaigns where trust matters."
      />

      <MarketingSection
        eyebrow="Trust architecture"
        title="A security page with operational weight"
        description="The visual language is deliberately serious: shield motifs, dark panels, precise claims and clear boundaries around what is implemented versus what is readiness planning."
        tone="dark"
      >
        <div className="marketing-security-grid">
          <div className="marketing-security-mark" aria-hidden="true">
            <LockKeyhole size={56} />
            <span />
          </div>
          <MarketingDashboardPanel
            title="Governance status"
            metrics={securityMetrics}
            rows={securityRows}
            note="This panel describes marketing/security positioning only. It does not change API, bidding, authentication or dashboard logic."
            dark
          />
        </div>
      </MarketingSection>

      <FeatureGrid
        eyebrow="Security themes"
        title="The controls buyers need to understand"
        description="Security is framed through records, permissions, governance and careful compliance language."
        features={securityFeatures}
      />

      <TrustSection
        eyebrow="Platform posture"
        title="Clear boundaries between public pages and product logic"
        description="These marketing pages explain security and governance while leaving the existing product systems untouched."
        items={[
          "Server-authoritative bidding and backend-owned accepted-bid state",
          "Immutable audit trails and repair/governance controls",
          "Admin roles, permissions and controlled outcome review",
          "PCI and payment readiness wording without unverified certification claims",
        ]}
      />

      <MarketingCTA
        title="Talk through security expectations before launch."
        description="Evaluate BIDALS against your event governance needs, supporter audience, payment approach and internal operating model."
      />

      <MarketingFooter />
    </main>
  );
}
