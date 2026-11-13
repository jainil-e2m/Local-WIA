import { describe, it, expect } from "vitest";
import { normalizeBasePath, readBasePath } from "./base-path.mjs";

/**
 * A wrong prefix does not fail loudly — it produces a URL the upstream router
 * does not match, so every proxied call 404s with no hint as to why. These pin
 * the shapes an operator is likely to paste in.
 */

describe("normalizeBasePath", () => {
  it("returns an empty prefix for nothing configured", () => {
    for (const value of ["", "   ", undefined, null]) {
      expect(normalizeBasePath(value)).toBe("");
    }
  });

  it("keeps an already-correct prefix unchanged", () => {
    expect(normalizeBasePath("/api/v1")).toBe("/api/v1");
  });

  it("adds the leading slash an operator is likely to omit", () => {
    expect(normalizeBasePath("api/v1")).toBe("/api/v1");
  });

  it("drops a trailing slash, which would double up against the suffix", () => {
    // Suffixes always start with "/", so "/api/v1/" + "/audits" would ask the
    // upstream for "/api/v1//audits".
    expect(normalizeBasePath("/api/v1/")).toBe("/api/v1");
  });

  it("collapses stray slashes at both ends", () => {
    expect(normalizeBasePath("//api/v1//")).toBe("/api/v1");
  });

  it("treats a lone slash as no prefix", () => {
    expect(normalizeBasePath("/")).toBe("");
  });
});

describe("readBasePath", () => {
  const NAME = "AI_PRESENCE_AUDIT_BASE_PATH";

  it("falls back when the variable is absent entirely", () => {
    expect(readBasePath({}, NAME, "/api/v1")).toBe("/api/v1");
  });

  it("honours an explicit empty value instead of falling back", () => {
    // The distinction this function exists for: "" means the service serves the
    // audit contract at its root, and must not be read as "unset".
    expect(readBasePath({ [NAME]: "" }, NAME, "/api/v1")).toBe("");
  });

  it("normalizes whatever the variable holds", () => {
    expect(readBasePath({ [NAME]: " api/v2/ " }, NAME, "/api/v1")).toBe("/api/v2");
  });
});

describe("joined upstream paths", () => {
  // Mirrors the proxy: new URL(`${basePath}${suffix}`, `${origin}/`)
  const join = (basePath, suffix, origin = "https://presence.test") =>
    new URL(`${normalizeBasePath(basePath)}${suffix}`, `${origin}/`).toString();

  it("prefixes a service that serves under API_PREFIX", () => {
    expect(join("/api/v1", "/audits")).toBe("https://presence.test/api/v1/audits");
    expect(join("/api/v1", "/audits/abc/progress")).toBe(
      "https://presence.test/api/v1/audits/abc/progress",
    );
  });

  it("leaves a root-mounted service untouched", () => {
    expect(join("", "/audits")).toBe("https://presence.test/audits");
  });

  it("preserves the query string", () => {
    expect(join("/api/v1", "/audits/abc/report?format=html")).toBe(
      "https://presence.test/api/v1/audits/abc/report?format=html",
    );
  });

  it("demonstrates why the prefix cannot live on the service URL", () => {
    // An absolute path replaces the base's path — the exact trap base-path.mjs
    // documents. If this ever stops being true the separate field is redundant.
    expect(new URL("/audits", "https://presence.test/api/v1/").toString()).toBe(
      "https://presence.test/audits",
    );
  });
});
