import Link from "next/link";

export default function PricingPage() {
  return (
    <main className="page-shell">
      <section className="page-heading">
        <span className="eyebrow">Pricing</span>
        <h1>Plans for trusted digital auctions</h1>
        <p>
          BIDALS pricing is being prepared for launch. Start with a seller account
          and we will keep the platform focused on secure auction operations.
        </p>
      </section>

      <section className="detail-panel">
        <strong>MVP access</strong>
        <p>
          Create auctions, manage lots, accept backend-validated bids, review audit
          trails, and run seller fulfillment workflows.
        </p>
        <div className="button-row">
          <Link className="primary-button" href="/dashboard/auctions/new">
            Start Auction
          </Link>
          <Link className="secondary-button" href="/auctions">
            Browse auctions
          </Link>
        </div>
      </section>
    </main>
  );
}
