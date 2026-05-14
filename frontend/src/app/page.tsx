import Link from "next/link";
import { ArrowRight, LockKeyhole, RadioTower, ShieldCheck } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="landing-hero">
      <div className="hero-visual-layer" aria-hidden="true" />
      <div className="hero-feed-snapshot" aria-hidden="true">
        <div className="snapshot-row">
          <div className="snapshot-media" />
          <div className="snapshot-line" />
          <div className="snapshot-line short" />
        </div>
        <div className="snapshot-row">
          <div className="snapshot-media" />
          <div className="snapshot-line" />
          <div className="snapshot-line short" />
        </div>
        <div className="snapshot-row">
          <div className="snapshot-media" />
          <div className="snapshot-line" />
          <div className="snapshot-line short" />
        </div>
      </div>

      <section className="landing-content">
        <span className="eyebrow">Secure digital auctions</span>
        <h1>BIDALS</h1>
        <p>
          A mobile-first auction platform for browsing, selling, and bidding with
          server-authoritative validation and audit-ready activity records.
        </p>
        <div className="hero-actions">
          <Link className="primary-button" href="/auctions">
            Browse auctions
            <ArrowRight size={18} aria-hidden="true" />
          </Link>
          <Link className="secondary-button" href="/login">
            Login / Register
          </Link>
        </div>
        <div className="feed-grid" id="how-it-works">
          <div className="detail-panel">
            <ShieldCheck size={22} aria-hidden="true" />
            <strong>Server authority</strong>
            <p>Bid outcomes come from the backend transaction.</p>
          </div>
          <div className="detail-panel">
            <RadioTower size={22} aria-hidden="true" />
            <strong>Live ready</strong>
            <p>Polling now, WebSockets-ready later.</p>
          </div>
          <div className="detail-panel">
            <LockKeyhole size={22} aria-hidden="true" />
            <strong>Audit focused</strong>
            <p>Critical events are recorded for review.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
