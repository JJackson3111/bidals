import { expect, test, type Page } from "@playwright/test";

const password = process.env.E2E_DEMO_PASSWORD ?? "ChangeMe123!";
const sellerUsername = process.env.E2E_SELLER_USERNAME ?? "demo_seller";
const bidderUsername = process.env.E2E_BIDDER_USERNAME ?? "demo_bidder";
const adminUsername = process.env.E2E_ADMIN_USERNAME ?? "demo_admin";

type IdResponse = { id: number };

function localDateTime(offsetMinutes: number): string {
  const date = new Date(Date.now() + offsetMinutes * 60_000);
  date.setSeconds(0, 0);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

async function login(page: Page, username: string) {
  await page.goto("/login");
  await page.locator("#username").fill(username);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /login/i }).click();
  await expect(page).toHaveURL(/\/auctions/, { timeout: 30_000 });
}

async function clearSession(page: Page) {
  await page.goto("/");
  await page.evaluate(() => {
    window.localStorage.removeItem("bidals.accessToken");
    window.localStorage.removeItem("bidals.refreshToken");
    window.localStorage.removeItem("bidals.user");
  });
}

test.describe("BIDALS smoke", () => {
  test("seller creates and edits an auction and lot, bidder sees backend bid feedback, admin sees audit", async ({ page }) => {
    if (process.env.E2E_DEBUG) {
      page.on("requestfailed", (request) => {
        if (request.url().includes(":8000") || request.url().includes("/api/")) {
          console.log(`request failed ${request.url()} ${request.failure()?.errorText ?? ""}`);
        }
      });
      page.on("response", (response) => {
        if (response.url().includes(":8000") || response.url().includes("/api/")) {
          console.log(`response ${response.status()} ${response.url()}`);
        }
      });
    }

    const suffix = Date.now();
    const auctionTitle = `Smoke Auction ${suffix}`;
    const editedAuctionTitle = `${auctionTitle} Edited`;
    const lotTitle = `Smoke Lot ${suffix}`;
    const editedLotTitle = `${lotTitle} Edited`;

    await login(page, sellerUsername);

    await page.goto("/dashboard/auctions/new");
    await page.getByLabel("Title").fill(auctionTitle);
    await page.getByLabel("Description").fill("Smoke-test auction created through the UI.");
    await page.getByLabel("Start time").fill(localDateTime(-5));
    await page.getByLabel("End time").fill(localDateTime(90));
    await page.getByLabel("Status").selectOption("live");
    const createAuctionResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/api/auctions/") && response.request().method() === "POST",
    );
    await page.getByRole("button", { name: /create auction/i }).click();
    const createdAuction = (await (await createAuctionResponsePromise).json()) as IdResponse;
    await page.goto(`/auctions/${createdAuction.id}`);
    await expect(page.getByRole("heading", { name: auctionTitle })).toBeVisible();

    const auctionId = createdAuction.id;

    await page.goto(`/dashboard/auctions/${auctionId}/edit`);
    await page.getByLabel("Title").fill(editedAuctionTitle);
    const updateAuctionResponsePromise = page.waitForResponse(
      (response) => response.url().includes(`/api/auctions/${auctionId}/`) && response.request().method() === "PATCH",
    );
    await page.getByRole("button", { name: /save auction/i }).click();
    await updateAuctionResponsePromise;
    await page.goto(`/auctions/${auctionId}`);
    await expect(page.getByRole("heading", { name: editedAuctionTitle })).toBeVisible();

    await page.goto("/dashboard/lots/new");
    await page.getByLabel("Auction").selectOption({ label: editedAuctionTitle });
    await page.getByLabel("Title").fill(lotTitle);
    await page.getByLabel("Description").fill("Smoke-test lot created through the UI.");
    await page.getByLabel("Starting price").fill("10.00");
    await page.getByLabel("Reserve price").fill("20.00");
    await page.getByLabel("Bid increment").fill("5.00");
    await page.getByLabel("Status").selectOption("open");
    const createLotResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/api/lots/") && response.request().method() === "POST",
    );
    await page.getByRole("button", { name: /create lot/i }).click();
    const createdLot = (await (await createLotResponsePromise).json()) as IdResponse;
    await page.goto(`/lots/${createdLot.id}`);
    await expect(page.getByRole("heading", { name: lotTitle })).toBeVisible();

    const lotId = createdLot.id;

    await page.goto(`/dashboard/lots/${lotId}/edit`);
    await page.getByLabel("Title").fill(editedLotTitle);
    const updateLotResponsePromise = page.waitForResponse(
      (response) => response.url().includes(`/api/lots/${lotId}/`) && response.request().method() === "PATCH",
    );
    await page.getByRole("button", { name: /save lot/i }).click();
    await updateLotResponsePromise;
    await page.goto(`/lots/${lotId}`);
    await expect(page.getByRole("heading", { name: editedLotTitle })).toBeVisible();

    await clearSession(page);
    await login(page, bidderUsername);

    await page.goto(`/lots/${lotId}`);
    await expect(page.getByRole("heading", { name: editedLotTitle })).toBeVisible();
    await page.getByLabel("Bid amount").fill("15.00");
    await page.getByRole("button", { name: /place bid/i }).click();
    await expect(page.getByText(/bid accepted/i)).toBeVisible();

    await page.getByLabel("Bid amount").fill("16.00");
    await page.getByRole("button", { name: /place bid/i }).click();
    await expect(page.getByText(/required increment|INVALID_INCREMENT/i)).toBeVisible();

    await clearSession(page);
    await login(page, adminUsername);

    await page.goto("/dashboard/audit");
    await expect(page.getByRole("heading", { name: /audit log/i })).toBeVisible();
    await expect(page.locator("article strong").filter({ hasText: /bid_accepted|auction_updated|lot_updated/ }).first()).toBeVisible();
  });
});
