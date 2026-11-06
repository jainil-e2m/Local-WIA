import { describe, it, expect, vi, afterEach } from "vitest";
import { parseToolFlag, resolveToolStatus, toolFlagName, TOOL_FLAG_ENV } from "./toolFlags";
import { tools } from "./tools";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("parseToolFlag", () => {
  it("reads the accepted truthy spellings, case- and space-insensitively", () => {
    for (const value of ["true", "TRUE", " True ", "1", "yes", "on", "enabled", "live"]) {
      expect(parseToolFlag(value)).toBe(true);
    }
  });

  it("reads the accepted falsy spellings", () => {
    for (const value of [
      "false",
      "FALSE",
      " off ",
      "0",
      "no",
      "disabled",
      "locked",
      "coming-soon",
    ]) {
      expect(parseToolFlag(value)).toBe(false);
    }
  });

  it("treats unset and empty as 'no opinion' so the committed status wins", () => {
    // Railway/docker pass an unset variable through as "", which must not read
    // as false — that would silently lock every tool on a fresh deploy.
    expect(parseToolFlag(undefined)).toBeUndefined();
    expect(parseToolFlag("")).toBeUndefined();
    expect(parseToolFlag("   ")).toBeUndefined();
  });

  it("falls back (and warns) on a typo rather than guessing", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(parseToolFlag("ture")).toBeUndefined();
    expect(parseToolFlag("maybe")).toBeUndefined();
    // A typo must not lock a live tool — the fallback is the committed status.
    expect(resolveToolStatus("nonexistent-tool", "live")).toBe("live");
    expect(warn).toHaveBeenCalled();
  });
});

describe("resolveToolStatus", () => {
  it("returns the committed status when the tool has no flag set", () => {
    expect(resolveToolStatus("nonexistent-tool", "live")).toBe("live");
    expect(resolveToolStatus("nonexistent-tool", "development")).toBe("development");
  });
});

describe("toolFlagName", () => {
  it("maps a tool id to its env var", () => {
    expect(toolFlagName("lead-magnet")).toBe("VITE_TOOL_LEAD_MAGNET_ENABLED");
    expect(toolFlagName("ai-presence-checker")).toBe("VITE_TOOL_AI_PRESENCE_CHECKER_ENABLED");
  });
});

describe("flag coverage", () => {
  it("declares a flag for every tool", () => {
    // Vite only substitutes literal `import.meta.env.VITE_X` accesses, so each
    // tool needs its own entry in TOOL_FLAG_ENV — a tool missing from that map
    // could never be toggled from the environment.
    for (const tool of tools) {
      expect(Object.keys(TOOL_FLAG_ENV)).toContain(tool.id);
    }
  });

  it("keys every flag by a real tool id", () => {
    const ids = new Set(tools.map((tool) => tool.id));
    for (const id of Object.keys(TOOL_FLAG_ENV)) {
      expect(ids).toContain(id);
    }
  });
});
