import { describe, it, expect } from "vitest";
import { tools, toolsForRole } from "./tools";

/**
 * The hero counters and every route derive from this list, so its integrity
 * matters more than any single UI detail. These guard the invariants the rest
 * of the app assumes.
 */
describe("tools data", () => {
  it("has at least one tool", () => {
    expect(tools.length).toBeGreaterThan(0);
  });

  it("uses unique ids (routes key off tool.id)", () => {
    const ids = tools.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("only uses known statuses", () => {
    for (const tool of tools) {
      expect(["live", "development"]).toContain(tool.status);
    }
  });

  it("gives every tool valid hex gradient stops", () => {
    const hex = /^#[0-9a-fA-F]{6}$/;
    for (const tool of tools) {
      expect(tool.from).toMatch(hex);
      expect(tool.to).toMatch(hex);
    }
  });

  it("gives every tool a name and at least one tag", () => {
    for (const tool of tools) {
      expect(tool.name.trim()).not.toBe("");
      expect(tool.tags.length).toBeGreaterThan(0);
    }
  });
});

/**
 * A hidden tool must disappear from the library and STAY reachable by URL.
 * Both halves matter: dropping the entries instead would 404 the typed route
 * and orphan the audit history that HistoryPage joins on tool.id.
 */
describe("hidden tools", () => {
  const hidden = tools.filter((tool) => tool.hidden);

  it("keeps hidden tools out of the library for every role", () => {
    for (const role of ["team", "client", null] as const) {
      const listed = toolsForRole(role).map((tool) => tool.id);
      for (const tool of hidden) {
        expect(listed).not.toContain(tool.id);
      }
    }
  });

  it("keeps hidden tools in the resolvable list, so their URLs still work", () => {
    const ids = tools.map((tool) => tool.id);
    for (const tool of hidden) {
      expect(ids).toContain(tool.id);
    }
  });

  it("still lists the tools that are not hidden", () => {
    expect(toolsForRole("team").length).toBe(tools.filter((t) => !t.hidden).length);
    expect(toolsForRole("team").length).toBeGreaterThan(0);
  });
});
