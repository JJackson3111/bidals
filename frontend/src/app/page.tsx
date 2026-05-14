import Link from "next/link";
import { ArrowRight, BarChart3, Bell, CheckCircle2, Clock, Package, Shield, TrendingUp, Users, Zap } from "lucide-react";

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

const launchSteps = [
  ["1", "Create auction", "Set the title, schedule, status, and seller-owned auction details."],
  ["2", "Add lots", "Prepare items with images, descriptions, starting prices, and bid increments."],
  ["3", "Open bidding", "Share the auction feed and let bidders participate from any device."],
  ["4", "Close with confidence", "Use backend-owned outcomes, audit logs, and fulfillment tracking after the auction."],
];

const liveLots = [
  { name: "Art Nouveau Print Collection", bid: "$1,850", time: "3h 45m", status: "Active" },
  { name: "Premium Wine Selection", bid: "$4,200", time: "1h 12m", status: "Ending soon" },
  { name: "Luxury Travel Package", bid: "$6,500", time: "6h 30m", status: "Active" },
  { name: "Signed Sports Memorabilia", bid: "$3,100", time: "45m", status: "Ending soon" },
  { name: "Tech Bundle Pro", bid: "$2,900", time: "4h 20m", status: "Active" },
  { name: "Designer Furniture Set", bid: "$5,750", time: "2h 55m", status: "Active" },
];

const activityItems = [
  { icon: TrendingUp, text: "New bid on Vintage Camera", time: "2m ago" },
  { icon: Users, text: "New bidder registered", time: "5m ago" },
  { icon: TrendingUp, text: "Bid increased on Watch Set", time: "8m ago" },
  { icon: Package, text: "New lot added to auction", time: "12m ago" },
];

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
            <article className="hero-lot-card">
              <div className="hero-lot-media">Premium Item</div>
              <div className="hero-lot-body">
                <h2>Vintage Camera Collection</h2>
                <div className="hero-lot-meta">
                  <div>
                    <span>Current bid</span>
                    <strong>$2,450</strong>
                  </div>
                  <div className="hero-lot-time">
                    <Clock size={16} aria-hidden="true" />
                    <span>2h 34m</span>
                  </div>
                </div>
                <div className="preview-bid-button">Place bid</div>
              </div>
            </article>

            <article className="hero-lot-card hero-lot-card-secondary">
              <div className="hero-lot-media">Premium Item</div>
              <div className="hero-lot-body">
                <h2>Designer Watch Set</h2>
                <div className="hero-lot-meta">
                  <div>
                    <span>Current bid</span>
                    <strong>$8,200</strong>
                  </div>
                  <div className="hero-lot-time">
                    <Clock size={16} aria-hidden="true" />
                    <span>5h 12m</span>
                  </div>
                </div>
                <div className="preview-bid-button">Place bid</div>
              </div>
            </article>
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
                  <div className="landing-icon-box">
                    <Icon size={24} aria-hidden="true" />
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
            {launchSteps.map(([number, title, description], index) => (
              <article className="landing-step" key={title}>
                <div className="landing-step-number">{number}</div>
                <h3>{title}</h3>
                <p>{description}</p>
                {index < launchSteps.length - 1 ? <span className="landing-step-line" aria-hidden="true" /> : null}
              </article>
            ))}
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
                <div className="auction-preview-media">Item</div>
                <div className="auction-preview-body">
                  <div>
                    <h3>{item.name}</h3>
                    <span className={`status-chip ${item.status === "Ending soon" ? "ending" : ""}`}>{item.status}</span>
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
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-section-muted">
        <div className="landing-container">
          <div className="landing-section-heading">
            <h2>Manage with clarity</h2>
            <p>Everything sellers and admins need to monitor auction health without extra noise.</p>
          </div>
          <div className="seller-preview-grid">
            <article className="seller-preview-panel">
              <div className="seller-preview-title">
                <div className="landing-icon-box compact">
                  <BarChart3 size={20} aria-hidden="true" />
                </div>
                <h3>Live analytics</h3>
              </div>
              <div className="seller-metric-list">
                <div>
                  <span>Total bids</span>
                  <strong>1,247</strong>
                </div>
                <div>
                  <span>Active bidders</span>
                  <strong>89</strong>
                </div>
                <div>
                  <span>Total value</span>
                  <strong>$124,580</strong>
                </div>
              </div>
            </article>

            <article className="seller-preview-panel">
              <div className="seller-preview-title">
                <div className="landing-icon-box compact">
                  <Bell size={20} aria-hidden="true" />
                </div>
                <h3>Live activity</h3>
              </div>
              <div className="activity-list">
                {activityItems.map((activity) => {
                  const Icon = activity.icon;
                  return (
                    <div className="activity-row" key={`${activity.text}-${activity.time}`}>
                      <div className="activity-icon">
                        <Icon size={16} aria-hidden="true" />
                      </div>
                      <div>
                        <span>{activity.text}</span>
                        <small>{activity.time}</small>
                      </div>
                    </div>
                  );
                })}
              </div>
            </article>
          </div>
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
