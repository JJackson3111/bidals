import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  CheckCircle2,
  Gauge,
  HeartHandshake,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  Ticket,
  Trophy,
} from "lucide-react";

type MarketingLink = {
  href: string;
  label: string;
};

type MarketingHeroProps = {
  eyebrow: string;
  title: string;
  description: string;
  highlights?: string[];
  primaryCta?: MarketingLink;
  secondaryCta?: MarketingLink;
};

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
};

export type MarketingFeature = {
  eyebrow?: string;
  title: string;
  description: string;
  icon?: LucideIcon;
  items?: string[];
};

type FeatureGridProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  features: MarketingFeature[];
};

type TrustSectionProps = {
  eyebrow?: string;
  title: string;
  description: string;
  items: string[];
};

type MarketingCTAProps = {
  title: string;
  description: string;
  primaryCta?: MarketingLink;
  secondaryCta?: MarketingLink;
};

type MarketingSectionProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  tone?: "light" | "dark" | "muted";
  children: ReactNode;
};

type MarketingMetric = {
  label: string;
  value: string;
  detail?: string;
};

type MarketingDashboardRow = {
  label: string;
  value: string;
  status?: "live" | "ready" | "review";
};

type MarketingDashboardPanelProps = {
  eyebrow?: string;
  title: string;
  metrics: MarketingMetric[];
  rows: MarketingDashboardRow[];
  note?: string;
  dark?: boolean;
};

type PhoneVariant = "auction" | "raffle" | "donation";

type MarketingPhoneMockupProps = {
  variant: PhoneVariant;
  className?: string;
};

const defaultPrimaryCta = { href: "/book-demo", label: "Book a demo" };
const defaultSecondaryCta = { href: "/features", label: "Explore features" };

const phoneMockups: Record<
  PhoneVariant,
  {
    icon: LucideIcon;
    eyebrow: string;
    title: string;
    context: string;
    metricLabel: string;
    metricValue: string;
    chips: string[];
    primaryAction: string;
    rows: MarketingDashboardRow[];
    footer: string;
  }
> = {
  auction: {
    icon: Trophy,
    eyebrow: "Live auction lot",
    title: "Chef's table for eight",
    context: "Gala auction",
    metricLabel: "Current bid",
    metricValue: "GBP 1,850",
    chips: ["Watchlist active", "Closing control on"],
    primaryAction: "Quick bid GBP 1,900",
    rows: [
      { label: "Bid accepted", value: "Server record", status: "live" },
      { label: "Bid history", value: "12 entries", status: "ready" },
      { label: "Extension rule", value: "Armed", status: "review" },
    ],
    footer: "Illustrative mobile bidding UI",
  },
  raffle: {
    icon: Ticket,
    eyebrow: "Raffle flow",
    title: "Mystery grand prize",
    context: "Prize reveal locked",
    metricLabel: "Ticket basket",
    metricValue: "12 entries",
    chips: ["Hidden reveal", "Draw review"],
    primaryAction: "Reserve tickets",
    rows: [
      { label: "Ticket sell-through", value: "68%", status: "live" },
      { label: "Raffle income", value: "GBP 7.4k", status: "ready" },
      { label: "Winner draw", value: "Governed", status: "review" },
    ],
    footer: "Illustrative raffle workflow UI",
  },
  donation: {
    icon: HeartHandshake,
    eyebrow: "Donation form",
    title: "Children's appeal",
    context: "Event giving",
    metricLabel: "Your gift",
    metricValue: "GBP 50",
    chips: ["One-off", "Monthly option"],
    primaryAction: "Complete donation",
    rows: [
      { label: "Impact", value: "10 meals funded", status: "live" },
      { label: "Recognition", value: "Optional", status: "ready" },
      { label: "Campaign total", value: "Updating", status: "review" },
    ],
    footer: "Illustrative donation UI",
  },
};

function MarketingActions({
  primaryCta = defaultPrimaryCta,
  secondaryCta = defaultSecondaryCta,
}: {
  primaryCta?: MarketingLink;
  secondaryCta?: MarketingLink;
}) {
  return (
    <div className="marketing-actions">
      <Link className="primary-button marketing-button" href={primaryCta.href}>
        {primaryCta.label}
        <ArrowRight size={18} aria-hidden="true" />
      </Link>
      <Link className="secondary-button marketing-button" href={secondaryCta.href}>
        {secondaryCta.label}
      </Link>
    </div>
  );
}

function MarketingHeroScene() {
  return (
    <div className="marketing-hero-scene" aria-label="BIDALS product preview">
      <MarketingPhoneMockup variant="auction" className="marketing-hero-phone" />
      <div className="marketing-hero-dashboard">
        <div className="marketing-scene-header">
          <Image className="marketing-scene-logo" src="/bidals-logo-mark.png" alt="" width={52} height={52} priority />
          <div>
            <span>Operating view</span>
            <strong>Spring appeal</strong>
          </div>
        </div>
        <div className="marketing-scene-progress" aria-hidden="true">
          <span />
        </div>
        <div className="marketing-scene-metrics">
          <div>
            <span>Raised</span>
            <strong>86%</strong>
          </div>
          <div>
            <span>Lots</span>
            <strong>42</strong>
          </div>
          <div>
            <span>Gifts</span>
            <strong>318</strong>
          </div>
        </div>
        <p>Illustrative dashboard UI for event health, bidder activity and donation momentum.</p>
      </div>
      <div className="marketing-scene-float marketing-scene-float-top">
        <ShieldCheck size={17} aria-hidden="true" />
        <span>Server accepted</span>
      </div>
      <div className="marketing-scene-float marketing-scene-float-bottom">
        <Gauge size={17} aria-hidden="true" />
        <span>Event health live</span>
      </div>
    </div>
  );
}

export function MarketingHero({ eyebrow, title, description, highlights = [], primaryCta, secondaryCta }: MarketingHeroProps) {
  return (
    <section className="marketing-hero">
      <div className="marketing-container marketing-hero-grid">
        <div className="marketing-hero-content">
          <span className="eyebrow marketing-eyebrow">{eyebrow}</span>
          <h1>{title}</h1>
          <p>{description}</p>
          <MarketingActions primaryCta={primaryCta} secondaryCta={secondaryCta} />
          {highlights.length > 0 ? (
            <ul className="marketing-hero-highlights" aria-label="Platform highlights">
              {highlights.map((item) => (
                <li key={item}>
                  <CheckCircle2 size={16} aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <MarketingHeroScene />
      </div>
    </section>
  );
}

export function PageHeader({ eyebrow, title, description }: PageHeaderProps) {
  return (
    <section className="marketing-page-header">
      <div className="marketing-container">
        <span className="eyebrow marketing-eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </section>
  );
}

export function MarketingSection({ eyebrow, title, description, tone = "light", children }: MarketingSectionProps) {
  return (
    <section className={`marketing-section marketing-section-${tone}`}>
      <div className="marketing-container">
        <div className="marketing-section-heading">
          {eyebrow ? <span className="eyebrow marketing-eyebrow">{eyebrow}</span> : null}
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {children}
      </div>
    </section>
  );
}

export function FeatureGrid({ eyebrow, title, description, features }: FeatureGridProps) {
  return (
    <section className="marketing-section marketing-section-light">
      <div className="marketing-container">
        <div className="marketing-section-heading">
          {eyebrow ? <span className="eyebrow marketing-eyebrow">{eyebrow}</span> : null}
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        <div className="marketing-feature-grid">
          {features.map((feature) => {
            const Icon = feature.icon;

            return (
              <article className="marketing-feature-card" key={feature.title}>
                <div className="marketing-feature-card-top">
                  {Icon ? (
                    <span className="marketing-feature-icon">
                      <Icon size={20} aria-hidden="true" />
                    </span>
                  ) : null}
                  {feature.eyebrow ? <span>{feature.eyebrow}</span> : null}
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
                {feature.items ? (
                  <ul>
                    {feature.items.map((item) => (
                      <li key={item}>
                        <CheckCircle2 size={15} aria-hidden="true" />
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export function MarketingPhoneMockup({ variant, className }: MarketingPhoneMockupProps) {
  const config = phoneMockups[variant];
  const Icon = config.icon;
  const classes = ["marketing-phone", `marketing-phone-${variant}`, className].filter(Boolean).join(" ");

  return (
    <article className={classes} aria-label={config.footer}>
      <div className="marketing-phone-frame">
        <div className="marketing-phone-speaker" aria-hidden="true" />
        <div className="marketing-phone-screen">
          <div className="marketing-phone-hero">
            <div>
              <span>{config.eyebrow}</span>
              <h3>{config.title}</h3>
              <p>{config.context}</p>
            </div>
            <span className="marketing-phone-icon">
              <Icon size={20} aria-hidden="true" />
            </span>
          </div>
          <div className="marketing-phone-metric">
            <span>{config.metricLabel}</span>
            <strong>{config.metricValue}</strong>
          </div>
          <div className="marketing-phone-chips">
            {config.chips.map((chip) => (
              <span key={chip}>{chip}</span>
            ))}
          </div>
          <button className="marketing-phone-action" type="button" tabIndex={-1}>
            {config.primaryAction}
          </button>
          <div className="marketing-phone-activity">
            {config.rows.map((row) => (
              <div className="marketing-phone-row" key={row.label}>
                <span className={`marketing-status-dot marketing-status-${row.status ?? "ready"}`} aria-hidden="true" />
                <span>{row.label}</span>
                <strong>{row.value}</strong>
              </div>
            ))}
          </div>
          <small>{config.footer}</small>
        </div>
      </div>
    </article>
  );
}

export function MarketingDashboardPanel({
  eyebrow = "Illustrative operating view",
  title,
  metrics,
  rows,
  note,
  dark = false,
}: MarketingDashboardPanelProps) {
  return (
    <article className={`marketing-dashboard-panel ${dark ? "marketing-dashboard-panel-dark" : ""}`}>
      <div className="marketing-dashboard-header">
        <span>{eyebrow}</span>
        <h3>{title}</h3>
      </div>
      <div className="marketing-dashboard-metrics">
        {metrics.map((metric) => (
          <div key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            {metric.detail ? <small>{metric.detail}</small> : null}
          </div>
        ))}
      </div>
      <div className="marketing-dashboard-rows">
        {rows.map((row) => (
          <div className="marketing-dashboard-row" key={row.label}>
            <span className={`marketing-status-dot marketing-status-${row.status ?? "ready"}`} aria-hidden="true" />
            <span>{row.label}</span>
            <strong>{row.value}</strong>
          </div>
        ))}
      </div>
      {note ? <p className="marketing-dashboard-note">{note}</p> : null}
    </article>
  );
}

export function MarketingMetricStrip({ metrics, note }: { metrics: MarketingMetric[]; note?: string }) {
  return (
    <div className="marketing-metric-strip">
      {metrics.map((metric) => (
        <div className="marketing-metric-item" key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
          {metric.detail ? <small>{metric.detail}</small> : null}
        </div>
      ))}
      {note ? <p>{note}</p> : null}
    </div>
  );
}

export function TrustSection({ eyebrow = "Trust layer", title, description, items }: TrustSectionProps) {
  return (
    <section className="marketing-section marketing-section-strong">
      <div className="marketing-container marketing-trust-layout">
        <div>
          <span className="marketing-trust-icon">
            <LockKeyhole size={22} aria-hidden="true" />
          </span>
          <span className="eyebrow marketing-eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <ul className="marketing-trust-list">
          {items.map((item) => (
            <li key={item}>
              <CheckCircle2 className="marketing-trust-check" size={18} aria-hidden="true" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function MarketingCTA({ title, description, primaryCta, secondaryCta }: MarketingCTAProps) {
  return (
    <section className="marketing-cta">
      <div className="marketing-container">
        <span className="marketing-cta-mark">
          <Sparkles size={18} aria-hidden="true" />
        </span>
        <h2>{title}</h2>
        <p>{description}</p>
        <MarketingActions primaryCta={primaryCta} secondaryCta={secondaryCta} />
      </div>
    </section>
  );
}

export function MarketingFooter() {
  const footerGroups = [
    {
      title: "Platform",
      links: [
        { href: "/features", label: "Features" },
        { href: "/auctions", label: "Auctions" },
        { href: "/raffles", label: "Raffles" },
        { href: "/donations", label: "Donations" },
      ],
    },
    {
      title: "Company",
      links: [
        { href: "/pricing", label: "Pricing" },
        { href: "/book-demo", label: "Book demo" },
        { href: "/contact", label: "Contact" },
      ],
    },
    {
      title: "Legal",
      links: [
        { href: "/security", label: "Security" },
        { href: "/contact", label: "Data enquiries" },
      ],
    },
  ];

  return (
    <footer className="marketing-footer">
      <div className="marketing-container marketing-footer-inner">
        <div className="marketing-footer-brand">
          <strong>BIDALS</strong>
          <p>Modern fundraising operating system for premium, mobile-first campaigns.</p>
        </div>
        <nav aria-label="Marketing footer navigation">
          {footerGroups.map((group) => (
            <div className="marketing-footer-group" key={group.title}>
              <span>{group.title}</span>
              {group.links.map((link) => (
                <Link key={link.href + link.label} href={link.href}>
                  {link.label}
                </Link>
              ))}
            </div>
          ))}
        </nav>
      </div>
    </footer>
  );
}
