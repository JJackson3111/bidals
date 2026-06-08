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
  Monitor,
  Palette,
  ShieldCheck,
  Sparkles,
  Smartphone,
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

type BrandTheme = {
  id: string;
  organisation: string;
  event: string;
  initials: string;
  accent: string;
  palette: string;
  story: string;
  lot: string;
  lotMeta: string;
  currentBid: string;
  nextBid: string;
  donation: string;
  raffle: string;
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

const brandThemes: BrandTheme[] = [
  {
    id: "harbour",
    organisation: "Harbour House Foundation",
    event: "Spring Gala 2026",
    initials: "HH",
    accent: "Acid green / muted teal",
    palette: "Signature gala",
    story: "A polished evening auction supporting long-term community projects.",
    lot: "Chef's table for eight",
    lotMeta: "Live lot 18",
    currentBid: "GBP 2,550",
    nextBid: "Quick bid GBP 2,700",
    donation: "Children's appeal GBP 12.8k",
    raffle: "Grand prize raffle 184 entries",
  },
  {
    id: "mary",
    organisation: "St Mary's School",
    event: "Summer Giving Evening",
    initials: "SM",
    accent: "Warm gold / deep navy",
    palette: "School evening",
    story: "A confident supporter journey for parents, alumni and local sponsors.",
    lot: "Headteacher's dinner",
    lotMeta: "Live lot 07",
    currentBid: "GBP 1,180",
    nextBid: "Quick bid GBP 1,250",
    donation: "Library appeal GBP 6.4k",
    raffle: "Family hamper 96 entries",
  },
  {
    id: "oakfield",
    organisation: "Oakfield Hospice",
    event: "Care & Community Auction",
    initials: "OH",
    accent: "Soft lavender / deep plum",
    palette: "Care campaign",
    story: "A calm, warm auction experience built around donor confidence.",
    lot: "Garden retreat weekend",
    lotMeta: "Live lot 12",
    currentBid: "GBP 1,760",
    nextBid: "Quick bid GBP 1,850",
    donation: "Care fund GBP 18.2k",
    raffle: "Memory tree raffle 142 entries",
  },
  {
    id: "sports",
    organisation: "Local Sports Trust",
    event: "Clubhouse Fundraiser",
    initials: "LST",
    accent: "Bright green / dark graphite",
    palette: "Club campaign",
    story: "A direct, energetic experience for members, families and sponsors.",
    lot: "Signed matchday shirt",
    lotMeta: "Live lot 03",
    currentBid: "GBP 820",
    nextBid: "Quick bid GBP 900",
    donation: "Youth teams GBP 9.1k",
    raffle: "Season ticket raffle 211 entries",
  },
];

const brandStudioElements = [
  "Organisation logo",
  "Event branding",
  "Brand colour accents",
  "Supporter-facing experience",
  "Phone and desktop previews",
  "BIDALS operating layer beneath",
];

const brandViews = [
  { id: "phone", label: "Phone view", icon: Smartphone },
  { id: "desktop", label: "Desktop view", icon: Monitor },
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

function PhoneSupporterPreview({ theme }: { theme: BrandTheme }) {
  return (
    <article className={`home-brand-preview home-preview-theme-${theme.id} home-preview-phone`}>
      <div className={`home-supporter-phone home-theme-${theme.id}`}>
        <div className="home-supporter-phone-top">
          <span className="home-supporter-logo">{theme.initials}</span>
          <div>
            <span>{theme.organisation}</span>
            <strong>{theme.event}</strong>
          </div>
        </div>
        <div className="home-supporter-lot-card">
          <div className="home-supporter-lot-media" aria-hidden="true">
            <span />
          </div>
          <span>{theme.lotMeta}</span>
          <h3>{theme.lot}</h3>
          <p>{theme.story}</p>
          <div className="home-supporter-bid-row">
            <span>Current bid</span>
            <strong>{theme.currentBid}</strong>
          </div>
          <button type="button" tabIndex={-1}>
            {theme.nextBid}
          </button>
        </div>
        <div className="home-supporter-mini-grid">
          <span>
            <HeartHandshake size={15} aria-hidden="true" />
            {theme.donation}
          </span>
          <span>
            <Ticket size={15} aria-hidden="true" />
            {theme.raffle}
          </span>
        </div>
        <small>Powered by BIDALS</small>
      </div>
    </article>
  );
}

function DesktopSupporterPreview({ theme }: { theme: BrandTheme }) {
  return (
    <article className={`home-brand-preview home-preview-theme-${theme.id} home-preview-desktop`}>
      <div className={`home-supporter-desktop home-theme-${theme.id}`}>
        <header className="home-supporter-desktop-header">
          <div>
            <span className="home-supporter-logo">{theme.initials}</span>
            <div>
              <span>{theme.organisation}</span>
              <strong>{theme.event}</strong>
            </div>
          </div>
          <small>Powered by BIDALS</small>
        </header>
        <div className="home-supporter-desktop-grid">
          <section className="home-supporter-hero-lot">
            <div className="home-supporter-lot-media" aria-hidden="true">
              <span />
            </div>
            <span>{theme.lotMeta}</span>
            <h3>{theme.lot}</h3>
            <p>{theme.story}</p>
          </section>
          <aside className="home-supporter-bid-panel">
            <span>Current bid</span>
            <strong>{theme.currentBid}</strong>
            <button type="button" tabIndex={-1}>
              {theme.nextBid}
            </button>
            <div>
              <span>
                <HeartHandshake size={15} aria-hidden="true" />
                {theme.donation}
              </span>
              <span>
                <Ticket size={15} aria-hidden="true" />
                {theme.raffle}
              </span>
            </div>
          </aside>
        </div>
        <div className="home-supporter-auction-grid" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </article>
  );
}

function BrandPreviewStudio() {
  return (
    <div className="home-brand-studio">
      {brandThemes.map((theme, index) => (
        <input
          className={`home-brand-radio brand-theme-${theme.id}`}
          defaultChecked={index === 0}
          id={`brand-theme-${theme.id}`}
          key={theme.id}
          name="brand-theme"
          type="radio"
        />
      ))}
      {brandViews.map((view, index) => (
        <input
          className={`home-brand-radio brand-view-${view.id}`}
          defaultChecked={index === 0}
          id={`brand-view-${view.id}`}
          key={view.id}
          name="brand-view"
          type="radio"
        />
      ))}

      <div className="home-brand-studio-layout">
        <aside className="home-brand-control-panel" aria-label="Brand Preview Studio controls">
          <div className="home-brand-control-heading">
            <span className="home-eyebrow">Brand Preview Studio</span>
            <h3>See the bidder-facing experience shift by organisation.</h3>
          </div>

          <div className="home-theme-options" aria-label="Saved example organisation themes">
            {brandThemes.map((theme) => (
              <label className={`home-theme-option brand-theme-label-${theme.id}`} htmlFor={`brand-theme-${theme.id}`} key={theme.id}>
                <span className={`home-theme-swatch home-theme-${theme.id}`} aria-hidden="true">
                  {theme.initials}
                </span>
                <span>
                  <strong>{theme.organisation}</strong>
                  <small>{theme.event}</small>
                </span>
                <em>{theme.palette}</em>
              </label>
            ))}
          </div>

          <div className="home-view-toggle" aria-label="Preview view toggle">
            {brandViews.map((view) => {
              const Icon = view.icon;

              return (
                <label className={`home-view-option brand-view-label-${view.id}`} htmlFor={`brand-view-${view.id}`} key={view.id}>
                  <Icon size={16} aria-hidden="true" />
                  <span>{view.label}</span>
                </label>
              );
            })}
          </div>

          <div className="home-studio-meta">
            <span>
              <Palette size={16} aria-hidden="true" />
              Theme colour accents
            </span>
            <span>
              <ShieldCheck size={16} aria-hidden="true" />
              BIDALS operating layer
            </span>
          </div>
        </aside>

        <div className="home-brand-preview-stage" aria-label="Bidder-facing branded supporter preview">
          {brandThemes.map((theme) => (
            <PhoneSupporterPreview key={`phone-${theme.id}`} theme={theme} />
          ))}
          {brandThemes.map((theme) => (
            <DesktopSupporterPreview key={`desktop-${theme.id}`} theme={theme} />
          ))}
        </div>
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
        <div className="home-container home-brand-section">
          <div className="home-brand-copy">
            <span className="home-eyebrow">Brand-led deployment</span>
            <h2>Your organisation. Front and centre.</h2>
            <p>
              Show supporters an experience led by your event identity, organisation colours and campaign story — with
              BIDALS powering the operating layer underneath.
            </p>
            <div className="home-brand-tags" aria-label="Brand-led deployment elements">
              {brandStudioElements.map((signal) => (
                <span key={signal}>{signal}</span>
              ))}
            </div>
          </div>
          <BrandPreviewStudio />
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
