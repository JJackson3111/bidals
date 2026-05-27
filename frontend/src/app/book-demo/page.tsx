import type { Metadata } from "next";

import { MarketingFooter, MarketingSection, PageHeader } from "@/components/marketing/MarketingBlocks";
import { MarketingLeadForm } from "@/components/marketing/MarketingLeadForm";

export const metadata: Metadata = {
  title: "Book a Demo | BIDALS",
  description: "Request a BIDALS demo for auctions, raffles, donations and mobile-first fundraising workflows.",
};

const demoTopics = [
  "Campaign structure and fundraising channels",
  "Auction setup, bidding and close-down",
  "Raffle workflow support and careful compliance language",
  "Donation journeys and campaign reporting needs",
];

export default function BookDemoPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Book a demo"
        title="See how BIDALS could support your next fundraising campaign."
        description="Use this frontend-only request form to capture demo intent while the backend or email integration is planned."
      />

      <MarketingSection
        eyebrow="Demo request"
        title="Tell us what you are building"
        description="A good demo should focus on your campaign model, supporter audience and governance needs."
      >
        <div className="marketing-form-layout">
          <MarketingLeadForm kind="demo" />
          <aside className="marketing-side-panel" aria-label="Demo topics">
            <h3>Useful demo topics</h3>
            <ul>
              {demoTopics.map((topic) => (
                <li key={topic}>{topic}</li>
              ))}
            </ul>
          </aside>
        </div>
      </MarketingSection>

      <MarketingFooter />
    </main>
  );
}
