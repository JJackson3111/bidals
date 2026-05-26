import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  CalendarPlus,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  DollarSign,
  Eye,
  Gavel,
  ImagePlus,
  RadioTower,
  Shield,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { LandingLiveAnalytics } from "@/components/LandingLiveAnalytics";

const trustFeatures = [
  {
    icon: Shield,
    title: "Trusted bidding",
    description: "Secure accounts, strict permissions, and server-side bid validation keep every auction accountable.",
  },
  {
    icon: Zap,
    title: "Live event ready",
    description: "Mobile-first bidding, refreshable lot state, and a path to real-time auction activity.",
  },
  {
    icon: CheckCircle2,
    title: "Transparent outcomes",
    description: "Audit trails, winner records, and fulfillment workflows give sellers and admins a reliable record.",
  },
];

type LaunchStep = {
  number: string;
  title: string;
  description: string;
  cue: LucideIcon;
  cueKind: "calendar" | "images" | "radio" | "close";
  altCue?: LucideIcon;
};

const launchSteps: LaunchStep[] = [
  {
    number: "1",
    title: "Create auction",
    description: "Set the title, schedule, status, and seller-owned auction details.",
    cue: CalendarPlus,
    cueKind: "calendar",
  },
  {
    number: "2",
    title: "Add lots",
    description: "Prepare items with images, descriptions, starting prices, and bid increments.",
    cue: ImagePlus,
    cueKind: "images",
  },
  {
    number: "3",
    title: "Open bidding",
    description: "Share the auction feed and let bidders participate from any device.",
    cue: RadioTower,
    cueKind: "radio",
  },
  {
    number: "4",
    title: "Close with confidence",
    description: "Use backend-owned outcomes, audit logs, and fulfillment tracking after the auction.",
    cue: CheckCircle2,
    cueKind: "close",
    altCue: DollarSign,
  },
];

const heroLots = [
  {
    name: "Vintage Camera Collection",
    bid: "$2,450",
    time: "2h 34m",
    status: "Live",
    bidders: "12 bidders",
    watchers: "34 watching",
    activity: "3 bids in last hour",
    reserve: "Reserve met",
    mediaCount: "1/4",
    image: "/demo-lots/vintage-camera.jpg",
    variant: "camera",
  },
  {
    name: "Designer Watch Set",
    bid: "$8,200",
    time: "5h 12m",
    status: "Trending",
    bidders: "28 bidders",
    watchers: "91 watching",
    activity: "7 bids in last hour",
    reserve: "Verified seller",
    mediaCount: "1/6",
    image: "/demo-lots/designer-watch.jpg",
    variant: "watch",
  },
];

const liveLots = [
  {
    name: "Art Nouveau Print Collection",
    bid: "$1,850",
    time: "3h 45m",
    status: "Active",
    bidders: "14 bidders",
    watchers: "41 watching",
    activity: "4 bids in last hour",
    reserve: "Reserve met",
    mediaCount: "1/5",
    image: "/demo-lots/art-print.jpg",
    variant: "art",
  },
  {
    name: "Premium Wine Selection",
    bid: "$4,200",
    time: "1h 12m",
    status: "Ending soon",
    bidders: "22 bidders",
    watchers: "68 watching",
    activity: "9 bids in last hour",
    reserve: "Reserve met",
    mediaCount: "1/4",
    image: "/demo-lots/wine-selection.jpg",
    variant: "wine",
  },
  {
    name: "Luxury Travel Package",
    bid: "$6,500",
    time: "6h 30m",
    status: "Trending",
    bidders: "19 bidders",
    watchers: "77 watching",
    activity: "5 bids in last hour",
    reserve: "Verified seller",
    mediaCount: "1/6",
    image: "/demo-lots/travel-package.jpg",
    variant: "travel",
  },
  {
    name: "Signed Sports Memorabilia",
    bid: "$3,100",
    time: "45m",
    status: "Ending soon",
    bidders: "31 bidders",
    watchers: "112 watching",
    activity: "11 bids in last hour",
    reserve: "Reserve met",
    mediaCount: "1/3",
    image: "/demo-lots/sports-memorabilia.jpg",
    variant: "sports",
  },
  {
    name: "Tech Bundle Pro",
    bid: "$2,900",
    time: "4h 20m",
    status: "Active",
    bidders: "17 bidders",
    watchers: "55 watching",
    activity: "2 bids in last hour",
    reserve: "Verified seller",
    mediaCount: "1/5",
    image: "/demo-lots/tech-bundle.jpg",
    variant: "tech",
  },
  {
    name: "Designer Furniture Set",
    bid: "$5,750",
    time: "2h 55m",
    status: "Active",
    bidders: "24 bidders",
    watchers: "83 watching",
    activity: "6 bids in last hour",
    reserve: "Reserve met",
    mediaCount: "1/4",
    image: "/demo-lots/designer-furniture.jpg",
    variant: "furniture",
  },
];

function MediaPanel({ count, image, label, variant }: { count: string; image: string; label: string; variant: string }) {
  return (
    <>
      <div className={`media-art media-art-${variant}`} />
      <Image className="media-image" src={image} alt="" fill sizes="(min-width: 720px) 480px, 100vw" />
      <div className="media-overlay" />
      <span className="media-count">{count}</span>
      <span className="media-label">{label}</span>
      <div className="media-nav-hint" aria-hidden="true">
        <span>
          <ChevronLeft size={14} />
        </span>
        <span>
          <ChevronRight size={14} />
        </span>
      </div>
      <div className="media-dots" aria-hidden="true">
        <span className="active" />
        <span />
        <span />
      </div>
    </>
  );
}

function StatusBadge({ status }: { status: string }) {
  const statusClass = status === "Ending soon" ? "ending" : status === "Trending" ? "trending" : "";
  return (
    <span className={`status-chip ${statusClass}`}>
      <span className="live-dot" aria-hidden="true" />
      {status}
    </span>
  );
}

export default function LandingPage() {
  return (
    <main className="landing-page">
      <section className="landing-hero">
        <div className="landing-container">
          <div className="landing-hero-copy">
            <span className="eyebrow landing-eyebrow">Secure digital auctions</span>
            <h1>Power every bid.</h1>
            <p className="landing-lede">
              Run professional auctions with confidence. Create events, manage lots, and power live bidding from one
              secure platform built around backend-owned auction truth.
            </p>
            <div className="landing-actions">
              <Link className="primary-button landing-button" href="/dashboard/auctions/new">
                Start an auction
                <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <Link className="secondary-button landing-button" href="/auctions">
                Browse auctions
              </Link>
            </div>
          </div>

          <div className="landing-hero-preview" aria-hidden="true">
            {heroLots.map((lot) => (
              <article className="hero-lot-card" key={lot.name}>
                <div className="hero-lot-media media-panel">
                  <MediaPanel count={lot.mediaCount} image={lot.image} label={lot.name} variant={lot.variant} />
                </div>
                <div className="hero-lot-body">
                  <div className="card-title-row">
                    <h2>{lot.name}</h2>
                    <StatusBadge status={lot.status} />
                  </div>
                  <div className="hero-lot-meta">
                    <div>
                      <span>Current bid</span>
                      <strong>{lot.bid}</strong>
                    </div>
                    <div className="hero-lot-time">
                      <Clock size={16} aria-hidden="true" />
                      <span>{lot.time}</span>
                    </div>
                  </div>
                  <div className="lot-signal-grid">
                    <span>
                      <Users size={14} aria-hidden="true" />
                      {lot.bidders}
                    </span>
                    <span>
                      <Eye size={14} aria-hidden="true" />
                      {lot.watchers}
                    </span>
                    <span>
                      <TrendingUp size={14} aria-hidden="true" />
                      {lot.activity}
                    </span>
                    <span>
                      <BadgeCheck size={14} aria-hidden="true" />
                      {lot.reserve}
                    </span>
                  </div>
                  <div className="preview-bid-button">Place bid</div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-container">
          <div className="landing-card-grid">
            {trustFeatures.map((feature) => {
              const Icon = feature.icon;
              return (
                <article className="landing-feature-card" key={feature.title}>
                  <div className="feature-icon-mark">
                    <Icon className="feature-icon-svg" size={30} strokeWidth={1.9} aria-hidden="true" />
                  </div>
                  <h2>{feature.title}</h2>
                  <p>{feature.description}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="landing-section landing-section-muted" id="how-it-works">
        <div className="landing-container">
          <div className="landing-section-heading">
            <h2>Simple to launch</h2>
            <p>From creation to completion in a clean, governed workflow.</p>
          </div>
          <div className="landing-steps-grid">
            {launchSteps.map((step, index) => {
              const CueIcon = step.cue;
              const AltCue = step.altCue;
              return (
                <article className="landing-step" key={step.title}>
                  <div className="landing-step-number">{step.number}</div>
                  <div className={`landing-step-cue cue-${step.cueKind}`}>
                    {step.cueKind !== "images" ? (
                      <CueIcon className="cue-icon cue-primary" size={22} strokeWidth={1.9} aria-hidden="true" />
                    ) : null}
                    {AltCue ? <AltCue className="cue-icon cue-secondary" size={22} strokeWidth={1.9} aria-hidden="true" /> : null}
                    {step.cueKind === "images" ? (
                      <span className="cue-photo-stack" aria-hidden="true">
                        <i className="photo-card-one" />
                        <i className="photo-card-two" />
                        <i className="photo-card-three" />
                      </span>
                    ) : null}
                    {step.cueKind === "radio" ? (
                      <>
                        <span className="cue-signal cue-signal-left" aria-hidden="true" />
                        <span className="cue-signal cue-signal-right" aria-hidden="true" />
                        <span className="cue-live-dot" aria-hidden="true" />
                      </>
                    ) : null}
                  </div>
                  <h3>{step.title}</h3>
                  <p>{step.description}</p>
                  {index < launchSteps.length - 1 ? <span className="landing-step-line" aria-hidden="true" /> : null}
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-container">
          <div className="landing-section-heading">
            <h2>Live auctions that engage</h2>
            <p>Social-style browsing for bidders, serious controls for sellers.</p>
          </div>
          <div className="landing-live-grid">
            {liveLots.map((item) => (
              <article className="auction-preview-card" key={item.name}>
                <div className="auction-preview-media media-panel">
                  <MediaPanel count={item.mediaCount} image={item.image} label={item.name} variant={item.variant} />
                </div>
                <div className="auction-preview-body">
                  <div className="card-title-row">
                    <h3>{item.name}</h3>
                    <StatusBadge status={item.status} />
                  </div>
                  <div className="auction-preview-footer">
                    <div>
                      <span>Current bid</span>
                      <strong>{item.bid}</strong>
                    </div>
                    <div className="hero-lot-time">
                      <Clock size={14} aria-hidden="true" />
                      <span>{item.time}</span>
                    </div>
                  </div>
                  <div className="lot-signal-grid compact">
                    <span>
                      <Users size={13} aria-hidden="true" />
                      {item.bidders}
                    </span>
                    <span>
                      <Eye size={13} aria-hidden="true" />
                      {item.watchers}
                    </span>
                    <span>
                      <Gavel size={13} aria-hidden="true" />
                      {item.activity}
                    </span>
                    <span>
                      <BadgeCheck size={13} aria-hidden="true" />
                      {item.reserve}
                    </span>
                  </div>
                  <div className="card-quick-actions" aria-label={`Quick actions for ${item.name}`}>
                    <Link href="/auctions" className="quick-action">
                      Watch
                    </Link>
                    <Link href="/auctions" className="quick-action">
                      Preview
                    </Link>
                    <Link href="/auctions" className="quick-action primary">
                      Quick bid
                    </Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-section-muted">
        <div className="landing-container seller-preview-container">
          <div className="landing-section-heading seller-preview-heading">
            <h2>Manage with clarity</h2>
            <p>Everything sellers and admins need to monitor auction health without extra noise.</p>
          </div>
          <LandingLiveAnalytics />
        </div>
      </section>

      <section className="landing-final-cta">
        <div className="landing-container">
          <h2>Modern auction management built for real events.</h2>
          <Link className="primary-button landing-button" href="/dashboard/auctions/new">
            Launch your next auction
            <ArrowRight size={18} aria-hidden="true" />
          </Link>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-container landing-footer-inner">
          <strong>BIDALS</strong>
          <nav aria-label="Footer navigation">
            <Link href="/#how-it-works">How It Works</Link>
            <Link href="/pricing">Pricing</Link>
            <Link href="/login">Login</Link>
            <Link href="/auctions">Browse</Link>
          </nav>
        </div>
      </footer>
    </main>
  );
}
