import { test, expect } from "@playwright/test";

test.describe("Home page", () => {
  test("renders URL input and submit button", async ({ page }) => {
    await page.goto("/");
    const input = page.locator('input[type="url"]');
    await expect(input).toBeVisible();
    await expect(page.getByRole("button", { name: /get transcript/i })).toBeVisible();
    await expect(page.getByText(/store knowledge, not media/i)).toBeVisible();
  });

  test("shows validation error for empty URL", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /get transcript/i }).click();
    await expect(page.getByText(/valid url/i)).toBeVisible();
  });

  test("shows error for invalid URL format", async ({ page }) => {
    await page.goto("/");
    await page.locator('input[type="url"]').fill("not-a-url");
    await page.getByRole("button", { name: /get transcript/i }).click();
    await expect(page.getByText(/valid url/i)).toBeVisible();
  });

  test("shows privacy message", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/no video stored/i)).toBeVisible();
    await expect(page.getByText(/no audio stored/i)).toBeVisible();
  });
});

test.describe("History page", () => {
  test("loads without crashing", async ({ page }) => {
    await page.goto("/history");
    await expect(page).toHaveTitle(/bayyn/i);
  });

  test("shows empty state when no transcripts", async ({ page }) => {
    await page.route("**/api/transcriptions*", async (route) => {
      await route.fulfill({
        json: { jobs: [], total: 0 },
      });
    });
    await page.goto("/history");
    await expect(page.getByText(/no transcripts yet/i)).toBeVisible();
  });
});

test.describe("Privacy page", () => {
  test("shows never stored items", async ({ page }) => {
    await page.goto("/privacy");
    await expect(page.getByText(/never stored/i)).toBeVisible();
    await expect(page.getByText(/media_stored/i)).toBeVisible();
  });
});

test.describe("Navbar", () => {
  test("has Bayyn branding and nav links", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Bayyn")).toBeVisible();
    await expect(page.getByRole("link", { name: /history/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /privacy/i })).toBeVisible();
  });
});
