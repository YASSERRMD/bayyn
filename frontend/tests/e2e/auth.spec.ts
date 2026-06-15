import { test, expect } from "@playwright/test";

test.describe("Login page", () => {
  test("renders email and password fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("has link to register page", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("link", { name: /create one/i })).toBeVisible();
  });

  test("shows error for wrong credentials", async ({ page }) => {
    await page.route("**/api/auth/login", async (route) => {
      await route.fulfill({ status: 401, json: { detail: "Invalid email or password." } });
    });

    await page.goto("/login");
    await page.locator('input[type="email"]').fill("wrong@example.com");
    await page.locator('input[type="password"]').fill("wrongpass");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.getByText(/invalid email or password/i)).toBeVisible();
  });

  test("redirects to /history after successful login", async ({ page }) => {
    await page.route("**/api/auth/login", async (route) => {
      await route.fulfill({ json: { access_token: "valid-token", token_type: "bearer" } });
    });
    await page.route("**/api/auth/me", async (route) => {
      await route.fulfill({ json: { id: "user-1", email: "user@example.com", name: null, is_active: true } });
    });
    await page.route("**/api/transcriptions*", async (route) => {
      await route.fulfill({ json: { jobs: [], total: 0 } });
    });

    await page.goto("/login");
    await page.locator('input[type="email"]').fill("user@example.com");
    await page.locator('input[type="password"]').fill("password123");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/history/);
  });
});

test.describe("Register page", () => {
  test("renders name, email, and password fields", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator('input[placeholder*="Name"]')).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole("button", { name: /create account/i })).toBeVisible();
  });

  test("has link to login page", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("link", { name: /sign in/i })).toBeVisible();
  });

  test("shows validation error for short password", async ({ page }) => {
    await page.goto("/register");
    await page.locator('input[type="email"]').fill("user@example.com");
    await page.locator('input[type="password"]').fill("short");
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page.getByText(/at least 8 characters/i)).toBeVisible();
  });

  test("redirects to /history after successful registration", async ({ page }) => {
    await page.route("**/api/auth/register", async (route) => {
      await route.fulfill({ status: 201, json: { access_token: "new-token", token_type: "bearer" } });
    });
    await page.route("**/api/auth/me", async (route) => {
      await route.fulfill({ json: { id: "user-2", email: "new@example.com", name: "Test User", is_active: true } });
    });
    await page.route("**/api/transcriptions*", async (route) => {
      await route.fulfill({ json: { jobs: [], total: 0 } });
    });

    await page.goto("/register");
    await page.locator('input[type="email"]').fill("new@example.com");
    await page.locator('input[type="password"]').fill("securepass123");
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page).toHaveURL(/\/history/);
  });
});

test.describe("Nav auth state", () => {
  test("shows sign-in link when not authenticated", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: /sign in/i })).toBeVisible();
  });

  test("shows user email and sign-out when authenticated", async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("bayyn_access_token", "valid-token");
    });
    await page.route("**/api/auth/me", async (route) => {
      await route.fulfill({ json: { id: "u1", email: "logged@example.com", name: null, is_active: true } });
    });

    await page.goto("/");
    await expect(page.getByText(/logged@example\.com/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /out/i })).toBeVisible();
  });
});
