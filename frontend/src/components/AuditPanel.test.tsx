import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { AuditPanel } from "./AuditPanel";
import type { Tool } from "@/data/tools";
import type { AuditType } from "@/services/api/audits";

const run = vi.fn();

vi.mock("@/hooks/useAuditRun", () => ({
  useAuditRun: () => ({
    phase: "idle",
    percent: 0,
    stage: "",
    business: null,
    auditId: null,
    detail: null,
    run,
    resume: vi.fn(),
    refresh: vi.fn(),
    reset: vi.fn(),
  }),
}));

function tool(id: string): Tool {
  return {
    id,
    name: id,
    description: "",
    tags: [],
    status: "live",
    roles: ["team"],
    url: "",
    icon: (() => null) as unknown as Tool["icon"],
    from: "#000",
    to: "#fff",
  };
}

/** The panel reads and writes ?run=, so it needs a router even for intake tests. */
function renderPanel(auditType: AuditType) {
  return render(
    <MemoryRouter>
      <AuditPanel tool={tool(`${auditType}-seo`)} auditType={auditType} />
    </MemoryRouter>,
  );
}

/** Every field the AI SEO API refuses to queue an audit without. */
async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/business name/i), "Wahha Design");
  await user.type(screen.getByLabelText(/business url/i), "wahhadesign.com");
  await user.type(screen.getByLabelText(/^country/i), "United States");
  await user.type(screen.getByLabelText(/state \/ region/i), "Texas");
  await user.type(screen.getByLabelText(/business type/i), "Marketing Agency");
}

const runAudit = () => screen.getByRole("button", { name: /run audit/i });

beforeEach(() => run.mockReset());

describe("AuditPanel — AI SEO required fields", () => {
  it("marks name, URL, country, state and business type required; city stays optional", () => {
    renderPanel("ai");
    expect(screen.getByLabelText(/business name/i)).toBeRequired();
    expect(screen.getByLabelText(/business url/i)).toBeRequired();
    expect(screen.getByLabelText(/^country/i)).toBeRequired();
    expect(screen.getByLabelText(/state \/ region/i)).toBeRequired();
    expect(screen.getByLabelText(/business type/i)).toBeRequired();
    // Optional on purpose: a padded city would skew the Knowledge Graph lookup.
    expect(screen.getByLabelText(/^city/i)).not.toBeRequired();
  });

  it("submits every required field once they are filled", async () => {
    const user = userEvent.setup();
    renderPanel("ai");
    await fillRequiredFields(user);
    await user.click(runAudit());

    expect(run).toHaveBeenCalledTimes(1);
    const [name, url, identity] = run.mock.calls[0];
    expect(name).toBe("Wahha Design");
    // The bare host is normalized so the backend receives an absolute URL.
    expect(url).toBe("https://wahhadesign.com");
    expect(identity).toMatchObject({
      country: "United States",
      state: "Texas",
      businessType: "Marketing Agency",
    });
    expect(identity.city).toBeUndefined();
    expect(identity.socialProfiles).toEqual([]);
  });

  it.each([
    ["state / region", /state \/ region/i],
    ["business type", /business type/i],
  ])("does not submit when %s is blank", async (_label, pattern) => {
    const user = userEvent.setup();
    renderPanel("ai");
    await fillRequiredFields(user);
    await user.clear(screen.getByLabelText(pattern));
    await user.click(runAudit());

    expect(run).not.toHaveBeenCalled();
  });
});

describe("AuditPanel — location autosuggest", () => {
  it("suggests countries by prefix and fills the field on selection", async () => {
    const user = userEvent.setup();
    renderPanel("ai");

    await user.type(screen.getByLabelText(/^country/i), "United Kin");
    await user.click(await screen.findByRole("option", { name: "United Kingdom" }));

    expect(screen.getByLabelText(/^country/i)).toHaveValue("United Kingdom");
  });

  it("scopes state suggestions to the chosen country", async () => {
    const user = userEvent.setup();
    renderPanel("ai");

    await user.type(screen.getByLabelText(/^country/i), "United States");
    await user.type(screen.getByLabelText(/state \/ region/i), "Tex");
    await user.click(await screen.findByRole("option", { name: "Texas" }));

    expect(screen.getByLabelText(/state \/ region/i)).toHaveValue("Texas");
  });

  it("clears the dependent state and city when the country changes", async () => {
    const user = userEvent.setup();
    renderPanel("ai");

    await user.type(screen.getByLabelText(/^country/i), "United States");
    await user.type(screen.getByLabelText(/state \/ region/i), "Texas");
    await user.type(screen.getByLabelText(/^city/i), "Austin");

    // A different country invalidates a Texan city.
    await user.type(screen.getByLabelText(/^country/i), "x");

    expect(screen.getByLabelText(/state \/ region/i)).toHaveValue("");
    expect(screen.getByLabelText(/^city/i)).toHaveValue("");
  });

  it("fills the state when a city is picked without one", async () => {
    const user = userEvent.setup();
    renderPanel("ai");

    await user.type(screen.getByLabelText(/^country/i), "United States");
    // State deliberately left blank — the city suggestion has to supply it.
    await user.type(screen.getByLabelText(/^city/i), "matth");
    await user.click(await screen.findByRole("option", { name: /Matthews, North Carolina/i }));

    expect(screen.getByLabelText(/^city/i)).toHaveValue("Matthews");
    expect(screen.getByLabelText(/state \/ region/i)).toHaveValue("North Carolina");
  });

  it("submits the state a city selection filled in", async () => {
    const user = userEvent.setup();
    renderPanel("ai");

    await user.type(screen.getByLabelText(/business name/i), "Schein Dental");
    await user.type(screen.getByLabelText(/business url/i), "scheindentalnc.com");
    await user.type(screen.getByLabelText(/business type/i), "Dental Clinic");
    await user.type(screen.getByLabelText(/^country/i), "United States");
    await user.type(screen.getByLabelText(/^city/i), "matth");
    await user.click(await screen.findByRole("option", { name: /Matthews, North Carolina/i }));
    await user.click(runAudit());

    // State is required by the API, so the backfill has to survive to the payload.
    expect(run).toHaveBeenCalledTimes(1);
    expect(run.mock.calls[0][2]).toMatchObject({
      country: "United States",
      state: "North Carolina",
      city: "Matthews",
    });
  });

  it("does not clear the city it just filled the state from", async () => {
    const user = userEvent.setup();
    renderPanel("ai");

    await user.type(screen.getByLabelText(/^country/i), "United States");
    await user.type(screen.getByLabelText(/^city/i), "matth");
    await user.click(await screen.findByRole("option", { name: /Matthews, North Carolina/i }));

    // Writing the state through its own handler would have wiped the city, since
    // changing a state invalidates the city beneath it.
    expect(screen.getByLabelText(/^city/i)).toHaveValue("Matthews");
  });

  it("keeps a typed value the dataset does not contain", async () => {
    const user = userEvent.setup();
    renderPanel("ai");
    await fillRequiredFields(user);
    await user.type(screen.getByLabelText(/^city/i), "Nowhereville");
    await user.click(runAudit());

    expect(run.mock.calls[0][2].city).toBe("Nowhereville");
  });
});

describe("AuditPanel — social profiles", () => {
  const addProfile = () =>
    screen.getByRole("button", { name: /add (a social profile|another)/i });

  it("adds no profile row until the add button is used", () => {
    renderPanel("ai");
    expect(screen.queryByRole("combobox", { name: /social platform/i })).toBeNull();
    expect(addProfile()).toBeInTheDocument();
  });

  it("submits the selected platform alongside its URL", async () => {
    const user = userEvent.setup();
    renderPanel("ai");
    await fillRequiredFields(user);

    await user.click(addProfile());
    await user.type(
      screen.getByLabelText(/youtube profile url/i),
      "https://www.youtube.com/@brand",
    );
    await user.click(runAudit());

    // The backend's grounding checks match on these exact lowercase keys.
    expect(run.mock.calls[0][2].socialProfiles).toEqual([
      { platform: "youtube", url: "https://www.youtube.com/@brand" },
    ]);
  });

  it("assigns each new row a platform not already taken, and disables the taken one", async () => {
    const user = userEvent.setup();
    renderPanel("ai");

    await user.click(addProfile());
    await user.click(addProfile());

    // Row 1 defaults to the first platform, row 2 to the first still unclaimed.
    expect(screen.getByLabelText(/youtube profile url/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/linkedin profile url/i)).toBeInTheDocument();

    // YouTube is claimed by row 1, so row 2 cannot also choose it.
    await user.click(screen.getByRole("combobox", { name: /social platform 2/i }));
    const listbox = screen.getByRole("listbox", { name: /social platform 2/i });
    expect(within(listbox).getByRole("option", { name: /youtube/i })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("rejects a URL from a different platform and blocks the run", async () => {
    const user = userEvent.setup();
    renderPanel("ai");
    await fillRequiredFields(user);

    await user.click(addProfile());
    // An Instagram URL under the YouTube label — the mistake this guard exists for.
    await user.type(
      screen.getByLabelText(/youtube profile url/i),
      "https://instagram.com/brand",
    );
    await user.click(runAudit());

    expect(run).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/not a YouTube URL/i);
  });

  it("accepts a bare host and a subdomain for the selected platform", async () => {
    const user = userEvent.setup();
    renderPanel("ai");
    await fillRequiredFields(user);

    await user.click(addProfile());
    // No scheme, and a subdomain: both are normal ways to paste a profile.
    await user.type(screen.getByLabelText(/youtube profile url/i), "m.youtube.com/@brand");
    await user.click(runAudit());

    expect(run).toHaveBeenCalledTimes(1);
    expect(run.mock.calls[0][2].socialProfiles).toEqual([
      { platform: "youtube", url: "m.youtube.com/@brand" },
    ]);
  });

  it("rejects a lookalike host that only ends with the platform name", async () => {
    const user = userEvent.setup();
    renderPanel("ai");
    await fillRequiredFields(user);

    await user.click(addProfile());
    await user.type(
      screen.getByLabelText(/youtube profile url/i),
      "https://youtube.com.attacker.net/@brand",
    );
    await user.click(runAudit());

    expect(run).not.toHaveBeenCalled();
  });

  it("drops a row left blank rather than blocking the run", async () => {
    const user = userEvent.setup();
    renderPanel("ai");
    await fillRequiredFields(user);

    await user.click(addProfile());
    await user.click(runAudit());

    expect(run).toHaveBeenCalledTimes(1);
    expect(run.mock.calls[0][2].socialProfiles).toEqual([]);
  });

  it("removes a row on request", async () => {
    const user = userEvent.setup();
    renderPanel("ai");

    await user.click(addProfile());
    await user.click(screen.getByRole("button", { name: /remove youtube profile/i }));

    expect(screen.queryByLabelText(/youtube profile url/i)).toBeNull();
  });
});

describe("AuditPanel — AI Presence intake", () => {
  /** Every field the AI Presence API refuses to queue an audit without. */
  async function fillPresenceFields(user: ReturnType<typeof userEvent.setup>) {
    await fillRequiredFields(user);
    await user.type(screen.getByLabelText(/^city/i), "Austin");
  }

  const identity = () => run.mock.calls[0][2];

  it("requires the city AI SEO leaves optional", () => {
    renderPanel("ai-presence");
    // Every assistant prompt is built around "city, state, country", so this API
    // refuses a blank city where AI SEO prefers one.
    expect(screen.getByLabelText(/^city/i)).toBeRequired();
  });

  it("does not ask for social profiles, which a presence run does not use", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    expect(screen.queryByRole("button", { name: /add a social profile/i })).toBeNull();

    await fillPresenceFields(user);
    await user.click(runAudit());

    expect(identity().socialProfiles).toBeUndefined();
  });

  it("does not submit when the city is blank", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillRequiredFields(user);
    await user.click(runAudit());

    expect(run).not.toHaveBeenCalled();
  });

  it("submits every assistant by default", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillPresenceFields(user);
    await user.click(runAudit());

    expect(run).toHaveBeenCalledTimes(1);
    // The backend's provider keys, not display names — `google_gemini`, not `gemini`.
    expect(identity().aiAssistants).toEqual([
      "chatgpt",
      "claude",
      "perplexity",
      "grok",
      "google_gemini",
    ]);
  });

  it("never offers or sends google_ai_overviews", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    expect(screen.queryByRole("button", { name: /ai overviews/i })).toBeNull();

    await fillPresenceFields(user);
    await user.click(runAudit());

    // Omitting it from the list is the whole mechanism: the backend reads an
    // empty `llm_eval_targets` as "every target", which would run it anyway.
    expect(identity().aiAssistants).not.toContain("google_ai_overviews");
    expect(identity().aiAssistants.length).toBeGreaterThan(0);
  });

  it("submits only the assistants left selected", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillPresenceFields(user);

    for (const label of ["Claude", "Perplexity", "Grok", "Gemini"]) {
      await user.click(screen.getByRole("button", { name: label }));
    }
    await user.click(runAudit());

    expect(identity().aiAssistants).toEqual(["chatgpt"]);
  });

  it("blocks the run when every assistant is deselected", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillPresenceFields(user);

    for (const label of ["ChatGPT", "Claude", "Perplexity", "Grok", "Gemini"]) {
      await user.click(screen.getByRole("button", { name: label }));
    }
    await user.click(runAudit());

    // An empty target list means "all of them" to the backend, so silently
    // sending nothing would run a wider audit than the form describes.
    expect(run).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/at least one platform/i);
  });

  it("sends a target keyword as a query seed, and omits a blank one", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillPresenceFields(user);
    await user.click(runAudit());
    expect(identity().targetKeywords).toEqual([]);

    run.mockReset();
    await user.type(screen.getByLabelText(/target keyword/i), "marketing agency austin");
    await user.click(runAudit());
    expect(identity().targetKeywords).toEqual(["marketing agency austin"]);
  });

  it("submits a completed competitor row", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillPresenceFields(user);

    await user.click(screen.getByRole("button", { name: /add a competitor/i }));
    await user.type(screen.getByLabelText(/competitor 1 brand name/i), "Rival Co");
    await user.type(screen.getByLabelText(/competitor 1 domain/i), "rival.com");
    await user.click(runAudit());

    expect(identity().competitors).toEqual([{ brandName: "Rival Co", domainUrl: "rival.com" }]);
  });

  it("blocks a half-filled competitor row, which the API would reject", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillPresenceFields(user);

    await user.click(screen.getByRole("button", { name: /add a competitor/i }));
    await user.type(screen.getByLabelText(/competitor 1 brand name/i), "Rival Co");
    await user.click(runAudit());

    expect(run).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/domain/i);
  });

  it("drops a competitor row left blank rather than blocking the run", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillPresenceFields(user);

    await user.click(screen.getByRole("button", { name: /add a competitor/i }));
    await user.click(runAudit());

    expect(run).toHaveBeenCalledTimes(1);
    expect(identity().competitors).toEqual([]);
  });

  it("offers the real-estate profiles only for a real-estate business", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    expect(screen.queryByRole("button", { name: /add a real estate profile/i })).toBeNull();

    // Free text, so the match is on the words a real-estate business would use.
    await user.type(screen.getByLabelText(/business type/i), "Residential Real Estate Broker");
    expect(screen.getByRole("button", { name: /add a real estate profile/i })).toBeInTheDocument();
  });

  it("submits a real-estate profile under its own payload key", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillRequiredFields(user);
    await user.clear(screen.getByLabelText(/business type/i));
    await user.type(screen.getByLabelText(/business type/i), "Realtor");
    await user.type(screen.getByLabelText(/^city/i), "Austin");

    await user.click(screen.getByRole("button", { name: /add a real estate profile/i }));
    await user.type(
      screen.getByLabelText(/zillow profile url/i),
      "zillow.com/profile/brand",
    );
    await user.click(runAudit());

    // Not a list entry — each platform is its own top-level field on that API.
    expect(identity().realEstateProfiles).toEqual({
      zillowProfileUrl: "zillow.com/profile/brand",
    });
  });

  it("rejects a real-estate URL pointing at the wrong platform", async () => {
    const user = userEvent.setup();
    renderPanel("ai-presence");
    await fillRequiredFields(user);
    await user.clear(screen.getByLabelText(/business type/i));
    await user.type(screen.getByLabelText(/business type/i), "Realtor");
    await user.type(screen.getByLabelText(/^city/i), "Austin");

    await user.click(screen.getByRole("button", { name: /add a real estate profile/i }));
    await user.type(screen.getByLabelText(/zillow profile url/i), "https://realtor.com/agents/x");
    await user.click(runAudit());

    expect(run).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/not a Zillow URL/i);
  });
});

describe("AuditPanel — AI SEO does not gain the presence controls", () => {
  it("renders no assistant picker, competitors or target keyword", () => {
    renderPanel("ai");
    expect(screen.queryByRole("group", { name: /ai platforms/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /add a competitor/i })).toBeNull();
    expect(screen.queryByLabelText(/target keyword/i)).toBeNull();
  });

  it("keeps its own social profiles, which ground its discoverability checks", () => {
    renderPanel("ai");
    expect(screen.getByRole("button", { name: /add a social profile/i })).toBeInTheDocument();
  });
});

describe("AuditPanel — Technical SEO is unaffected", () => {
  it("does not render identity fields, whose API does not accept them", () => {
    renderPanel("technical");
    expect(screen.getByLabelText(/business name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/business url/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^country/i)).toBeNull();
    expect(screen.queryByLabelText(/state \/ region/i)).toBeNull();
    expect(screen.queryByLabelText(/business type/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /add a social profile/i })).toBeNull();
  });

  it("submits name and URL only, with no identity payload", async () => {
    const user = userEvent.setup();
    renderPanel("technical");

    await user.type(screen.getByLabelText(/business name/i), "Brand");
    await user.type(screen.getByLabelText(/business url/i), "brand.com");
    await user.click(runAudit());

    expect(run).toHaveBeenCalledWith("Brand", "https://brand.com");
  });
});
