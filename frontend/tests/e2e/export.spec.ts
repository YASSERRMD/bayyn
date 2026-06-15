import { test, expect } from "@playwright/test";

const JOB_ID = "11111111-1111-1111-1111-111111111111";

const MOCK_JOB = {
  job_id: JOB_ID,
  source_url: "https://www.youtube.com/watch?v=test",
  source_type: "youtube",
  source_domain: "youtube.com",
  title: "Test Video",
  duration_seconds: 300,
  language: "en",
  status: "completed",
  processing_strategy: "caption",
  error_message: null,
  progress_pct: 100,
  current_step: null,
  retry_count: 0,
  is_dead_letter: false,
  media_stored: false,
  created_at: "2026-01-01T00:00:00Z",
  started_at: "2026-01-01T00:00:01Z",
  completed_at: "2026-01-01T00:00:10Z",
};

const MOCK_TRANSCRIPT = {
  job_id: JOB_ID,
  full_text: "Hello world. This is a test transcript.",
  word_count: 8,
  segment_count: 2,
  average_confidence: 0.95,
  low_confidence_count: 0,
  has_low_confidence_segments: false,
  accuracy_disclaimer: null,
  segments: [
    { sequence_number: 1, start: 0, end: 5, text: "Hello world.", confidence: 0.98, speaker_label: null, low_confidence: false, updated_at: null },
    { sequence_number: 2, start: 5, end: 10, text: "This is a test transcript.", confidence: 0.92, speaker_label: null, low_confidence: false, updated_at: null },
  ],
  created_at: "2026-01-01T00:00:10Z",
};

function mockTranscriptPage(page) {
  return Promise.all([
    page.route(`**/api/transcriptions/${JOB_ID}`, async (route) => {
      await route.fulfill({ json: MOCK_JOB });
    }),
    page.route(`**/api/transcriptions/${JOB_ID}/transcript`, async (route) => {
      await route.fulfill({ json: MOCK_TRANSCRIPT });
    }),
  ]);
}

test.describe("Export buttons on transcript page", () => {
  test("shows TXT, SRT, and DOCX export buttons when transcript is ready", async ({ page }) => {
    await mockTranscriptPage(page);
    await page.goto(`/transcriptions/${JOB_ID}`);

    // Wait for transcript to load
    await expect(page.getByText(/hello world/i)).toBeVisible();

    // Export anchor-wrapped buttons
    await expect(page.locator('a[download]').filter({ hasText: /txt/i })).toBeVisible();
    await expect(page.locator('a[download]').filter({ hasText: /srt/i })).toBeVisible();
    await expect(page.locator('a[download]').filter({ hasText: /docx/i })).toBeVisible();
  });

  test("export links point to correct API paths", async ({ page }) => {
    await mockTranscriptPage(page);
    await page.goto(`/transcriptions/${JOB_ID}`);
    await expect(page.getByText(/hello world/i)).toBeVisible();

    const txtLink = page.locator('a[download]').filter({ hasText: /txt/i });
    const href = await txtLink.getAttribute("href");
    expect(href).toContain(`/transcriptions/${JOB_ID}/export/txt`);
  });

  test("transcript text is visible in the UI", async ({ page }) => {
    await mockTranscriptPage(page);
    await page.goto(`/transcriptions/${JOB_ID}`);
    await expect(page.getByText(/hello world/i)).toBeVisible();
    await expect(page.getByText(/this is a test transcript/i)).toBeVisible();
  });

  test("privacy notice is visible", async ({ page }) => {
    await mockTranscriptPage(page);
    await page.goto(`/transcriptions/${JOB_ID}`);
    await expect(page.getByText(/no video or audio stored/i)).toBeVisible();
  });
});
