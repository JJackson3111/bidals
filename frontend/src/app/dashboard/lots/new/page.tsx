"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Save } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { LoadingState } from "@/components/StateViews";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import type { Auction, LotStatus } from "@/lib/types";

export default function NewLotPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [auctionId, setAuctionId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startingPrice, setStartingPrice] = useState("");
  const [reservePrice, setReservePrice] = useState("");
  const [bidIncrement, setBidIncrement] = useState("1.00");
  const [status, setStatus] = useState<LotStatus>("draft");
  const [externalImageUrl, setExternalImageUrl] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageAltText, setImageAltText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      try {
        const data = await api.getAuctions();
        setAuctions(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load auctions.");
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, []);

  const ownedAuctions = useMemo(() => {
    if (!user) return [];
    if (user.role === "admin") return auctions;
    return auctions.filter((auction) => auction.created_by === user.id);
  }, [auctions, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const lot = await api.createLot({
        auction: Number(auctionId),
        title,
        description,
        starting_price: startingPrice,
        reserve_price: reservePrice || null,
        bid_increment: bidIncrement,
        status,
        images: externalImageUrl ? [externalImageUrl] : [],
      });
      if (imageFile) {
        await api.uploadLotImage(lot.id, {
          file: imageFile,
          altText: imageAltText || title,
        });
      }
      router.push(`/lots/${lot.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create lot.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedRoute sellerOnly>
      <DashboardLayout title="Create lot">
        {isLoading ? <LoadingState label="Loading auctions" /> : null}
        {!isLoading ? (
          <form className="form-panel" onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-field">
                <label htmlFor="auction">Auction</label>
                <select id="auction" required value={auctionId} onChange={(event) => setAuctionId(event.target.value)}>
                  <option value="">Select auction</option>
                  {ownedAuctions.map((auction) => (
                    <option key={auction.id} value={auction.id}>{auction.title}</option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="title">Title</label>
                <input id="title" required value={title} onChange={(event) => setTitle(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="description">Description</label>
                <textarea id="description" value={description} onChange={(event) => setDescription(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="starting-price">Starting price</label>
                <span className="form-help">Current price starts here until the first accepted bid.</span>
                <input id="starting-price" inputMode="decimal" min="0" required step="0.01" type="number" value={startingPrice} onChange={(event) => setStartingPrice(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="reserve-price">Reserve price</label>
                <span className="form-help">Optional. Leave blank when the lot has no reserve.</span>
                <input id="reserve-price" inputMode="decimal" min="0" step="0.01" type="number" value={reservePrice} onChange={(event) => setReservePrice(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="bid-increment">Bid increment</label>
                <span className="form-help">The backend enforces this increment on every bid.</span>
                <input id="bid-increment" inputMode="decimal" min="0.01" required step="0.01" type="number" value={bidIncrement} onChange={(event) => setBidIncrement(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="status">Status</label>
                <select id="status" value={status} onChange={(event) => setStatus(event.target.value as LotStatus)}>
                  <option value="draft">Draft</option>
                  <option value="open">Open</option>
                  <option value="closed">Closed</option>
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="external-image">External image URL</label>
                <span className="form-help">Optional URL for CDN or object-storage hosted images.</span>
                <input id="external-image" type="url" value={externalImageUrl} onChange={(event) => setExternalImageUrl(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="image-file">Upload image</label>
                <span className="form-help">Local dev stores this under media; production should use object storage.</span>
                <input id="image-file" accept="image/*" type="file" onChange={(event) => setImageFile(event.target.files?.[0] ?? null)} />
              </div>
              <div className="form-field">
                <label htmlFor="image-alt">Image alt text</label>
                <input id="image-alt" value={imageAltText} onChange={(event) => setImageAltText(event.target.value)} />
              </div>
            </div>
            {error ? <div className="form-error" role="alert">{error}</div> : null}
            <button className="primary-button" disabled={isSubmitting} type="submit">
              <Save size={18} aria-hidden="true" />
              {isSubmitting ? "Creating" : "Create lot"}
            </button>
          </form>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}
