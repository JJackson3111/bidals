"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowDown, ArrowUp, Save, Trash2, Upload } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ErrorState, LoadingState } from "@/components/StateViews";
import { api, ApiError } from "@/lib/api";
import { getLotPrimaryImageUrl } from "@/lib/format";
import type { Bid, Lot, LotStatus, UpdateLotInput } from "@/lib/types";

export default function EditLotPage() {
  const params = useParams<{ id: string }>();
  const submitInFlightRef = useRef(false);
  const [lot, setLot] = useState<Lot | null>(null);
  const [bids, setBids] = useState<Bid[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startingPrice, setStartingPrice] = useState("");
  const [reservePrice, setReservePrice] = useState("");
  const [bidIncrement, setBidIncrement] = useState("");
  const [lotStatus, setLotStatus] = useState<LotStatus>("draft");
  const [externalImageUrl, setExternalImageUrl] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState("");
  const [imageAltText, setImageAltText] = useState("");
  const [imageActionId, setImageActionId] = useState<number | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function uploadErrorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      return err.message;
    }
    if (err instanceof Error) {
      return err.message;
    }
    return "Image upload failed. The lot changes were saved.";
  }

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const lotData = await api.getLot(params.id);
        const bidData = await api.getBidHistory(lotData.id).catch(() => [] as Bid[]);
        setLot(lotData);
        setBids(bidData);
        setTitle(lotData.title);
        setDescription(lotData.description);
        setStartingPrice(lotData.starting_price);
        setReservePrice(lotData.reserve_price ?? "");
        setBidIncrement(lotData.bid_increment);
        setLotStatus(lotData.status);
        setExternalImageUrl(lotData.images?.[0] ?? "");
        setImageAltText(lotData.title);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load lot.");
      } finally {
        setIsLoading(false);
      }
    }

    if (params.id) load();
  }, [params.id]);

  const hasAcceptedBids = useMemo(() => bids.some((bid) => bid.status === "accepted"), [bids]);
  const primaryImageUrl = lot ? getLotPrimaryImageUrl(lot) : null;
  const previewImageUrl = imagePreviewUrl || externalImageUrl || primaryImageUrl;
  const openStatusAllowed = lot?.auction_status === "live" || lot?.auction_status === "scheduled";
  const statusHelp = lot
    ? lot.auction_status === "live"
      ? "This lot can accept bids only while the auction is live and the backend accepts the bid."
      : lot.auction_status === "scheduled"
        ? "Lots only become bid-open when the auction is live."
        : "This auction is not live. Keep the lot as draft or closed until the auction can accept bids."
    : "Lots only become bid-open when the auction is live.";
  const sortedImages = useMemo(
    () => [...(lot?.uploaded_images ?? [])].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id),
    [lot?.uploaded_images],
  );

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    if (query.get("imageUpload") === "failed") {
      setImageError(
        query.get("message") || "Lot was created, but the image upload did not finish. Upload the image again here.",
      );
    }
  }, []);

  useEffect(() => {
    if (lotStatus === "open" && lot && !openStatusAllowed) {
      setLotStatus("draft");
    }
  }, [lot, lotStatus, openStatusAllowed]);

  useEffect(() => {
    if (!imageFile) {
      setImagePreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(imageFile);
    setImagePreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [imageFile]);

  async function refreshLot() {
    const lotData = await api.getLot(params.id);
    setLot(lotData);
    setExternalImageUrl(lotData.images?.[0] ?? "");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!lot) return;
    if (submitInFlightRef.current) return;

    submitInFlightRef.current = true;
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    const payload: UpdateLotInput = {
      title,
      description,
      reserve_price: reservePrice || null,
      status: lotStatus,
      images: externalImageUrl ? [externalImageUrl] : [],
    };

    if (!hasAcceptedBids) {
      payload.starting_price = startingPrice;
      payload.bid_increment = bidIncrement;
    }

    try {
      const savedLot = await api.updateLot(lot.id, payload);
      if (imageFile) {
        try {
          await api.uploadLotImage(savedLot.id, {
            file: imageFile,
            altText: imageAltText,
          });
          setImageFile(null);
          setImagePreviewUrl("");
          setImageError(null);
        } catch (uploadErr) {
          setLot(savedLot);
          setImageError(uploadErrorMessage(uploadErr));
          setSuccess("Lot details were saved, but the image did not upload.");
          return;
        }
      }
      await refreshLot();
      setSuccess(imageFile ? "Lot saved and image uploaded." : "Lot saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to save lot.");
    } finally {
      submitInFlightRef.current = false;
      setIsSubmitting(false);
    }
  }

  async function handleDeleteImage(imageId: number) {
    if (!lot) return;
    setImageError(null);
    setSuccess(null);
    setImageActionId(imageId);

    try {
      await api.deleteLotImage(lot.id, imageId);
      await refreshLot();
      setSuccess("Image deleted.");
    } catch (err) {
      setImageError(err instanceof ApiError ? err.message : "Unable to delete image.");
    } finally {
      setImageActionId(null);
    }
  }

  async function handleMoveImage(imageId: number, direction: -1 | 1) {
    if (!lot) return;
    const currentIndex = sortedImages.findIndex((image) => image.id === imageId);
    const nextIndex = currentIndex + direction;
    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= sortedImages.length) return;

    const nextImages = [...sortedImages];
    const [moved] = nextImages.splice(currentIndex, 1);
    nextImages.splice(nextIndex, 0, moved);
    setImageError(null);
    setSuccess(null);
    setImageActionId(imageId);

    try {
      const reordered = await api.reorderLotImages(
        lot.id,
        nextImages.map((image, index) => ({ id: image.id, sort_order: index + 1 })),
      );
      setLot({ ...lot, uploaded_images: reordered });
      setSuccess("Image order saved.");
    } catch (err) {
      setImageError(err instanceof ApiError ? err.message : "Unable to reorder images.");
    } finally {
      setImageActionId(null);
    }
  }

  return (
    <ProtectedRoute sellerOnly>
      <DashboardLayout title="Edit lot">
        {isLoading ? <LoadingState label="Loading lot" /> : null}
        {!isLoading && error ? <ErrorState message={error} /> : null}
        {!isLoading && !error && lot ? (
          <form className="form-panel" onSubmit={handleSubmit} aria-busy={isSubmitting}>
            {previewImageUrl ? (
              <div className="form-image-preview" style={{ backgroundImage: `url("${previewImageUrl}")` }} role="img" aria-label={imageAltText || lot.title} />
            ) : null}
            <section className="image-manager" aria-label="Lot images">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">Images</span>
                  <h2>Manage lot images</h2>
                </div>
              </div>
              {sortedImages.length === 0 ? (
                <p>No uploaded images yet.</p>
              ) : (
                <div className="image-manager-grid">
                  {sortedImages.map((image, index) => (
                    <article className="image-manager-item" key={image.id}>
                      <div
                        aria-label={image.alt_text || lot.title}
                        className="image-manager-thumb"
                        role="img"
                        style={{ backgroundImage: `url("${image.image_url}")` }}
                      />
                      <div>
                        <strong>{image.alt_text || "Lot image"}</strong>
                        <span>Order {index + 1}</span>
                      </div>
                      <div className="image-manager-actions">
                        <button
                          aria-label="Move image up"
                          className="icon-button"
                          disabled={index === 0 || imageActionId === image.id}
                          onClick={() => handleMoveImage(image.id, -1)}
                          type="button"
                        >
                          <ArrowUp size={17} aria-hidden="true" />
                        </button>
                        <button
                          aria-label="Move image down"
                          className="icon-button"
                          disabled={index === sortedImages.length - 1 || imageActionId === image.id}
                          onClick={() => handleMoveImage(image.id, 1)}
                          type="button"
                        >
                          <ArrowDown size={17} aria-hidden="true" />
                        </button>
                        <button
                          aria-label="Delete image"
                          className="icon-button danger"
                          disabled={imageActionId === image.id}
                          onClick={() => handleDeleteImage(image.id)}
                          type="button"
                        >
                          <Trash2 size={17} aria-hidden="true" />
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
              {imageError ? <div className="form-error" role="alert">{imageError}</div> : null}
            </section>
            <div className="form-grid">
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
                <span className="form-help">
                  {hasAcceptedBids ? "Locked after accepted bids exist." : "Current price starts here until the first accepted bid."}
                </span>
                <input
                  disabled={hasAcceptedBids}
                  id="starting-price"
                  inputMode="decimal"
                  min="0"
                  required
                  step="0.01"
                  type="number"
                  value={startingPrice}
                  onChange={(event) => setStartingPrice(event.target.value)}
                />
              </div>
              <div className="form-field">
                <label htmlFor="reserve-price">Reserve price</label>
                <span className="form-help">Optional. Leave blank when the lot has no reserve.</span>
                <input id="reserve-price" inputMode="decimal" min="0" step="0.01" type="number" value={reservePrice} onChange={(event) => setReservePrice(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="bid-increment">Bid increment</label>
                <span className="form-help">
                  {hasAcceptedBids ? "Locked after accepted bids exist." : "The backend enforces this increment on every bid."}
                </span>
                <input
                  disabled={hasAcceptedBids}
                  id="bid-increment"
                  inputMode="decimal"
                  min="0.01"
                  required
                  step="0.01"
                  type="number"
                  value={bidIncrement}
                  onChange={(event) => setBidIncrement(event.target.value)}
                />
              </div>
              <div className="form-field">
                <label htmlFor="status">Status</label>
                <select id="status" value={lotStatus} onChange={(event) => setLotStatus(event.target.value as LotStatus)}>
                  <option value="draft">Draft</option>
                  <option value="open" disabled={!openStatusAllowed}>Open</option>
                  <option value="closed">Closed</option>
                  <option value="sold">Sold</option>
                  <option value="cancelled">Cancelled</option>
                </select>
                <span className="form-help">{statusHelp}</span>
              </div>
              <div className="form-field">
                <label htmlFor="external-image">External image URL</label>
                <span className="form-help">Optional URL field for object-storage or CDN-hosted images.</span>
                <input id="external-image" type="url" value={externalImageUrl} onChange={(event) => setExternalImageUrl(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="image-file">Upload image</label>
                <span className="form-help">Local development stores uploads under media; production should use object storage.</span>
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
            {success ? <div className="form-success" role="status">{success}</div> : null}
            {error ? <div className="form-error" role="alert">{error}</div> : null}
            <button className="primary-button" disabled={isSubmitting} type="submit">
              {imageFile ? <Upload size={18} aria-hidden="true" /> : <Save size={18} aria-hidden="true" />}
              {isSubmitting ? "Saving" : "Save lot"}
            </button>
          </form>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}
