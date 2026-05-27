import type { Metadata } from "next";

import { MarketingFooter, MarketingSection, PageHeader } from "@/components/marketing/MarketingBlocks";
import { MarketingLeadForm } from "@/components/marketing/MarketingLeadForm";

export const metadata: Metadata = {
  title: "Contact | BIDALS",
  description: "Contact BIDALS about digital fundraising, auctions, raffles, donations and platform partnerships.",
};

const contactReasons = [
  "Questions about a fundraising campaign",
  "Organisation or partner enquiries",
  "Security and governance discussions",
  "Future domain, Render or launch coordination",
];

export default function ContactPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Contact"
        title="Talk to BIDALS about secure digital fundraising."
        description="Use this frontend-only contact page for now. A backend or email workflow can be connected once the safe endpoint is agreed."
      />

      <MarketingSection
        eyebrow="Enquiry"
        title="Send a message"
        description="Share the context for your campaign, organisation or partnership conversation."
      >
        <div className="marketing-form-layout">
          <MarketingLeadForm kind="contact" />
          <aside className="marketing-side-panel" aria-label="Contact reasons">
            <h3>Good reasons to get in touch</h3>
            <ul>
              {contactReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </aside>
        </div>
      </MarketingSection>

      <MarketingFooter />
    </main>
  );
}
