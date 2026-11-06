import { describe, expect, it } from "vitest";
import { describeUpstreamUrlRejection, isAllowedUpstreamUrl } from "./upstream-url.mjs";

const dev = { nodeEnv: "development" };
const prod = { nodeEnv: "production" };

describe("isAllowedUpstreamUrl — https is always allowed", () => {
  it("accepts https anywhere, in any environment", () => {
    expect(isAllowedUpstreamUrl("https://tech-seo.up.railway.app", prod)).toBe(true);
    expect(isAllowedUpstreamUrl("https://tech-seo.up.railway.app", dev)).toBe(true);
    expect(isAllowedUpstreamUrl("https://127.0.0.1:8443", prod)).toBe(true);
  });
});

describe("isAllowedUpstreamUrl — the local-http exception stays narrow", () => {
  it("accepts plain http on loopback hosts outside production", () => {
    expect(isAllowedUpstreamUrl("http://127.0.0.1:8010", dev)).toBe(true);
    expect(isAllowedUpstreamUrl("http://localhost:8010", dev)).toBe(true);
    // URL.hostname KEEPS the brackets on an IPv6 literal, so the allow-list
    // carries the bracketed spelling too.
    expect(isAllowedUpstreamUrl("http://[::1]:8010", dev)).toBe(true);
  });

  it("refuses plain http in production even on loopback", () => {
    // The whole point: a bearer token must never cross an unencrypted hop in prod.
    expect(isAllowedUpstreamUrl("http://127.0.0.1:8010", prod)).toBe(false);
    expect(isAllowedUpstreamUrl("http://localhost:8010", prod)).toBe(false);
  });

  it("refuses plain http on any non-loopback host", () => {
    expect(isAllowedUpstreamUrl("http://ai-seo.up.railway.app", dev)).toBe(false);
    expect(isAllowedUpstreamUrl("http://10.0.0.5:8010", dev)).toBe(false);
    expect(isAllowedUpstreamUrl("http://192.168.1.20:8010", dev)).toBe(false);
  });

  it("is not fooled by hostnames that merely contain a loopback name", () => {
    // Exact-match set, not substring/suffix matching.
    expect(isAllowedUpstreamUrl("http://localhost.attacker.com", dev)).toBe(false);
    expect(isAllowedUpstreamUrl("http://notlocalhost", dev)).toBe(false);
    expect(isAllowedUpstreamUrl("http://127.0.0.1.attacker.com", dev)).toBe(false);
  });

  it("refuses other loopback spellings rather than guessing", () => {
    // Deliberately not in the allow-list; keeps the rule auditable by reading it.
    expect(isAllowedUpstreamUrl("http://127.0.0.2:8010", dev)).toBe(false);
    expect(isAllowedUpstreamUrl("http://0.0.0.0:8010", dev)).toBe(false);
  });
});

describe("isAllowedUpstreamUrl — junk is refused (fail closed)", () => {
  it("refuses empty, undefined and unparseable values", () => {
    expect(isAllowedUpstreamUrl(undefined, dev)).toBe(false);
    expect(isAllowedUpstreamUrl("", dev)).toBe(false);
    expect(isAllowedUpstreamUrl("not a url", dev)).toBe(false);
    expect(isAllowedUpstreamUrl("//127.0.0.1:8010", dev)).toBe(false);
  });

  it("refuses non-http protocols outright", () => {
    expect(isAllowedUpstreamUrl("ftp://127.0.0.1", dev)).toBe(false);
    expect(isAllowedUpstreamUrl("file:///etc/passwd", dev)).toBe(false);
    expect(isAllowedUpstreamUrl("ws://127.0.0.1:8010", dev)).toBe(false);
  });
});

describe("describeUpstreamUrlRejection", () => {
  it("returns null for an accepted URL", () => {
    expect(describeUpstreamUrlRejection("https://example.com", prod)).toBeNull();
  });

  it("returns null for loopback http in development", () => {
    // Regression: this returned a rejection reason for a URL the proxy gate
    // accepted, so boot logged "AI SEO BFF is not usable" while it proxied fine.
    expect(describeUpstreamUrlRejection("http://127.0.0.1:8010", dev)).toBeNull();
    expect(describeUpstreamUrlRejection("http://localhost:8010", dev)).toBeNull();
    expect(describeUpstreamUrlRejection("http://[::1]:8010", dev)).toBeNull();
  });

  it("never disagrees with isAllowedUpstreamUrl", () => {
    // The two are consumed by different call sites (the proxy gate vs. the boot
    // warning); if they can diverge, one of them lies.
    const cases = [
      "https://example.com",
      "http://127.0.0.1:8010",
      "http://localhost:8010",
      "http://[::1]:8010",
      "http://example.com",
      "http://10.0.0.5:8010",
      "http://localhost.attacker.com",
      "ftp://127.0.0.1",
      "nonsense",
      "",
      undefined,
    ];
    for (const nodeEnv of ["development", "production"]) {
      for (const value of cases) {
        const allowed = isAllowedUpstreamUrl(value, { nodeEnv });
        const reason = describeUpstreamUrlRejection(value, { nodeEnv });
        expect(reason === null, `${JSON.stringify(value)} @ ${nodeEnv}`).toBe(allowed);
      }
    }
  });

  it("explains why a set-but-rejected value was refused", () => {
    expect(describeUpstreamUrlRejection(undefined, dev)).toBe("not set");
    expect(describeUpstreamUrlRejection("nonsense", dev)).toMatch(/valid absolute URL/);
    expect(describeUpstreamUrlRejection("http://127.0.0.1:8010", prod)).toMatch(/production/);
    expect(describeUpstreamUrlRejection("http://example.com", dev)).toMatch(/loopback/);
    expect(describeUpstreamUrlRejection("ftp://127.0.0.1", dev)).toMatch(/unsupported protocol/);
  });
});
