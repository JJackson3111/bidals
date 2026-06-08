import Image from "next/image";
import Link from "next/link";
import type { Metadata } from "next";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Gavel,
  HeartHandshake,
  Palette,
  ShieldCheck,
  Sparkles,
  Ticket,
  Trophy,
  UsersRound,
} from "lucide-react";

import { MarketingFooter } from "@/components/marketing/MarketingBlocks";

export const metadata: Metadata = {
  title: "BIDALS | Fundraising Operating System",
  description:
    "BIDALS is the fundraising operating system for premium auctions, raffles, donations and governed event outcomes.",
};

type PlatformModule = {
  title: string;
  description: string;
  icon: LucideIcon;
  signal: string;
  metric: string;
};

type ProofCard = {
  title: string;
  description: string;
  icon: LucideIcon;
};

const trustChips = ["Mobile-first experiences", "Server-authoritative records", "Enterprise-grade governance"];

const phoneMoments = [
  {
    eyebrow: "Browse experience",
    title: "Gala lots open",
    meta: "42 live lots",
    value: "From GBP 180",
    detail: "Supporters browse auction, raffle and donation moments from one mobile journey.",
  },
  {
    eyebrow: "Live auction",
    title: "Chef's table for eight",
    meta: "12 active bidders",
    value: "GBP 2,400",
    detail: "Watchlist active with live bid history and controlled close timing.",
  },
  {
    eyebrow: "Bid accepted state",
    title: "Bid accepted",
    meta: "Server record created",
    value: "GBP 2,550",
    detail: "The accepted bid is recorded by the platform and reflected immediately.",
  },
  {
    eyebrow: "Auction progress",
    title: "Reserve met",
    meta: "Outcome ready",
    value: "86%",
    detail: "Campaign progress, reserve status and next actions remain visible.",
  },
  {
    eyebrow: "Donation moment",
    title: "Children's appeal",
    meta: "Gift received",
    value: "GBP 125",
    detail: "Donation paths sit beside auction activity without breaking the supporter flow.",
  },
  {
    eyebrow: "Raffle moment",
    title: "Grand prize draw",
    meta: "184 entries",
    value: "GBP 3,680",
    detail: "Raffle participation is captured with clear organiser review.",
  },
  {
    eyebrow: "Winner confirmation",
    title: "Winner confirmed",
    meta: "Outcome governed",
    value: "Lot 18",
    detail: "Final outcomes can be reviewed, repaired and defended after the event.",
  },
];

const floatingSignals = [
  "Bid accepted",
  "Auction live",
  "Donation received",
  "Reserve met",
  "Winner confirmed",
  "Outcome governed",
];

const platformModules: PlatformModule[] = [
  {
    title: "Auctions",
    description:
      "Create live and silent auction moments with mobile bidding, watchlists and server-owned bid records.",
    icon: Gavel,
    signal: "Live bidding",
    metric: "42 lots",
  },
  {
    title: "Raffles",
    description:
      "Support raffle-style fundraising with clear participant flows, organiser review and compliant draw records.",
    icon: Ticket,
    signal: "Draw review",
    metric: "184 entries",
  },
  {
    title: "Donations",
    description:
      "Capture generosity in the same premium experience with simple one-off or recurring donation paths.",
    icon: HeartHandshake,
    signal: "Gift path",
    metric: "GBP 12.8k",
  },
  {
    title: "Analytics",
    description:
      "See campaign progress, bidder activity and donation momentum without stitching reports together.",
    icon: BarChart3,
    signal: "Momentum",
    metric: "86% target",
  },
  {
    title: "Governance",
    description:
      "Keep roles, permissions, audit trails and outcome controls close to every fundraising moment.",
    icon: ShieldCheck,
    signal: "Controls on",
    metric: "7 roles",
  },
];

const dashboardFeed = [
  { label: "Bid accepted", detail: "Lot 18 raised to GBP 2,550", tone: "live" },
  { label: "Donation received", detail: "GBP 125 added to Children's appeal", tone: "gift" },
  { label: "Raffle entry", detail: "12 grand prize entries reserved", tone: "raffle" },
  { label: "Outcome review", detail: "Winner confirmation ready for organiser", tone: "review" },
];

const leaderboard = [
  { name: "Chef's table", value: "GBP 2,550" },
  { name: "Weekend retreat", value: "GBP 1,920" },
  { name: "Signed guitar", value: "GBP 1,340" },
];

const brandSignals = [
  "Organisation logo",
  "Event branding",
  "Brand colour accents",
  "Supporter-facing experience",
  "Admin controls",
  "BIDALS operating layer beneath",
];

const choiceCards: ProofCard[] = [
  {
    title: "Confidence",
    description: "Every accepted bid is recorded by the platform, not guessed by the browser.",
    icon: CheckCircle2,
  },
  {
    title: "Governance",
    description:
      "Roles, permissions, audit trails and outcome controls help teams manage sensitive fundraising moments properly.",
    icon: ShieldCheck,
  },
  {
    title: "Growth",
    description:
      "Auctions, raffles and donations operate together so campaigns can expand without fragmenting the supporter journey.",
    icon: Activity,
  },
];

const proofPoints = [
  "Accepted bid records",
  "Outcome repair workflows",
  "Governance controls",
  "Audit history",
  "Role permissions",
  "Seller administration",
  "Bid protection",
];

function HomeActions({
  primaryLabel = "Book a demo",
  secondaryLabel = "Explore the platform",
}: {
  primaryLabel?: string;
  secondaryLabel?: string;
}) {
  return (
    <div className="home-actions">
      <Link className="home-button home-button-primary" href="/book-demo">
        {primaryLabel}
        <ArrowRight size={18} aria-hidden="true" />
      </Link>
      <Link className="home-button home-button-secondary" href="/features">
        {secondaryLabel}
      </Link>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
  dark = false,
}: {
  eyebrow: string;
  title: string;
  description: string;
  dark?: boolean;
}) {
  return (
    <div className={`home-section-heading ${dark ? "home-section-heading-dark" : ""}`}>
      <span className="home-eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      <p>{description}</p>
    </div>
  );
}

function HeroPhone() {
  return (
    <div className="home-product-stage" aria-label="BIDALS mobile product preview">
      {floatingSignals.map((signal, index) => (
        <span className={`home-floating-signal home-floating-signal-${index + 1}`} key={signal}>
          <span aria-hidden="true" />
          {signal}
        </span>
      ))}

      <article className="home-phone" aria-label="Animated preview of BIDALS supporter journey">
        <div className="home-phone-frame">
          <div className="home-phone-island" aria-hidden="true" />
          <div className="home-phone-screen">
            <div className="home-phone-topbar">
              <Image src="/bidals-logo-mark.png" alt="" width={24} height={24} priority />
              <div>
                <span>Harbour House Gala</span>
                <strong>Live fundraiser</strong>
              </div>
            </div>
            <div className="home-phone-scroll">
              {phoneMoments.map((moment) => (
                <section className="home-phone-moment" key={moment.eyebrow}>
                  <div className="home-phone-media" aria-hidden="true">
                    <span />
                    <span />
                  </div>
                  <div className="home-phone-moment-copy">
                    <span>{moment.eyebrow}</span>
                    <h3>{moment.title}</h3>
                    <p>{moment.detail}</p>
                  </div>
                  <div className="home-phone-metric">
                    <span>{moment.meta}</span>
                    <strong>{moment.value}</strong>
                  </div>
                  <div className="home-phone-action-row">
                    <span>Live record</span>
                    <strong>Governed</strong>
                  </div>
                </section>
              ))}
            </div>
          </div>
        </div>
      </article>
    </div>
  );
}

function PlatformModuleCard({ module }: { module: PlatformModule }) {
  const Icon = module.icon;

  return (
    <article className="home-platform-module">
      <div className="home-platform-module-top">
        <span className="home-module-icon">
          <Icon size={19} aria-hidden="true" />
        </span>
        <span>{module.signal}</span>
      </div>
      <div className="home-module-body">
        <h3>{module.title}</h3>
        <p>{module.description}</p>
      </div>
      <div className="home-module-rail" aria-hidden="true">
        <span />
      </div>
      <strong>{module.metric}</strong>
    </article>
  );
}

function OperatingDashboard() {
  return (
    <div className="home-dashboard-shell" aria-label="Illustrative BIDALS event operating dashboard">
      <div className="home-dashboard-top">
        <div>
          <span>Operating view</span>
          <h3>Harbour House Gala</h3>
        </div>
        <strong>Live</strong>
      </div>

      <div className="home-dashboard-metrics">
        <div>
          <span>Donation total</span>
          <strong>GBP 12,840</strong>
        </div>
        <div>
          <span>Raffle entries</span>
          <strong>184</strong>
        </div>
        <div>
          <span>Auction progress</span>
          <strong>86%</strong>
        </div>
      </div>

      <div className="home-dashboard-grid">
        <section className="home-activity-feed">
          <div className="home-panel-title">
            <Activity size={17} aria-hidden="true" />
            <span>Activity feed</span>
          </div>
          {dashboardFeed.map((item) => (
            <article className={`home-feed-row home-feed-row-${item.tone}`} key={item.label}>
              <span aria-hidden="true" />
              <div>
                <strong>{item.label}</strong>
                <p>{item.detail}</p>
              </div>
            </article>
          ))}
        </section>

        <section className="home-leaderboard">
          <div className="home-panel-title">
            <Trophy size={17} aria-hidden="true" />
            <span>Leaderboard</span>
          </div>
          {leaderboard.map((item, index) => (
            <div className="home-leader-row" key={item.name}>
              <span>{index + 1}</span>
              <strong>{item.name}</strong>
              <em>{item.value}</em>
            </div>
          ))}
          <div className="home-outcome-review">
            <ClipboardCheck size={18} aria-hidden="true" />
            <div>
              <span>Outcome review</span>
              <strong>Recent winners ready for confirmation</strong>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <main className="marketing-page homepage-v2">
      <section className="home-hero">
        <div className="home-container home-hero-grid">
          <div className="home-hero-copy">
            <span className="home-eyebrow">BIDALS fundraising operating system</span>
            <h1>Power every bid.</h1>
            <p className="home-hero-lede">
              The fundraising operating system built for auctions, raffles, donations and event teams.
            </p>
            <p className="home-hero-promise">
              Premium for supporters.
              <br />
              Governed for operators.
              <br />
              Trusted for outcomes.
            </p>
            <HomeActions />
            <ul className="home-trust-chips" aria-label="BIDALS trust signals">
              {trustChips.map((chip) => (
                <li key={chip}>
                  <CheckCircle2 size={16} aria-hidden="true" />
                  <span>{chip}</span>
                </li>
              ))}
            </ul>
          </div>
          <HeroPhone />
        </div>
      </section>

      <section className="home-section">
        <div className="home-container">
          <SectionHeading
            eyebrow="Unified fundraising"
            title="Fundraising without fragmentation"
            description="Bring auctions, raffles, donations, analytics and governance into one calm operating layer."
          />
          <div className="home-platform-grid">
            {platformModules.map((module) => (
              <PlatformModuleCard module={module} key={module.title} />
            ))}
          </div>
        </div>
      </section>

      <section className="home-section home-section-muted">
        <div className="home-container home-ops-grid">
          <div>
            <SectionHeading
              eyebrow="Live operations"
              title="See the event as it happens"
              description="BIDALS gives event teams a live operating view of bids, raffle entries, donations, campaign progress and outcomes."
            />
            <div className="home-ops-proof">
              <span>
                <UsersRound size={17} aria-hidden="true" />
                Event teams
              </span>
              <span>
                <BarChart3 size={17} aria-hidden="true" />
                Campaign progress
              </span>
              <span>
                <ShieldCheck size={17} aria-hidden="true" />
                Outcome review
              </span>
            </div>
          </div>
          <OperatingDashboard />
        </div>
      </section>

      <section className="home-section">
        <div className="home-container home-brand-grid">
          <div className="home-brand-visual" aria-label="Illustrative branded BIDALS deployment">
            <div className="home-brand-card">
              <div className="home-brand-header">
                <span className="home-brand-logo">HH</span>
                <div>
                  <span>Harbour House Foundation</span>
                  <strong>Spring Gala 2026</strong>
                </div>
              </div>
              <div className="home-brand-banner">
                <span>Event-branded fundraising</span>
                <strong>Bid, enter, donate</strong>
              </div>
              <div className="home-brand-controls">
                <span>
                  <Palette size={16} aria-hidden="true" />
                  Brand colour accents
                </span>
                <span>
                  <ShieldCheck size={16} aria-hidden="true" />
                  Admin controls
                </span>
              </div>
              <div className="home-brand-layer">
                <Sparkles size={17} aria-hidden="true" />
                <span>BIDALS operating layer beneath</span>
              </div>
            </div>
          </div>
          <div className="home-brand-copy">
            <span className="home-eyebrow">Brand-led deployment</span>
            <h2>Your organisation. Front and centre.</h2>
            <p>
              Run campaigns with your event identity, organisation branding and supporter experience leading the journey
              - powered quietly by BIDALS underneath.
            </p>
            <div className="home-brand-tags" aria-label="Brand-led deployment elements">
              {brandSignals.map((signal) => (
                <span key={signal}>{signal}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="home-section home-section-muted">
        <div className="home-container">
          <SectionHeading
            eyebrow="Why BIDALS"
            title="Why event teams choose BIDALS"
            description="Premium supporter journeys only matter when the operational record behind them is strong enough for real fundraising pressure."
          />
          <div className="home-choice-grid">
            {choiceCards.map((card) => {
              const Icon = card.icon;

              return (
                <article className="home-choice-card" key={card.title}>
                  <span className="home-choice-icon">
                    <Icon size={22} aria-hidden="true" />
                  </span>
                  <h3>{card.title}</h3>
                  <p>{card.description}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="home-dark-section">
        <div className="home-container home-dark-grid">
          <div>
            <SectionHeading
              eyebrow="Defensible outcomes"
              title="Beautiful in the room. Defensible afterwards."
              description="BIDALS is designed to feel effortless for supporters while giving operators the records, permissions and controls they need after the event gets busy."
              dark
            />
          </div>
          <div className="home-proof-board" aria-label="BIDALS governance proof points">
            {proofPoints.map((point) => (
              <div className="home-proof-point" key={point}>
                <span aria-hidden="true" />
                <strong>{point}</strong>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="home-final-cta">
        <div className="home-container">
          <span className="home-cta-mark">
            <Sparkles size={19} aria-hidden="true" />
          </span>
          <h2>Run your next fundraiser with confidence.</h2>
          <p>Bring auctions, raffles and donations into one governed fundraising platform.</p>
          <HomeActions secondaryLabel="Explore features" />
        </div>
      </section>

      <MarketingFooter />
    </main>
  );
}
