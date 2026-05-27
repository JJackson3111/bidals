import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";

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
  children: ReactNode;
};

const defaultPrimaryCta = { href: "/book-demo", label: "Book a demo" };
const defaultSecondaryCta = { href: "/features", label: "Explore features" };

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
    <div className="marketing-hero-scene" aria-hidden="true">
      <div className="marketing-scene-panel marketing-scene-panel-main">
        <div className="marketing-scene-header">
          <Image className="marketing-scene-logo" src="/bidals-logo-mark.png" alt="" width={52} height={52} priority />
          <div>
            <span>Live event</span>
            <strong>Spring appeal</strong>
          </div>
        </div>
        <div className="marketing-scene-progress">
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
      </div>
      <div className="marketing-scene-panel marketing-scene-panel-bid">
        <span>New secure bid</span>
        <strong>Server accepted</strong>
      </div>
      <div className="marketing-scene-panel marketing-scene-panel-gift">
        <span>Supporter giving</span>
        <strong>Mobile first</strong>
      </div>
    </div>
  );
}

export function MarketingHero({ eyebrow, title, description, highlights = [], primaryCta, secondaryCta }: MarketingHeroProps) {
  return (
    <section className="marketing-hero">
      <MarketingHeroScene />
      <div className="marketing-container marketing-hero-content">
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

export function MarketingSection({ eyebrow, title, description, children }: MarketingSectionProps) {
  return (
    <section className="marketing-section">
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
    <section className="marketing-section">
      <div className="marketing-container">
        <div className="marketing-section-heading">
          {eyebrow ? <span className="eyebrow marketing-eyebrow">{eyebrow}</span> : null}
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        <div className="marketing-feature-grid">
          {features.map((feature) => (
            <article className="marketing-feature-card" key={feature.title}>
              {feature.eyebrow ? <span>{feature.eyebrow}</span> : null}
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
          ))}
        </div>
      </div>
    </section>
  );
}

export function TrustSection({ eyebrow = "Trust layer", title, description, items }: TrustSectionProps) {
  return (
    <section className="marketing-section marketing-section-strong">
      <div className="marketing-container marketing-trust-layout">
        <div>
          <span className="eyebrow marketing-eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <ul className="marketing-trust-list">
          {items.map((item) => (
            <li key={item}>
              <CheckCircle2 size={18} aria-hidden="true" />
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
        <h2>{title}</h2>
        <p>{description}</p>
        <MarketingActions primaryCta={primaryCta} secondaryCta={secondaryCta} />
      </div>
    </section>
  );
}

export function MarketingFooter() {
  return (
    <footer className="marketing-footer">
      <div className="marketing-container marketing-footer-inner">
        <strong>BIDALS</strong>
        <nav aria-label="Marketing footer navigation">
          <Link href="/features">Features</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/security">Security</Link>
          <Link href="/auctions">Auctions</Link>
          <Link href="/raffles">Raffles</Link>
          <Link href="/donations">Donations</Link>
          <Link href="/contact">Contact</Link>
        </nav>
      </div>
    </footer>
  );
}
