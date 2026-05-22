import { clearAuthSession, getAccessToken, getRefreshToken } from "@/lib/auth";
import type {
  AccountNotificationsResponse,
  AdminActivityExportParams,
  ApiErrorBody,
  AuditLog,
  AuctionResultsResponse,
  Auction,
  Bid,
  BidResponse,
  CreateAuctionInput,
  CreateLotInput,
  FulfillmentTimelineResponse,
  FulfillmentResponse,
  FulfillmentUpdateInput,
  LoginResponse,
  Lot,
  LotImage,
  LotImageOrderItem,
  OperationsReport,
  OutcomeRepairCreateInput,
  OutcomeRepairCommentsResponse,
  OutcomeRepairAuditResponse,
  OutcomeRepairRequest,
  OutcomeRepairsResponse,
  PaginatedResponse,
  RegisterInput,
  ReadinessReport,
  UpdateAuctionInput,
  UpdateLotInput,
  User,
  WinnerReviewResponse,
  WonLotsResponse,
} from "@/lib/types";

const LOCAL_API_BASE_URL = "http://localhost:8000/api";
const STAGING_API_BASE_URL = "https://bidals.onrender.com/api";
const STAGING_FRONTEND_HOSTS = new Set([
  "bidals-frontend-staging.onrender.com",
  "bidals-1.onrender.com",
  "demo.bidals.com",
]);

export class ApiError extends Error {
  status: number;
  body: ApiErrorBody;

  constructor(message: string, status: number, body: ApiErrorBody = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }

  static messageFrom(error: unknown, fallback = "Request failed."): string {
    if (error instanceof ApiError) {
      return extractErrorMessage(error.body) || error.message || fallback;
    }

    if (isApiErrorLike(error)) {
      return extractErrorMessage(error.body) || error.message || fallback;
    }

    if (error instanceof Error && error.message) {
      return error.message;
    }

    return fallback;
  }
}

type ApiOptions = RequestInit & {
  auth?: boolean;
};

function resolveApiBaseUrl(): string {
  const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  const browserHostname = getBrowserHostname();
  const configuredBaseUrlIsUnsafe = Boolean(
    configuredBaseUrl
      && browserHostname
      && !isLocalHostname(browserHostname)
      && isLocalApiBaseUrl(configuredBaseUrl),
  );

  if (configuredBaseUrl && !configuredBaseUrlIsUnsafe) {
    return normalizeApiBaseUrl(configuredBaseUrl);
  }

  if (browserHostname && STAGING_FRONTEND_HOSTS.has(browserHostname)) {
    return STAGING_API_BASE_URL;
  }

  if (configuredBaseUrlIsUnsafe) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must not point at localhost outside local development.");
  }

  if (process.env.NODE_ENV === "development" || (browserHostname && isLocalHostname(browserHostname))) {
    return LOCAL_API_BASE_URL;
  }

  throw new Error("NEXT_PUBLIC_API_BASE_URL must be configured for deployed frontend builds.");
}

function normalizeApiBaseUrl(value: string): string {
  const trimmedValue = value.trim();

  try {
    const url = new URL(trimmedValue);
    const normalizedPath = url.pathname.replace(/\/+$/, "");
    url.pathname = normalizedPath || "/api";
    url.search = "";
    url.hash = "";
    return url.toString().replace(/\/+$/, "");
  } catch {
    return trimmedValue.replace(/\/+$/, "");
  }
}

function getBrowserHostname(): string | null {
  return typeof window === "undefined" ? null : window.location.hostname;
}

function isLocalApiBaseUrl(value: string): boolean {
  try {
    return isLocalHostname(new URL(value).hostname);
  } catch {
    return false;
  }
}

function isLocalHostname(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const hasBody = options.body !== undefined;
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  if (hasBody && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (options.auth !== false) {
    const token = getAccessToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(buildApiUrl(path), {
    ...options,
    headers,
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await response.json().catch(() => null) : null;
  const textBody = !isJson ? await response.text().catch(() => "") : "";

  if (!response.ok) {
    const message = extractErrorMessage(body) || textBody.trim() || response.statusText || `Request failed with ${response.status}`;
    throw new ApiError(message, response.status, body ?? {});
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!isJson) {
    throw new ApiError("Expected JSON response from API.", response.status, {
      detail: textBody.trim() || "The API returned a non-JSON response.",
    });
  }

  if (body === null) {
    throw new ApiError("Invalid JSON response from API.", response.status, {
      detail: "The API response could not be parsed as JSON.",
    });
  }

  return body as T;
}

function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${resolveApiBaseUrl()}${normalizedPath}`;
}

function extractErrorMessage(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const record = body as Record<string, unknown>;

  if (typeof record.detail === "string") return record.detail;
  if (typeof record.message === "string") return record.message;
  if (typeof record.reason === "string") return record.reason;

  const fieldMessages = Object.entries(record)
    .map(([key, value]) => {
      const message = formatErrorValue(value);
      return message ? `${humanizeFieldName(key)}: ${message}` : "";
    })
    .filter(Boolean);

  if (fieldMessages.length) return fieldMessages.join(" ");

  return null;
}

function isApiErrorLike(error: unknown): error is { body: ApiErrorBody; message?: string } {
  if (!error || typeof error !== "object") return false;
  return "body" in error && typeof (error as { body?: unknown }).body === "object";
}

function humanizeFieldName(key: string): string {
  if (key === "non_field_errors") return "Error";
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatErrorValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(formatErrorValue).filter(Boolean).join(" ");
  }

  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);

  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, nestedValue]) => {
        const nestedMessage = formatErrorValue(nestedValue);
        return nestedMessage ? `${humanizeFieldName(key)}: ${nestedMessage}` : "";
      })
      .filter(Boolean)
      .join(" ");
  }

  return "";
}

function unwrapResults<T>(response: PaginatedResponse<T> | T[]): T[] {
  if (Array.isArray(response)) {
    return response;
  }

  if (response && typeof response === "object" && Array.isArray(response.results)) {
    return response.results;
  }

  throw new ApiError("Unexpected API response shape.", 0, { detail: "Expected a list or paginated results." });
}

export const api = {
  async login(username: string, password: string): Promise<LoginResponse> {
    return apiFetch<LoginResponse>("/auth/login/", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ username, password }),
    });
  },

  async register(input: RegisterInput): Promise<User> {
    return apiFetch<User>("/auth/register/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(input),
    });
  },

  async logout(): Promise<void> {
    const refresh = getRefreshToken();
    if (!refresh) {
      clearAuthSession();
      return;
    }

    try {
      await apiFetch<void>("/auth/logout/", {
        method: "POST",
        body: JSON.stringify({ refresh }),
      });
    } finally {
      clearAuthSession();
    }
  },

  async me(): Promise<User> {
    return apiFetch<User>("/auth/me/");
  },

  async getAuctions(params?: {
    status?: string;
    search?: string;
    starts_after?: string;
    ends_before?: string;
    sort?: string;
  }): Promise<Auction[]> {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.search) search.set("search", params.search);
    if (params?.starts_after) search.set("starts_after", params.starts_after);
    if (params?.ends_before) search.set("ends_before", params.ends_before);
    if (params?.sort) search.set("sort", params.sort);
    const suffix = search.toString() ? `?${search.toString()}` : "";
    const response = await apiFetch<PaginatedResponse<Auction> | Auction[]>(`/auctions/${suffix}`);
    return unwrapResults(response);
  },

  async getAuction(id: number | string): Promise<Auction> {
    return apiFetch<Auction>(`/auctions/${id}/`);
  },

  async getManageAuction(id: number | string): Promise<Auction> {
    return apiFetch<Auction>(`/auctions/${id}/manage/`);
  },

  async createAuction(input: CreateAuctionInput): Promise<Auction> {
    return apiFetch<Auction>("/auctions/", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async updateAuction(id: number | string, input: UpdateAuctionInput): Promise<Auction> {
    return apiFetch<Auction>(`/auctions/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  },

  async getLots(params?: {
    auction?: number | string;
    status?: string;
    search?: string;
    auction_search?: string;
    starts_after?: string;
    ends_before?: string;
    sort?: string;
  }): Promise<Lot[]> {
    const search = new URLSearchParams();
    if (params?.auction) search.set("auction", String(params.auction));
    if (params?.status) search.set("status", params.status);
    if (params?.search) search.set("search", params.search);
    if (params?.auction_search) search.set("auction_search", params.auction_search);
    if (params?.starts_after) search.set("starts_after", params.starts_after);
    if (params?.ends_before) search.set("ends_before", params.ends_before);
    if (params?.sort) search.set("sort", params.sort);
    const suffix = search.toString() ? `?${search.toString()}` : "";
    const response = await apiFetch<PaginatedResponse<Lot> | Lot[]>(`/lots/${suffix}`);
    return unwrapResults(response);
  },

  async getLot(id: number | string): Promise<Lot> {
    return apiFetch<Lot>(`/lots/${id}/`);
  },

  async createLot(input: CreateLotInput): Promise<Lot> {
    return apiFetch<Lot>("/lots/", {
      method: "POST",
      body: JSON.stringify({
        ...input,
        reserve_price: input.reserve_price || null,
        images: input.images ?? [],
      }),
    });
  },

  async updateLot(id: number | string, input: UpdateLotInput): Promise<Lot> {
    return apiFetch<Lot>(`/lots/${id}/`, {
      method: "PATCH",
      body: JSON.stringify({
        ...input,
        reserve_price: input.reserve_price === "" ? null : input.reserve_price,
        images: input.images ?? undefined,
      }),
    });
  },

  async uploadLotImage(lotId: number | string, input: { file: File; altText?: string; sortOrder?: number }): Promise<LotImage> {
    const body = new FormData();
    body.append("image", input.file);
    if (input.altText) body.append("alt_text", input.altText);
    if (input.sortOrder !== undefined) body.append("sort_order", String(input.sortOrder));

    return apiFetch<LotImage>(`/lots/${lotId}/images/`, {
      method: "POST",
      body,
    });
  },

  async deleteLotImage(lotId: number | string, imageId: number | string): Promise<void> {
    await apiFetch<void>(`/lots/${lotId}/images/${imageId}/`, {
      method: "DELETE",
    });
  },

  async reorderLotImages(lotId: number | string, imageOrder: LotImageOrderItem[]): Promise<LotImage[]> {
    return apiFetch<LotImage[]>(`/lots/${lotId}/images/reorder/`, {
      method: "PATCH",
      body: JSON.stringify({ image_order: imageOrder }),
    });
  },

  async placeBid(lotId: number | string, amount: string): Promise<BidResponse> {
    return apiFetch<BidResponse>(`/lots/${lotId}/bid/`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    });
  },

  async getBidHistory(lotId: number | string): Promise<Bid[]> {
    const response = await apiFetch<PaginatedResponse<Bid> | Bid[]>(`/lots/${lotId}/bids/`);
    return unwrapResults(response);
  },

  async getAuditLogs(params?: {
    action?: string;
    actor?: string;
    entity_type?: string;
    entity_id?: string;
    date_from?: string;
    date_to?: string;
    bid_status?: string;
    metadata_search?: string;
  }): Promise<AuditLog[]> {
    const search = new URLSearchParams();
    if (params?.action) search.set("action", params.action);
    if (params?.actor) search.set("actor", params.actor);
    if (params?.entity_type) search.set("entity_type", params.entity_type);
    if (params?.entity_id) search.set("entity_id", params.entity_id);
    if (params?.date_from) search.set("date_from", params.date_from);
    if (params?.date_to) search.set("date_to", params.date_to);
    if (params?.bid_status) search.set("bid_status", params.bid_status);
    if (params?.metadata_search) search.set("metadata_search", params.metadata_search);
    const suffix = search.toString() ? `?${search.toString()}` : "";
    const response = await apiFetch<PaginatedResponse<AuditLog> | AuditLog[]>(`/audit/${suffix}`);
    return unwrapResults(response);
  },

  async getOperationsReport(params?: { window_minutes?: number | string }): Promise<OperationsReport> {
    const search = new URLSearchParams();
    if (params?.window_minutes) search.set("window_minutes", String(params.window_minutes));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return apiFetch<OperationsReport>(`/operations/${suffix}`);
  },

  async downloadAdminActivityExport(params?: AdminActivityExportParams): Promise<Blob> {
    const search = new URLSearchParams();
    if (params?.date_from) search.set("date_from", params.date_from);
    if (params?.date_to) search.set("date_to", params.date_to);
    if (params?.actor) search.set("actor", params.actor);
    if (params?.action_type) search.set("action_type", params.action_type);
    if (params?.entity_type) search.set("entity_type", params.entity_type);
    const suffix = search.toString() ? `?${search.toString()}` : "";
    const headers = new Headers();
    const token = getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const response = await fetch(buildApiUrl(`/admin/activity/export/${suffix}`), { headers });
    if (!response.ok) {
      const isJson = response.headers.get("content-type")?.includes("application/json");
      const body = isJson ? await response.json() : null;
      const message = extractErrorMessage(body) || response.statusText || "Export failed";
      throw new ApiError(message, response.status, body ?? {});
    }
    return response.blob();
  },

  async getReleaseCheck(): Promise<ReadinessReport> {
    return apiFetch<ReadinessReport>("/admin/release-check/");
  },

  async getWinnerReviews(params?: { outcome_status?: string; auction?: number | string }): Promise<WinnerReviewResponse> {
    const search = new URLSearchParams();
    if (params?.outcome_status) search.set("outcome_status", params.outcome_status);
    if (params?.auction) search.set("auction", String(params.auction));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return apiFetch<WinnerReviewResponse>(`/dashboard/winners/${suffix}`);
  },

  async getAuctionResults(id: number | string): Promise<AuctionResultsResponse> {
    return apiFetch<AuctionResultsResponse>(`/auctions/${id}/results/`);
  },

  async getFulfillmentRecords(params?: { status?: string; search?: string }): Promise<FulfillmentResponse> {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.search) search.set("search", params.search);
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return apiFetch<FulfillmentResponse>(`/dashboard/fulfillment/${suffix}`);
  },

  async updateFulfillmentRecord(id: number | string, input: FulfillmentUpdateInput): Promise<FulfillmentResponse["results"][number]> {
    return apiFetch<FulfillmentResponse["results"][number]>(`/dashboard/fulfillment/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  },

  async getFulfillmentTimeline(id: number | string): Promise<FulfillmentTimelineResponse> {
    return apiFetch<FulfillmentTimelineResponse>(`/dashboard/fulfillment/${id}/timeline/`);
  },

  async getWonLots(): Promise<WonLotsResponse> {
    return apiFetch<WonLotsResponse>("/account/won-lots/");
  },

  async getWonLotTimeline(id: number | string): Promise<FulfillmentTimelineResponse> {
    return apiFetch<FulfillmentTimelineResponse>(`/account/won-lots/${id}/timeline/`);
  },

  async getAccountNotifications(): Promise<AccountNotificationsResponse> {
    return apiFetch<AccountNotificationsResponse>("/account/notifications/");
  },

  async getUnreadNotificationCount(): Promise<{ unread_count: number }> {
    return apiFetch<{ unread_count: number }>("/account/notifications/unread-count/");
  },

  async markNotificationRead(id: number | string): Promise<AccountNotificationsResponse["results"][number]> {
    return apiFetch<AccountNotificationsResponse["results"][number]>(`/account/notifications/${id}/read/`, {
      method: "PATCH",
    });
  },

  async markAllNotificationsRead(): Promise<{ marked_read: number; unread_count: number }> {
    return apiFetch<{ marked_read: number; unread_count: number }>("/account/notifications/mark-all-read/", {
      method: "POST",
    });
  },

  async getOutcomeRepairs(params?: { status?: string; lot?: number | string }): Promise<OutcomeRepairsResponse> {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.lot) search.set("lot", String(params.lot));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return apiFetch<OutcomeRepairsResponse>(`/admin/outcome-repairs/${suffix}`);
  },

  async createOutcomeRepair(input: OutcomeRepairCreateInput): Promise<OutcomeRepairRequest> {
    return apiFetch<OutcomeRepairRequest>("/admin/outcome-repairs/", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async approveOutcomeRepair(id: number | string, input?: { approval_notes?: string }): Promise<OutcomeRepairRequest> {
    return apiFetch<OutcomeRepairRequest>(`/admin/outcome-repairs/${id}/approve/`, {
      method: "POST",
      body: JSON.stringify(input ?? {}),
    });
  },

  async rejectOutcomeRepair(id: number | string): Promise<OutcomeRepairRequest> {
    return apiFetch<OutcomeRepairRequest>(`/admin/outcome-repairs/${id}/reject/`, { method: "POST" });
  },

  async applyOutcomeRepair(id: number | string): Promise<OutcomeRepairRequest> {
    return apiFetch<OutcomeRepairRequest>(`/admin/outcome-repairs/${id}/apply/`, { method: "POST" });
  },

  async getOutcomeRepairComments(id: number | string): Promise<OutcomeRepairCommentsResponse> {
    return apiFetch<OutcomeRepairCommentsResponse>(`/admin/outcome-repairs/${id}/comments/`);
  },

  async getOutcomeRepairAudit(id: number | string): Promise<OutcomeRepairAuditResponse> {
    return apiFetch<OutcomeRepairAuditResponse>(`/admin/outcome-repairs/${id}/audit/`);
  },

  async createOutcomeRepairComment(id: number | string, commentText: string): Promise<OutcomeRepairCommentsResponse["results"][number]> {
    return apiFetch<OutcomeRepairCommentsResponse["results"][number]>(`/admin/outcome-repairs/${id}/comments/`, {
      method: "POST",
      body: JSON.stringify({ comment_text: commentText }),
    });
  },
};
