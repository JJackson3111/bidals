import type { Metadata } from "next";
import { Headphones, MailQuestion, ShieldCheck } from "lucide-react";

import { MarketingFooter, MarketingSection, PageHeader } from "@/components/marketing/MarketingBlocks";
import { MarketingLeadForm } from "@/components/marketing/MarketingLeadForm";

export const metadata: Metadata = {
  title: "Contact | BIDALS",
  description:
    "Contact BIDALS about auctions, raffles, donations, secure fundraising operations, white-label needs and platform partnerships.",
};

const contactReasons = [
  "Campaign, demo and pricing conversations",
  "Support questions for fundraising operations",
  "Security, governance and data ownership discussions",
  "White-label, partner and event operator enquiries",
];

const supportDetails = [
  "Tell us about your fundraising plans, timeline and operating context.",
  "Include your organisation, event timeline and fundraising formats where possible.",
  "Do not share payment card data, passwords or sensitive supporter information.",
];

export default function ContactPage() {
  return (
    <main className="marketing-page">
      <PageHeader
        eyebrow="Contact"
        title="Talk to BIDALS about secure digital fundraising."
        description="Share the context for your campaign, support need or partnership conversation and we will come back to you directly."
      />

      <MarketingSection
        eyebrow="Enquiry"
        title="A clean route into the BIDALS team"
        description="Keep the message focused on your event model, operational needs and the part of the platform you want to discuss."
      >
        <div className="marketing-form-layout">
          <div className="marketing-form-card">
            <span className="marketing-inline-icon">
              <MailQuestion size={19} aria-hidden="true" />
              Contact request
            </span>
            <MarketingLeadForm kind="contact" />
            <p className="marketing-form-note">
              We&apos;ll review your request and come back to you directly.
            </p>
          </div>
          <aside className="marketing-side-panel" aria-label="Support and contact details">
            <span className="marketing-inline-icon">
              <Headphones size={19} aria-hidden="true" />
              Support details
            </span>
            <h3>What to include</h3>
            <ul>
              {contactReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
            <div className="marketing-side-divider" />
            <span className="marketing-inline-icon">
              <ShieldCheck size={19} aria-hidden="true" />
              Safe handling
            </span>
            <ul>
              {supportDetails.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          </aside>
        </div>
      </MarketingSection>

      <MarketingFooter />
    </main>
  );
}
