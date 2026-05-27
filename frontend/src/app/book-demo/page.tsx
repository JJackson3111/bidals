import type { Metadata } from "next";
import { BadgeCheck, CalendarCheck, ShieldCheck } from "lucide-react";

import { MarketingFooter, MarketingMetricStrip, MarketingSection, PageHeader } from "@/components/marketing/MarketingBlocks";
import { MarketingLeadForm } from "@/components/marketing/MarketingLeadForm";

export const metadata: Metadata = {
  title: "Book a Demo | BIDALS",
  description:
    "Request a BIDALS demo for auctions, raffles, donations, white-label event needs and mobile-first fundraising operations.",
};

const demoTopics = [
  "How your auction, raffle and donation flows should work together.",
  "Where bidder confidence, close-down rules and audit trails matter most.",
  "What white-label, reporting and governance needs your event team has.",
  "Which backend or email workflow should safely handle future lead submissions.",
];

export default function BookDemoPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Book a demo"
        title="See BIDALS as your fundraising operating system."
        description="Use this frontend-only request form to capture demo intent while the backend or email integration is planned."
      />

      <MarketingSection
        eyebrow="Demo request"
        title="A focused walkthrough for serious fundraising teams"
        description="The best demo starts with your event model, supporter audience, governance requirements and launch timeline."
      >
        <div className="marketing-form-layout marketing-form-layout-premium">
          <aside className="marketing-side-panel marketing-side-panel-dark" aria-label="Why book a demo">
            <span className="marketing-inline-icon">
              <CalendarCheck size={19} aria-hidden="true" />
              Why book
            </span>
            <h3>Make the conversation operational</h3>
            <p>
              BIDALS demos should cover the public supporter journey and the private controls your team needs to trust the outcome.
            </p>
            <ul>
              {demoTopics.map((topic) => (
                <li key={topic}>{topic}</li>
              ))}
            </ul>
            <MarketingMetricStrip
              metrics={[
                { label: "Formats", value: "3", detail: "Auctions, raffles, donations" },
                { label: "Readiness", value: "Scoped", detail: "Brand, payment and governance needs" },
              ]}
              note="Frontend-only form today. TODO: connect to an approved backend or email workflow."
            />
          </aside>
          <div className="marketing-form-card">
            <span className="marketing-inline-icon">
              <ShieldCheck size={19} aria-hidden="true" />
              Frontend-only capture
            </span>
            <MarketingLeadForm kind="demo" />
            <p className="marketing-form-note">
              This form does not send to a backend yet. The TODO remains to connect a safe lead or email integration.
            </p>
          </div>
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="Good fit"
        title="Built for teams that need premium presentation and clean governance"
        description="BIDALS is most useful when the event needs mobile participation, transparent outcomes and an operating layer the team can rely on."
        tone="muted"
      >
        <div className="marketing-mini-grid">
          <div>
            <BadgeCheck size={20} aria-hidden="true" />
            <h3>Premium events</h3>
            <p>Gala auctions, charity evenings, school appeals and partner-led fundraising campaigns.</p>
          </div>
          <div>
            <ShieldCheck size={20} aria-hidden="true" />
            <h3>Governed outcomes</h3>
            <p>Teams that need careful records, role-aware controls and trust-building supporter communication.</p>
          </div>
        </div>
      </MarketingSection>

      <MarketingFooter />
    </main>
  );
}
