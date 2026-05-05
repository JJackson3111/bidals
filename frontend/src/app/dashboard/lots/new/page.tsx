"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
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
  const submitInFlightRef = useRef(false);
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
  const [imagePreviewUrl, setImagePreviewUrl] = useState("");
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

  const selectedAuction = useMemo(
    () => ownedAuctions.find((auction) => String(auction.id) === auctionId) ?? null,
    [auctionId, ownedAuctions],
  );
  const openStatusAllowed = selectedAuction?.status === "live" || selectedAuction?.status === "scheduled";
  const statusHelp = selectedAuction
    ? selectedAuction.status === "live"
      ? "This lot can accept bids only while the auction is live and the backend accepts the bid."
      : selectedAuction.status === "scheduled"
        ? "Lots only become bid-open when the auction is live."
        : "This auction is not live. Keep the lot as draft or closed until the auction can accept bids."
    : "Select an auction before choosing lot availability. Lots only become bid-open when the auction is live.";
  const previewUrl = imagePreviewUrl || externalImageUrl;
  const submitDisabled = isSubmitting || !auctionId;

  useEffect(() => {
    if (status === "open" && selectedAuction && !openStatusAllowed) {
      setStatus("draft");
    }
  }, [openStatusAllowed, selectedAuction, status]);

  useEffect(() => {
    if (!imageFile) {
      setImagePreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(imageFile);
    setImagePreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [imageFile]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitInFlightRef.current) return;

    submitInFlightRef.current = true;
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
        try {
          await api.uploadLotImage(lot.id, {
            file: imageFile,
            altText: imageAltText || title,
          });
        } catch {
          router.push(`/dashboard/lots/${lot.id}/edit?imageUpload=failed`);
          return;
        }
      }
      router.push(`/lots/${lot.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create lot.");
    } finally {
      submitInFlightRef.current = false;
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedRoute sellerOnly>
      <DashboardLayout title="Create lot">
        {isLoading ? <LoadingState label="Loading auctions" /> : null}
        {!isLoading ? (
          <form className="form-panel" onSubmit={handleSubmit} aria-busy={isSubmitting}>
            {previewUrl ? (
              <div
                className="form-image-preview"
                style={{ backgroundImage: `url("${previewUrl}")` }}
                role="img"
                aria-label={imageAltText || title || "Lot image preview"}
              />
            ) : null}
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
                  <option value="open" disabled={!openStatusAllowed}>Open</option>
                  <option value="closed">Closed</option>
                </select>
                <span className="form-help">{statusHelp}</span>
              </div>
              <div className="form-field">
                <label htmlFor="external-image">External image URL</label>
                <span className="form-help">Optional URL for CDN or object-storage hosted images.</span>
                <input id="external-image" type="url" value={externalImageUrl} onChange={(event) => setExternalImageUrl(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="image-file">Upload image</label>
                <span className="form-help">Local dev stores this under media; production should use object storage.</span>
                <input
                  id="image-file"
                  accept="image/*"
                  disabled={isSubmitting}
                  type="file"
                  onChange={(event) => setImageFile(event.target.files?.[0] ?? null)}
                />
              </div>
              <div className="form-field">
                <label htmlFor="image-alt">Image alt text</label>
                <input id="image-alt" value={imageAltText} onChange={(event) => setImageAltText(event.target.value)} />
              </div>
            </div>
            {error ? <div className="form-error" role="alert">{error}</div> : null}
            <button className="primary-button" disabled={submitDisabled} type="submit">
              <Save size={18} aria-hidden="true" />
              {isSubmitting ? "Creating" : "Create lot"}
            </button>
          </form>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}
