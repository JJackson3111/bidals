import Link from "next/link";
import type { Metadata } from "next";
import {
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  HeartHandshake,
  ShieldCheck,
  Sparkles,
  Smartphone,
  TrendingUp,
  UsersRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { MarketingCTA, MarketingFooter, MarketingSection } from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "Pricing | BIDALS",
  description:
    "BIDALS pricing for Essentials, Fundraising Raffles and Signature branded fundraising experiences.",
};

type PricingPlan = {
  title: string;
  badge?: string;
  audience: string;
  tagline: string;
  price: string;
  secondaryLine: string;
  buyerCue?: string;
  features: string[];
  note?: string;
  partnership?: { label: string; value: string }[];
  cta: string;
  href: string;
  featured?: boolean;
};

type IconCard = {
  title: string;
  copy: string;
  icon: LucideIcon;
};

const trustItems = [
  "No setup fees",
  "No platform commissions",
  "Mobile-first bidding",
  "Auctions and donations",
  "Secure fundraising tools",
];

const outcomeCards: IconCard[] = [
  {
    title: "Increase Event Revenue",
    copy: "Encourage more bids, more participation and more ways for supporters to give.",
    icon: TrendingUp,
  },
  {
    title: "Reduce Event Administration",
    copy: "Replace paper sheets, manual winner tracking and fragmented event admin with a cleaner operating layer.",
    icon: ClipboardCheck,
  },
  {
    title: "Deliver a Better Supporter Experience",
    copy: "Give bidders and donors a modern mobile-first experience that feels simple, clear and professional.",
    icon: Smartphone,
  },
];

const essentialsPlan: PricingPlan = {
  title: "BIDALS Essentials",
  audience: "Best for churches, schools, small charities and community groups.",
  tagline: "Launch professional fundraising auctions and donations using the BIDALS platform.",
  price: "\u00a349/month",
  secondaryLine: "BIDALS-branded fundraising tools",
  features: [
    "Auctions",
    "Donations",
    "Mobile bidding",
    "Event dashboard",
    "Bid notifications",
    "BIDALS branding",
    "Standard support",
    "Platform updates",
  ],
  note: "Custom logo, colours, domain and Signature branding are available with BIDALS Signature.",
  cta: "Start Fundraising",
  href: "/register",
};

const signaturePlan: PricingPlan = {
  title: "BIDALS Signature",
  badge: "Recommended for branded fundraising",
  audience: "Best for recurring fundraising events, annual campaigns and fully branded experiences.",
  tagline: "Your brand. Your fundraising. Powered by BIDALS.",
  price: "\u00a32,000/year",
  secondaryLine: "3-year partnership \u00b7 Year 3 included",
  buyerCue: "Your organisation's own branded fundraising experience.",
  features: [
    "Your logo",
    "Your colours",
    "Branded fundraising experience",
    "Auctions",
    "Donations",
    "Raffles included",
    "Priority support",
    "Platform updates",
  ],
  partnership: [
    { label: "Year 1", value: "\u00a32,000" },
    { label: "Year 2", value: "\u00a32,000" },
    { label: "Year 3", value: "Included" },
  ],
  cta: "Book a Demo",
  href: "/book-demo",
  featured: true,
};

const raffleFeatures = ["Digital raffle ticket sales", "Prize management", "Winner draw tools", "Raffle reporting"];

const keepRaiseItems = ["No platform commissions", "No donation percentages", "No auction revenue sharing"];

const signatureReasons: IconCard[] = [
  {
    title: "Your logo and colours",
    copy: "Put your organisation, campaign and event identity at the centre of the supporter journey.",
    icon: Sparkles,
  },
  {
    title: "Raffles included",
    copy: "Run auctions, donations and raffles together without adding another monthly module.",
    icon: HeartHandshake,
  },
  {
    title: "Priority support",
    copy: "Give your team a clearer path from setup to event night with more responsive support.",
    icon: ClipboardCheck,
  },
  {
    title: "Built for recurring fundraising events",
    copy: "Support annual galas, school campaigns, church auctions and repeat fundraising moments with one polished platform.",
    icon: ShieldCheck,
  },
];

const audienceItems = [
  "Charity galas",
  "School fundraisers",
  "Church auctions",
  "PTA events",
  "Sports club campaigns",
  "Community raffles",
  "Corporate fundraising",
  "Silent auctions",
];

const traditionalFundraisingItems = [
  "Printed sheets",
  "Manual tracking",
  "Bid disputes",
  "Long checkout queues",
  "Limited engagement",
];

const bidalsFundraisingItems = [
  "Live mobile bidding",
  "Automated tracking",
  "Transparent bid history",
  "Instant winner identification",
  "Auctions, donations and raffles together",
];

const choiceCards: IconCard[] = [
  {
    title: "Raise more from every event",
    copy: "Give supporters a simpler way to bid, donate and take part in the moment.",
    icon: TrendingUp,
  },
  {
    title: "Reduce volunteer workload",
    copy: "Automate bidding, winner tracking and event reporting so teams spend less time reconciling results.",
    icon: ClipboardCheck,
  },
  {
    title: "Look more professional",
    copy: "Deliver a polished fundraising experience that reflects the quality of your organisation.",
    icon: Sparkles,
  },
];

const faqs = [
  {
    question: "Is there a setup fee?",
    answer: "No. BIDALS is designed to be simple to adopt without heavy upfront setup costs.",
  },
  {
    question: "Can I cancel the monthly plan?",
    answer: "Yes. The monthly Essentials plan is designed for flexibility.",
  },
  {
    question: "Why is Signature structured as a 3-year partnership?",
    answer:
      "Most organisations run recurring fundraising events. The partnership model allows BIDALS to support long-term fundraising growth, continuous platform improvement and a stronger branded experience, with Year 3 included.",
  },
  {
    question: "Can I use my own branding?",
    answer:
      "Yes. BIDALS Signature includes your logo, colours and branded fundraising experience. Essentials uses BIDALS branding.",
  },
  {
    question: "Do you charge transaction fees?",
    answer:
      "BIDALS does not take platform commissions, donation percentages or auction revenue share. Standard payment processing fees from providers such as Stripe may still apply.",
  },
  {
    question: "Can charities, schools and churches treat BIDALS as an expense?",
    answer:
      "BIDALS would usually be treated as an operational fundraising software cost, but organisations should always confirm with their accountant or finance adviser.",
  },
];

function TickList({ items }: { items: string[] }) {
  return (
    <ul>
      {items.map((item) => (
        <li key={item}>
          <CheckCircle2 size={17} aria-hidden="true" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function OutcomeCard({ card }: { card: IconCard }) {
  const Icon = card.icon;

  return (
    <article className="pricing-icon-card">
      <span className="pricing-icon-card-mark">
        <Icon size={18} aria-hidden="true" />
      </span>
      <h3>{card.title}</h3>
      <p>{card.copy}</p>
    </article>
  );
}

function PricingCard({ plan, className }: { plan: PricingPlan; className: string }) {
  return (
    <article
      className={`marketing-pricing-card pricing-plan-card ${className} ${
        plan.featured ? "marketing-pricing-card-featured pricing-plan-card-featured" : ""
      }`}
    >
      <div className="pricing-plan-top">
        <div>
          <span>{plan.audience}</span>
          <h2>{plan.title}</h2>
        </div>
        {plan.badge ? <span className="pricing-plan-badge">{plan.badge}</span> : null}
      </div>
      <p className="pricing-plan-tagline">{plan.tagline}</p>
      {plan.buyerCue ? <p className="pricing-plan-buyer-cue">{plan.buyerCue}</p> : null}
      <div className="pricing-plan-price">
        <strong>{plan.price}</strong>
        <span>{plan.secondaryLine}</span>
      </div>
      {plan.partnership ? (
        <div className="pricing-partnership" aria-label="BIDALS Signature partnership structure">
          {plan.partnership.map((item) => (
            <div key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      ) : null}
      <TickList items={plan.features} />
      {plan.note ? <p className="pricing-plan-note">{plan.note}</p> : null}
      <Link className={`marketing-button ${plan.featured ? "primary-button" : "secondary-button"}`} href={plan.href}>
        {plan.cta}
        <ArrowRight size={18} aria-hidden="true" />
      </Link>
    </article>
  );
}

export default function PricingPage() {
  return (
    <main className="marketing-page pricing-page">
      <section className="pricing-hero">
        <div className="marketing-container pricing-hero-grid">
          <div className="pricing-hero-copy">
            <span className="eyebrow marketing-eyebrow">BIDALS pricing</span>
            <h1>Pricing built for fundraisers, not software buyers.</h1>
            <p>
              Whether you&apos;re running a church auction, school fundraiser, charity gala or community campaign, BIDALS helps
              you raise more while doing less.
            </p>
            <ul className="pricing-trust-row" aria-label="Pricing trust signals">
              {trustItems.map((item) => (
                <li key={item}>
                  <CheckCircle2 size={17} aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <aside className="pricing-hero-proof" aria-label="Pricing model summary">
            <span>Transparent subscriptions</span>
            <h2>Simple pricing for serious fundraising.</h2>
            <p>
              Choose BIDALS-branded tools for flexible campaigns, or Signature for a fully branded fundraising experience
              with raffles included.
            </p>
            <div className="pricing-hero-example">
              <span>Commercial promise</span>
              <strong>No platform commissions, no donation percentages and no auction revenue sharing.</strong>
            </div>
            <small>Standard payment processing fees from providers such as Stripe may still apply.</small>
          </aside>
        </div>
      </section>

      <MarketingSection
        eyebrow="Fundraising outcomes"
        title="What BIDALS helps you achieve"
        description="Pricing matters most when it connects directly to better fundraising events, less admin and a smoother supporter experience."
      >
        <div className="pricing-outcome-grid">
          {outcomeCards.map((card) => (
            <OutcomeCard card={card} key={card.title} />
          ))}
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="Pricing"
        title="Simple pricing for modern fundraising."
        description="Choose the BIDALS-branded Essentials plan, then add raffles if you need them, or move to Signature for a fully branded annual partnership."
        tone="muted"
      >
        <div className="marketing-pricing-grid pricing-plan-grid" aria-label="BIDALS pricing options">
          <PricingCard className="pricing-essentials-card" plan={essentialsPlan} />

          <article className="pricing-addon-card" aria-label="Fundraising Raffles add-on for BIDALS Essentials">
            <div className="pricing-addon-top">
              <span className="pricing-icon-card-mark">
                <HeartHandshake size={18} aria-hidden="true" />
              </span>
              <div>
                <span>Optional Essentials add-on</span>
                <h3>Fundraising Raffles</h3>
              </div>
            </div>
            <div className="pricing-addon-price">
              <strong>+&pound;19/month</strong>
              <span>Add digital raffle ticket sales, prize management and winner draw tools.</span>
            </div>
            <TickList items={raffleFeatures} />
          </article>

          <PricingCard className="pricing-signature-card" plan={signaturePlan} />
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="Fundraising trust"
        title="Keep 100% of what you raise"
        description="BIDALS is funded through transparent software subscriptions, not by taking a share of your fundraising success."
      >
        <div className="pricing-keep-card">
          <div>
            <ShieldCheck size={24} aria-hidden="true" />
            <h3>When your fundraising grows, BIDALS does not take a larger share.</h3>
            <p>You keep the success you create.</p>
          </div>
          <TickList items={keepRaiseItems} />
          <p>
            Standard payment processing fees from providers such as Stripe may still apply, but BIDALS does not charge a
            platform commission on the funds you raise.
          </p>
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="Signature"
        title="Why organisations choose Signature"
        description="Signature is designed for organisations that want BIDALS to feel like their own fundraising platform while keeping fundraising operations simple and predictable."
        tone="muted"
      >
        <div className="pricing-signature-grid">
          {signatureReasons.map((card) => (
            <OutcomeCard card={card} key={card.title} />
          ))}
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="Built for"
        title="Built for organisations running modern fundraising events"
        description="BIDALS is suitable for the fundraising formats where clear participation, reliable records and professional presentation matter."
      >
        <ul className="pricing-audience-grid" aria-label="Fundraising event types BIDALS is built for">
          {audienceItems.map((item) => (
            <li key={item}>
              <UsersRound size={15} aria-hidden="true" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </MarketingSection>

      <MarketingSection
        eyebrow="Fundraising momentum"
        title="Raise more. Spend less time managing."
        description="BIDALS replaces the friction of traditional fundraising with a cleaner digital flow for bids, donations, raffles and event outcomes."
        tone="dark"
      >
        <div className="pricing-roi-layout">
          <div className="pricing-roi-comparison" aria-label="Traditional fundraising compared with BIDALS">
            <article>
              <span>Traditional fundraising</span>
              <TickList items={traditionalFundraisingItems} />
            </article>
            <article className="pricing-roi-bidals">
              <span>With BIDALS</span>
              <TickList items={bidalsFundraisingItems} />
            </article>
          </div>
          <aside className="pricing-roi-example-card" aria-label="Illustrative fundraising uplift example">
            <span>Illustrative example</span>
            <div className="pricing-roi-equation">
              <strong>250 attendees</strong>
              <span>+</span>
              <strong>&pound;15 increase in average supporter spend</strong>
              <span>=</span>
              <strong>Potential additional funds raised: &pound;3,750</strong>
            </div>
            <p>Illustrative example only. Actual results vary by event and audience.</p>
          </aside>
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="Why BIDALS"
        title="Why organisations choose BIDALS."
        description="The platform is built around the outcomes fundraising teams actually need from every event."
        tone="muted"
      >
        <div className="marketing-mini-grid pricing-choice-grid">
          {choiceCards.map((card) => (
            <OutcomeCard card={card} key={card.title} />
          ))}
        </div>
      </MarketingSection>

      <MarketingSection
        eyebrow="FAQ"
        title="Pricing questions, answered plainly."
        description="Clear commercial notes for fundraising teams, finance leads and event organisers."
      >
        <div className="pricing-faq-list">
          {faqs.map((faq) => (
            <details key={faq.question}>
              <summary>{faq.question}</summary>
              <p>{faq.answer}</p>
            </details>
          ))}
        </div>
      </MarketingSection>

      <MarketingCTA
        title="Ready to see BIDALS in action?"
        description="Book a live demo and see how auctions, donations and raffles work together in one professional fundraising platform."
        primaryCta={{ href: "/book-demo", label: "Book a Demo" }}
        secondaryCta={{ href: "/features", label: "Explore Features" }}
      />

      <MarketingFooter />
    </main>
  );
}