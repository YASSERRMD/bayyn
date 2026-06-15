import { test, expect } from "@playwright/test";

const MOCK_TRANSCRIPT = {
  job_id: "00000000-0000-0000-0000-000000000001",
  full_text: "Hello world. Goodbye world.",
  word_count: 4,
  segment_count: 2,
  average_confidence: null,
  low_confidence_count: 0,
  has_low_confidence_segments: false,
  accuracy_disclaimer: null,
  created_at: "2026-01-01T00:00:00Z",
  segments: [
    {
      sequence_number: 1,
      start: 0,
      end: 5,
      text: "Hello world.",
      confidence: null,
      speaker_label: null,
      low_confidence: false,
    },
    {
      sequence_number: 2,
      start: 5,
      end: 10,
      text: "Goodbye world.",
      confidence: null,
      speaker_label: null,
      low_confidence: false,
    },
  ],
};

const MOCK_JOB = {
  job_id: "00000000-0000-0000-0000-000000000001",
  source_url: "https://www.youtube.com/watch?v=test",
  source_type: "youtube",
  source_domain: "youtube.com",
  title: "Test Video",
  duration_seconds: 10,
  language: "en",
  status: "completed",
  processing_strategy: "caption",
  error_message: null,
  progress_pct: 100,
  current_step: "completed",
  retry_count: 0,
  is_dead_letter: false,
  media_stored: false,
  created_at: "2026-01-01T00:00:00Z",
  started_at: "2026-01-01T00:00:01Z",
  completed_at: "2026-01-01T00:00:05Z",
};

test.describe("Transcript search", () => {
  test.beforeEach(async ({ page }) => {
    const jobId = "00000000-0000-0000-0000-000000000001";
    await page.route(`**/api/transcriptions/${jobId}`, async (route) => {
      await route.fulfill({ json: MOCK_JOB });
    });
    await page.route(`**/api/transcriptions/${jobId}/transcript`, async (route) => {
      await route.fulfill({ json: MOCK_TRANSCRIPT });
    });
    await page.goto(`/transcriptions/${jobId}`);
    // Switch to segments tab
    await page.getByRole("button", { name: /segments/i }).click();
  });

  test("shows search input in segments tab", async ({ page }) => {
    await expect(page.getByPlaceholder(/search segments/i)).toBeVisible();
  });

  test("filters segments by search query", async ({ page }) => {
    await page.getByPlaceholder(/search segments/i).fill("Hello");
    await expect(page.getByTestId("segment-1")).toBeVisible();
    await expect(page.getByTestId("segment-2")).not.toBeVisible();
  });

  test("shows match counter", async ({ page }) => {
    await page.getByPlaceholder(/search segments/i).fill("world");
    await expect(page.getByText(/1 of 2/)).toBeVisible();
  });

  test("clears search with Escape key", async ({ page }) => {
    const input = page.getByPlaceholder(/search segments/i);
    await input.fill("Hello");
    await input.press("Escape");
    await expect(input).toHaveValue("");
    // Both segments visible again
    await expect(page.getByTestId("segment-1")).toBeVisible();
    await expect(page.getByTestId("segment-2")).toBeVisible();
  });

  test("shows no matches message for unknown query", async ({ page }) => {
    await page.getByPlaceholder(/search segments/i).fill("xyzzy");
    await expect(page.getByText(/no segments match/i)).toBeVisible();
  });

  test("clears search with X button", async ({ page }) => {
    const input = page.getByPlaceholder(/search segments/i);
    await input.fill("Hello");
    await page.getByRole("button", { name: /clear search/i }).click();
    await expect(input).toHaveValue("");
  });

  test("search is case-insensitive", async ({ page }) => {
    await page.getByPlaceholder(/search segments/i).fill("HELLO");
    await expect(page.getByTestId("segment-1")).toBeVisible();
    await expect(page.getByTestId("segment-2")).not.toBeVisible();
  });
});
