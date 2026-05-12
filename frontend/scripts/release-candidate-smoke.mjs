#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";

const tinyPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=",
  "base64",
);

const results = [];
const state = {};

function env(name, fallback = "") {
  return process.env[name] ?? fallback;
}

function boolEnv(name, fallback = false) {
  const value = env(name);
  if (!value) return fallback;
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
}

function intEnv(name, fallback) {
  const value = env(name);
  if (!value) return fallback;
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeApiBase(value) {
  const trimmed = value.replace(/\/+$/, "");
  return trimmed.endsWith("/api") ? trimmed : `${trimmed}/api`;
}

function requiredEnv(names) {
  return names.filter((name) => !env(name));
}

function nowIso(offsetSeconds = 0) {
  return new Date(Date.now() + offsetSeconds * 1000).toISOString();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function unwrapList(body) {
  if (Array.isArray(body)) return body;
  if (body && Array.isArray(body.results)) return body.results;
  return [];
}

function record(status, name, detail = "") {
  results.push({ status, name, detail });
  const padded = status.padEnd(4, " ");
  console.log(`[${padded}] ${name}${detail ? ` - ${detail}` : ""}`);
}

function fail(name, error) {
  const detail = error instanceof Error ? error.message : String(error);
  record("FAIL", name, detail);
}

function warn(name, detail) {
  record("WARN", name, detail);
}

async function check(name, fn, options = {}) {
  const warnOnly = Boolean(options.warnOnly);
  try {
    const detail = await fn();
    record("PASS", name, detail);
    return true;
  } catch (error) {
    if (warnOnly) {
      const detail = error instanceof Error ? error.message : String(error);
      warn(name, detail);
      return false;
    }
    fail(name, error);
    return false;
  }
}

class ApiClient {
  constructor(baseUrl, token = "") {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  withToken(token) {
    return new ApiClient(this.baseUrl, token);
  }

  async request(pathname, options = {}) {
    const headers = new Headers(options.headers ?? {});
    const hasBody = options.body !== undefined;
    const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
    if (hasBody && !isFormData && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (this.token) {
      headers.set("Authorization", `Bearer ${this.token}`);
    }

    const response = await fetch(`${this.baseUrl}${pathname}`, {
      ...options,
      headers,
    });
    const contentType = response.headers.get("content-type") ?? "";
    const body = contentType.includes("application/json")
      ? await response.json().catch(() => null)
      : await response.text().catch(() => "");

    if (!response.ok) {
      const message = extractError(body) || response.statusText || `HTTP ${response.status}`;
      const error = new Error(`${message} (${response.status})`);
      error.status = response.status;
      error.body = body;
      throw error;
    }

    return { body, response };
  }

  async json(pathname, options = {}) {
    const { body } = await this.request(pathname, options);
    return body;
  }
}

function extractError(body) {
  if (!body) return "";
  if (typeof body === "string") return body.trim();
  if (typeof body.detail === "string") return body.detail;
  if (typeof body.message === "string") return body.message;
  if (typeof body.reason === "string") return body.reason;
  const firstKey = Object.keys(body)[0];
  const firstValue = firstKey ? body[firstKey] : undefined;
  if (Array.isArray(firstValue)) return `${firstKey}: ${firstValue.join(" ")}`;
  if (typeof firstValue === "string") return `${firstKey}: ${firstValue}`;
  return "";
}

async function login(api, username, password) {
  const body = await api.json("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  if (!body?.access) {
    throw new Error(`Login did not return an access token for ${username}.`);
  }
  return body;
}

async function optionalFrontendHealth() {
  const frontendUrl = env("RC_SMOKE_FRONTEND_URL").replace(/\/+$/, "");
  if (!frontendUrl) {
    throw new Error("RC_SMOKE_FRONTEND_URL not set; API lifecycle smoke will continue.");
  }
  const response = await fetch(`${frontendUrl}/api/health`);
  if (!response.ok) {
    throw new Error(`Frontend health returned ${response.status}.`);
  }
  return `${frontendUrl}/api/health returned ${response.status}`;
}

async function uploadSmokeImage(api, lotId) {
  if (boolEnv("RC_SMOKE_UPLOAD_IMAGE", true) === false) {
    warn("Lot image upload", "RC_SMOKE_UPLOAD_IMAGE=false; upload check skipped.");
    return;
  }
  if (typeof FormData === "undefined" || typeof Blob === "undefined") {
    throw new Error("This Node runtime does not provide FormData/Blob for multipart uploads.");
  }

  const configuredPath = env("RC_SMOKE_IMAGE_PATH");
  let bytes = tinyPng;
  let filename = `rc-smoke-${Date.now()}.png`;
  let contentType = "image/png";

  if (configuredPath) {
    bytes = await readFile(configuredPath);
    filename = path.basename(configuredPath);
    const ext = path.extname(filename).toLowerCase();
    contentType = ext === ".webp" ? "image/webp" : ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
  }

  const form = new FormData();
  form.append("image", new Blob([bytes], { type: contentType }), filename);
  form.append("alt_text", "Release candidate smoke image");
  form.append("sort_order", "0");

  const image = await api.json(`/lots/${lotId}/images/`, {
    method: "POST",
    body: form,
  });
  if (!image?.id || !image?.image_url) {
    throw new Error("Image upload did not return id and image_url.");
  }
  state.imageId = image.id;
  return `image id ${image.id}`;
}

async function waitForWinner({ sellerApi, auctionId, lotId, endTimeMs }) {
  if (boolEnv("RC_SMOKE_SKIP_CLOSE_WAIT", false)) {
    warn("Auction close wait", "RC_SMOKE_SKIP_CLOSE_WAIT=true; lifecycle close/winner checks skipped.");
    return null;
  }

  const waitSeconds = intEnv("RC_SMOKE_CLOSE_WAIT_SECONDS", 210);
  const pollSeconds = intEnv("RC_SMOKE_POLL_SECONDS", 10);
  const deadline = Date.now() + waitSeconds * 1000;
  const endDelayMs = Math.max(0, endTimeMs - Date.now());
  if (endDelayMs > 0) {
    await sleep(Math.min(endDelayMs + 1500, waitSeconds * 1000));
  }

  while (Date.now() < deadline) {
    const auction = await sellerApi.json(`/auctions/${auctionId}/`);
    const results = await sellerApi.json(`/auctions/${auctionId}/results/`);
    const winner = unwrapList(results).find((item) => Number(item.lot_id) === Number(lotId));
    if (auction.status === "ended" && winner?.outcome_status === "winner_assigned") {
      return { auction, winner };
    }
    await sleep(pollSeconds * 1000);
  }

  return null;
}

async function main() {
  const rawApiBase = env("RC_SMOKE_API_BASE_URL") || env("NEXT_PUBLIC_API_BASE_URL");
  const missing = requiredEnv([
    rawApiBase ? "" : "RC_SMOKE_API_BASE_URL or NEXT_PUBLIC_API_BASE_URL",
    "RC_SMOKE_FRONTEND_URL",
    "RC_SMOKE_SELLER_USERNAME",
    "RC_SMOKE_SELLER_PASSWORD",
    "RC_SMOKE_BIDDER_USERNAME",
    "RC_SMOKE_BIDDER_PASSWORD",
    "RC_SMOKE_ADMIN_USERNAME",
    "RC_SMOKE_ADMIN_PASSWORD",
  ].filter(Boolean));

  if (missing.length) {
    for (const name of missing) {
      record("FAIL", "Required environment", `${name} is missing`);
    }
    summarizeAndExit();
    return;
  }

  const apiBase = normalizeApiBase(rawApiBase);
  const api = new ApiClient(apiBase);
  const runId = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const endOffsetSeconds = intEnv("RC_SMOKE_AUCTION_END_OFFSET_SECONDS", 75);
  const auctionTitle = `[RC SMOKE] Auction ${runId}`;
  const lotTitle = `[RC SMOKE] Lot ${runId}`;
  const startTime = nowIso(-120);
  const endTime = nowIso(endOffsetSeconds);
  const endTimeMs = new Date(endTime).getTime();

  record("PASS", "Smoke configuration", `api=${apiBase}`);
  await check("Frontend health", optionalFrontendHealth, { warnOnly: true });

  let seller;
  let bidder;
  let admin;
  let admin2;
  let sellerApi;
  let bidderApi;
  let adminApi;
  let admin2Api;

  await check("Seller login", async () => {
    seller = await login(api, env("RC_SMOKE_SELLER_USERNAME"), env("RC_SMOKE_SELLER_PASSWORD"));
    sellerApi = api.withToken(seller.access);
    return `seller user id ${seller.user?.id ?? "unknown"}`;
  });

  await check("Bidder login", async () => {
    bidder = await login(api, env("RC_SMOKE_BIDDER_USERNAME"), env("RC_SMOKE_BIDDER_PASSWORD"));
    bidderApi = api.withToken(bidder.access);
    return `bidder user id ${bidder.user?.id ?? "unknown"}`;
  });

  await check("Admin login", async () => {
    admin = await login(api, env("RC_SMOKE_ADMIN_USERNAME"), env("RC_SMOKE_ADMIN_PASSWORD"));
    adminApi = api.withToken(admin.access);
    return `admin user id ${admin.user?.id ?? "unknown"}`;
  });

  if (env("RC_SMOKE_ADMIN2_USERNAME") && env("RC_SMOKE_ADMIN2_PASSWORD")) {
    await check("Second admin login", async () => {
      admin2 = await login(api, env("RC_SMOKE_ADMIN2_USERNAME"), env("RC_SMOKE_ADMIN2_PASSWORD"));
      admin2Api = api.withToken(admin2.access);
      if (admin2.user?.id === admin.user?.id) {
        throw new Error("Second admin credentials resolved to the same user as the requesting admin.");
      }
      return `second admin user id ${admin2.user?.id ?? "unknown"}`;
    }, { warnOnly: true });
  } else {
    warn("Second admin login", "RC_SMOKE_ADMIN2_USERNAME/PASSWORD not set; full repair approve/apply smoke will be WARN.");
  }

  const unreadBefore = await bidderApi.json("/account/notifications/unread-count/").catch(() => ({ unread_count: null }));
  state.unreadBefore = unreadBefore.unread_count;

  await check("Create live auction", async () => {
    const auction = await sellerApi.json("/auctions/", {
      method: "POST",
      body: JSON.stringify({
        title: auctionTitle,
        description: "Release candidate smoke auction. Safe staging data.",
        start_time: startTime,
        end_time: endTime,
        status: "live",
      }),
    });
    state.auction = auction;
    return `auction id ${auction.id}, ends ${endTime}`;
  });

  await check("Create lot", async () => {
    const lot = await sellerApi.json("/lots/", {
      method: "POST",
      body: JSON.stringify({
        auction: state.auction.id,
        title: lotTitle,
        description: "Release candidate smoke lot. Safe staging data.",
        starting_price: "10.00",
        reserve_price: "15.00",
        bid_increment: "5.00",
        status: "open",
        images: [],
      }),
    });
    state.lot = lot;
    return `lot id ${lot.id}`;
  });

  await check("Upload lot image", async () => uploadSmokeImage(sellerApi, state.lot.id));

  await check("Browse created auction and lot", async () => {
    const auctions = unwrapList(await api.json(`/auctions/?search=${encodeURIComponent(auctionTitle)}`));
    const lots = unwrapList(await api.json(`/lots/?search=${encodeURIComponent(lotTitle)}`));
    if (!auctions.some((auction) => auction.id === state.auction.id)) {
      throw new Error("Created auction was not visible in public browse API.");
    }
    if (!lots.some((lot) => lot.id === state.lot.id)) {
      throw new Error("Created lot was not visible in public browse API.");
    }
    return "created auction and lot visible";
  });

  await check("Place valid bid", async () => {
    const result = await bidderApi.json(`/lots/${state.lot.id}/bid/`, {
      method: "POST",
      body: JSON.stringify({ amount: "15.00" }),
    });
    if (result.status !== "accepted" || !result.bid_id || result.current_price !== "15.00") {
      throw new Error(`Unexpected bid response: ${JSON.stringify(result)}`);
    }
    state.acceptedBidId = result.bid_id;
    return `accepted bid id ${result.bid_id}`;
  });

  await check("Place invalid bid controlled rejection", async () => {
    try {
      await bidderApi.json(`/lots/${state.lot.id}/bid/`, {
        method: "POST",
        body: JSON.stringify({ amount: "16.00" }),
      });
    } catch (error) {
      if (error.status !== 409 || error.body?.status !== "rejected") {
        throw error;
      }
      state.rejectedBidReason = error.body.reason;
      return `controlled ${error.status} ${error.body.reason}`;
    }
    throw new Error("Invalid bid was unexpectedly accepted.");
  });

  await check("Bid history", async () => {
    const publicHistory = unwrapList(await api.json(`/lots/${state.lot.id}/bids/`));
    const sellerHistory = unwrapList(await sellerApi.json(`/lots/${state.lot.id}/bids/`));
    if (!publicHistory.some((bid) => bid.id === state.acceptedBidId && bid.status === "accepted")) {
      throw new Error("Public bid history did not include accepted bid.");
    }
    if (!sellerHistory.some((bid) => bid.rejection_reason === state.rejectedBidReason)) {
      throw new Error("Seller bid history did not include rejected bid.");
    }
    return `public=${publicHistory.length}, seller=${sellerHistory.length}`;
  });

  await check("Audit log created", async () => {
    const logs = unwrapList(await adminApi.json(`/audit/?entity_type=lot&entity_id=${state.lot.id}`));
    const actions = new Set(logs.map((log) => log.action));
    if (!actions.has("bid_accepted") || !actions.has("bid_rejected")) {
      throw new Error(`Expected bid_accepted and bid_rejected audit logs; got ${[...actions].join(", ")}`);
    }
    return "bid audit logs visible to admin";
  });

  await check("Admin export CSV", async () => {
    const { body, response } = await adminApi.request(`/admin/activity/export/?entity_type=lot&entity_id=${state.lot.id}`);
    const text = String(body);
    if (!response.headers.get("content-type")?.includes("text/csv")) {
      throw new Error(`Expected text/csv; got ${response.headers.get("content-type")}`);
    }
    if (!text.includes("audit_id,admin_user_id,admin_username,action")) {
      throw new Error("CSV export header was not present.");
    }
    return "CSV export returned expected header";
  });

  let lifecycle;
  await check("Auction closing and winner calculation", async () => {
    lifecycle = await waitForWinner({
      sellerApi,
      auctionId: state.auction.id,
      lotId: state.lot.id,
      endTimeMs,
    });
    if (!lifecycle) {
      throw new Error("Timed out waiting for cron to close auction and calculate winner.");
    }
    state.winner = lifecycle.winner;
    if (Number(lifecycle.winner.winning_bid_id) !== Number(state.acceptedBidId)) {
      throw new Error("Winner was not calculated from the accepted bid created by this smoke run.");
    }
    return `winner bid id ${lifecycle.winner.winning_bid_id}`;
  }, { warnOnly: true });

  if (state.winner?.fulfillment_id) {
    await check("Fulfillment update", async () => {
      const updated = await sellerApi.json(`/dashboard/fulfillment/${state.winner.fulfillment_id}/`, {
        method: "PATCH",
        body: JSON.stringify({
          status: "winner_confirmed",
          public_winner_message: "Release candidate smoke fulfillment update.",
        }),
      });
      if (updated.status !== "winner_confirmed") {
        throw new Error(`Unexpected fulfillment status ${updated.status}.`);
      }
      state.fulfillment = updated;
      return `fulfillment id ${updated.id}`;
    });

    await check("Bidder won-lots reflects backend state", async () => {
      const wonLots = unwrapList(await bidderApi.json("/account/won-lots/"));
      const won = wonLots.find((item) => Number(item.lot_id) === Number(state.lot.id));
      if (!won) throw new Error("Won lot was not returned to bidder.");
      if (won.fulfillment_status !== "winner_confirmed") {
        throw new Error(`Expected winner_confirmed; got ${won.fulfillment_status}.`);
      }
      return "won-lots shows winner_confirmed";
    });

    await check("Notification unread and mark-read", async () => {
      const notifications = await bidderApi.json("/account/notifications/");
      const items = unwrapList(notifications);
      if (typeof state.unreadBefore === "number" && notifications.unread_count <= state.unreadBefore) {
        throw new Error(
          `Unread count did not increase after winner/fulfillment events; before=${state.unreadBefore}, after=${notifications.unread_count}.`,
        );
      }
      const related = items.find((item) => {
        const entityId = String(item.related_entity_id);
        return (
          (item.related_entity_type === "lot" && entityId === String(state.lot.id))
          || (item.related_entity_type === "fulfillment" && entityId === String(state.fulfillment.id))
        ) && !item.is_read;
      });
      if (!related) {
        throw new Error("No unread winner/fulfillment notification found for this smoke run.");
      }
      const readBack = await bidderApi.json(`/account/notifications/${related.id}/read/`, { method: "PATCH" });
      if (!readBack.is_read) {
        throw new Error("Notification did not return as read after mark-read.");
      }
      return `marked notification ${related.id} read`;
    });
  } else {
    warn("Fulfillment update", "Skipped because winner/fulfillment was not created before timeout.");
    warn("Bidder won-lots reflects backend state", "Skipped because winner/fulfillment was not created before timeout.");
    warn("Notification unread and mark-read", "Skipped because winner/fulfillment was not created before timeout.");
  }

  await check("Repair workflow access", async () => {
    const repairs = await adminApi.json(`/admin/outcome-repairs/?lot=${state.lot.id}`);
    if (!Array.isArray(repairs.results)) {
      throw new Error("Repair list did not return results.");
    }
    return "admin repair list accessible";
  });

  const repairMode = env("RC_SMOKE_REPAIR_MODE", "auto");
  if (state.winner?.winning_bid_id && admin2Api && repairMode !== "access") {
    await check("Repair create/approve/apply", async () => {
      const repair = await adminApi.json("/admin/outcome-repairs/", {
        method: "POST",
        body: JSON.stringify({
          lot: state.lot.id,
          requested_winning_bid: state.winner.winning_bid_id,
          reason: "Release candidate smoke verifies two-admin repair governance without changing bid history.",
        }),
      });
      await adminApi.json(`/admin/outcome-repairs/${repair.id}/comments/`, {
        method: "POST",
        body: JSON.stringify({ comment_text: "Release candidate smoke comment." }),
      });
      const approved = await admin2Api.json(`/admin/outcome-repairs/${repair.id}/approve/`, {
        method: "POST",
        body: JSON.stringify({ approval_notes: "Release candidate smoke approval." }),
      });
      if (approved.status !== "approved") {
        throw new Error(`Repair did not approve; status=${approved.status}`);
      }
      const applied = await adminApi.json(`/admin/outcome-repairs/${repair.id}/apply/`, { method: "POST" });
      if (applied.status !== "applied") {
        throw new Error(`Repair did not apply; status=${applied.status}`);
      }
      const audit = await adminApi.json(`/admin/outcome-repairs/${repair.id}/audit/`);
      if (unwrapList(audit).length === 0) {
        throw new Error("Repair audit detail returned no events.");
      }
      return `repair id ${repair.id}`;
    }, { warnOnly: repairMode === "auto" });
  } else if (repairMode === "full") {
    warn("Repair create/approve/apply", "Full repair mode requested but winner data or second admin credentials are unavailable.");
  } else {
    warn("Repair create/approve/apply", "Skipped; set RC_SMOKE_ADMIN2_USERNAME/PASSWORD to exercise two-admin repair approval.");
  }

  summarizeAndExit();
}

function summarizeAndExit() {
  const counts = {
    PASS: results.filter((result) => result.status === "PASS").length,
    WARN: results.filter((result) => result.status === "WARN").length,
    FAIL: results.filter((result) => result.status === "FAIL").length,
  };
  console.log("\nRelease candidate smoke summary");
  console.log(`PASS=${counts.PASS} WARN=${counts.WARN} FAIL=${counts.FAIL}`);
  const failOnWarn = boolEnv("RC_SMOKE_FAIL_ON_WARN", false);
  if (counts.FAIL > 0 || (failOnWarn && counts.WARN > 0)) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  fail("Unhandled smoke runner error", error);
  summarizeAndExit();
});
