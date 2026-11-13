import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { AuditRunRequest, AuditType } from "./audits";

/**
 * The request body each audit product receives. These shapes are the integration
 * contract with three independently deployed APIs, and nothing else in the app
 * asserts them — the panel tests stop at the `run()` call.
 */

const post = vi.fn();
const get = vi.fn();

vi.mock("axios", () => ({
  default: {
    create: () => ({
      post,
      get,
      interceptors: { response: { use: vi.fn() } },
    }),
  },
}));

async function loadAudits() {
  vi.resetModules();
  return import("./audits");
}

async function bodySentFor(type: AuditType, payload: AuditRunRequest) {
  const { startAudit } = await loadAudits();
  await startAudit(type, payload);
  const [path, body] = post.mock.calls[0];
  expect(path).toBe("/audits");
  return body as Record<string, unknown>;
}

const presencePayload: AuditRunRequest = {
  businessName: "Wahha Design",
  businessUrl: "https://wahhadesign.com",
  country: "United States",
  state: "Texas",
  city: "Austin",
  businessType: "Marketing Agency",
  socialProfiles: [],
  aiAssistants: ["chatgpt", "google_gemini"],
  targetKeywords: [],
  competitors: [],
  realEstateProfiles: {},
};

beforeEach(() => {
  post.mockReset();
  post.mockResolvedValue({ data: { audit_id: "run-1" } });
  get.mockReset();
});

afterEach(() => vi.unstubAllEnvs());

describe("startAudit — AI Presence", () => {
  it("sends a singular domain and camelCase identity, not seed_urls", async () => {
    const body = await bodySentFor("ai-presence", presencePayload);

    expect(body).toMatchObject({
      businessName: "Wahha Design",
      domain: "https://wahhadesign.com",
      country: "United States",
      state: "Texas",
      city: "Austin",
      businessType: "Marketing Agency",
    });
    // Technical SEO's keys must not leak into this product's intake.
    expect(body.seed_urls).toBeUndefined();
    expect(body.business_name).toBeUndefined();
  });

  it("always enables the AI visibility toggle, which the API requires", async () => {
    const body = await bodySentFor("ai-presence", presencePayload);
    expect(body.toggles).toEqual(["aiVisibility"]);
  });

  it("sends the assistant list explicitly rather than relying on the empty default", async () => {
    const body = await bodySentFor("ai-presence", presencePayload);
    expect(body.llm_eval_targets).toEqual(["chatgpt", "google_gemini"]);
  });

  it("omits the optional collections when they are empty", async () => {
    const body = await bodySentFor("ai-presence", presencePayload);
    expect(body.queries).toBeUndefined();
    expect(body.competitors).toBeUndefined();
    expect(body.socialProfiles).toBeUndefined();
    expect(body.youtubeAccountUrl).toBeUndefined();
  });

  it("carries the YouTube channel as its own field alongside the profile list", async () => {
    const body = await bodySentFor("ai-presence", {
      ...presencePayload,
      socialProfiles: [
        { platform: "linkedin", url: "linkedin.com/company/brand" },
        { platform: "youtube", url: "youtube.com/@brand" },
      ],
    });

    expect(body.socialProfiles).toHaveLength(2);
    expect(body.youtubeAccountUrl).toBe("youtube.com/@brand");
  });

  it("lifts each real-estate profile to its own top-level key", async () => {
    const body = await bodySentFor("ai-presence", {
      ...presencePayload,
      realEstateProfiles: {
        zillowProfileUrl: "zillow.com/profile/brand",
        realtorProfileUrl: "  ",
      },
    });

    expect(body.zillowProfileUrl).toBe("zillow.com/profile/brand");
    // A blank value is not a profile.
    expect(body.realtorProfileUrl).toBeUndefined();
  });

  it("sends the target keyword as the query seed list", async () => {
    const body = await bodySentFor("ai-presence", {
      ...presencePayload,
      targetKeywords: ["marketing agency austin"],
    });
    expect(body.queries).toEqual(["marketing agency austin"]);
  });
});

describe("status vocabulary bridge", () => {
  it("prefers dashboard_status on a single audit, so `complete` reads as terminal", async () => {
    const { getAuditStatus, TERMINAL_AUDIT_STATUSES } = await loadAudits();
    get.mockResolvedValue({
      data: { audit_id: "run-1", status: "complete", dashboard_status: "completed" },
    });

    const detail = await getAuditStatus("ai-presence", "run-1");

    // Untranslated, `complete` is not in the terminal set and useAuditRun would
    // poll a finished audit forever.
    expect(TERMINAL_AUDIT_STATUSES.has("complete" as never)).toBe(false);
    expect(detail.status).toBe("completed");
    expect(TERMINAL_AUDIT_STATUSES.has(detail.status as never)).toBe(true);
  });

  it("carries a partial completion through as its own outcome", async () => {
    const { getAuditStatus } = await loadAudits();
    get.mockResolvedValue({
      data: {
        audit_id: "run-1",
        status: "complete",
        dashboard_status: "completed_partial",
        has_partial_failures: true,
      },
    });

    expect((await getAuditStatus("ai-presence", "run-1")).status).toBe("completed_partial");
  });

  it("translates every row of the history list", async () => {
    const { listAudits } = await loadAudits();
    get.mockResolvedValue({
      data: {
        items: [
          { audit_id: "a", status: "complete", dashboard_status: "completed" },
          { audit_id: "b", status: "running_evals", dashboard_status: "running" },
        ],
      },
    });

    expect((await listAudits("ai-presence")).map((row) => row.status)).toEqual([
      "completed",
      "running",
    ]);
  });
});

describe("history list envelope", () => {
  it("reads AI Presence's paginated `items` envelope", async () => {
    const { listAudits } = await loadAudits();
    get.mockResolvedValue({
      data: {
        items: [{ audit_id: "a", status: "complete", dashboard_status: "completed" }],
        pagination: { page: 1, page_size: 20, total_count: 1, total_pages: 1 },
      },
    });

    // Reading only `audits` here yields [] — indistinguishable from "no audits",
    // which is exactly how this went unnoticed.
    expect(await listAudits("ai-presence")).toHaveLength(1);
  });

  it("still reads the `audits` envelope the other two services send", async () => {
    const { listAudits } = await loadAudits();
    get.mockResolvedValue({
      data: { audits: [{ audit_id: "a", status: "completed" }] },
    });

    expect(await listAudits("technical")).toHaveLength(1);
  });

  it("carries the client PDF download URL through to the row", async () => {
    const { listAudits } = await loadAudits();
    get.mockResolvedValue({
      data: {
        items: [
          {
            audit_id: "a",
            status: "complete",
            dashboard_status: "completed",
            client_pdf_download_url: "https://drive.google.com/uc?export=download&id=abc",
          },
        ],
      },
    });

    const [row] = await listAudits("ai-presence");
    expect(row.client_pdf_download_url).toContain("id=abc");
  });

  it("leaves a service that already speaks the vocabulary untouched", async () => {
    const { getAuditStatus } = await loadAudits();
    // Technical SEO sends no dashboard_status; its own status must pass through.
    get.mockResolvedValue({ data: { audit_id: "run-1", status: "completed_partial" } });

    expect((await getAuditStatus("technical", "run-1")).status).toBe("completed_partial");
  });
});

describe("startAudit — the other products are unchanged", () => {
  it("sends Technical SEO only its seed URLs and business name", async () => {
    const body = await bodySentFor("technical", {
      businessName: "Brand",
      businessUrl: "https://brand.com",
    });
    expect(body).toEqual({ seed_urls: ["https://brand.com"], business_name: "Brand" });
  });

  it("keeps AI SEO's snake_case base with its identity extras", async () => {
    const body = await bodySentFor("ai", {
      businessName: "Brand",
      businessUrl: "https://brand.com",
      country: "United States",
      state: "Texas",
      businessType: "Marketing Agency",
      socialProfiles: [{ platform: "youtube", url: "youtube.com/@brand" }],
    });

    expect(body).toEqual({
      seed_urls: ["https://brand.com"],
      business_name: "Brand",
      country: "United States",
      state: "Texas",
      businessType: "Marketing Agency",
      socialProfiles: [{ platform: "youtube", url: "youtube.com/@brand" }],
    });
    // Omitted rather than padded — a blank city would skew the entity lookup.
    expect(body.city).toBeUndefined();
    // AI SEO must not pick up the presence-only keys.
    expect(body.toggles).toBeUndefined();
    expect(body.llm_eval_targets).toBeUndefined();
  });
});
