import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  isPrivateAddress,
  assertFetchableUrl,
  pickDeclaredIcon,
  createFaviconCache,
  LIMITS,
} from "./favicon-resolver.mjs";

/** Stub DNS so these never touch the network. */
const publicDns = async () => [{ address: "93.184.216.34", family: 4 }];
const privateDns = async () => [{ address: "127.0.0.1", family: 4 }];

describe("isPrivateAddress (the SSRF boundary)", () => {
  it("blocks loopback, private, link-local, CGNAT and multicast v4", () => {
    for (const ip of [
      "127.0.0.1",
      "0.0.0.0",
      "10.1.2.3",
      "172.16.0.1",
      "172.31.255.255",
      "192.168.1.1",
      "169.254.169.254", // cloud metadata — the classic SSRF target
      "100.64.0.1",
      "198.18.0.1",
      "224.0.0.1",
    ]) {
      expect(isPrivateAddress(ip), ip).toBe(true);
    }
  });

  it("allows ordinary public v4", () => {
    for (const ip of ["93.184.216.34", "8.8.8.8", "172.15.0.1", "172.32.0.1"]) {
      expect(isPrivateAddress(ip), ip).toBe(false);
    }
  });

  it("blocks v6 loopback, unique-local and link-local", () => {
    for (const ip of ["::1", "::", "fc00::1", "fd12:3456::1", "fe80::1"]) {
      expect(isPrivateAddress(ip), ip).toBe(true);
    }
    expect(isPrivateAddress("2606:2800:220:1::248:1893")).toBe(false);
  });

  it("sees through v4-mapped v6 (::ffff:127.0.0.1)", () => {
    expect(isPrivateAddress("::ffff:127.0.0.1")).toBe(true);
    expect(isPrivateAddress("::ffff:169.254.169.254")).toBe(true);
  });

  it("treats junk as private (fail closed)", () => {
    expect(isPrivateAddress(undefined)).toBe(true);
    expect(isPrivateAddress("")).toBe(true);
  });
});

describe("assertFetchableUrl", () => {
  it("accepts a normal https URL", async () => {
    const url = await assertFetchableUrl("https://example.com/a", { lookup: publicDns });
    expect(url.hostname).toBe("example.com");
  });

  it("rejects non-http(s) schemes", async () => {
    for (const raw of ["file:///etc/passwd", "ftp://example.com", "javascript:alert(1)"]) {
      await expect(assertFetchableUrl(raw, { lookup: publicDns })).rejects.toThrow();
    }
  });

  it("rejects embedded credentials", async () => {
    await expect(
      assertFetchableUrl("https://user:pass@example.com/", { lookup: publicDns }),
    ).rejects.toThrow("credentials_in_url");
  });

  it("rejects hosts that resolve to a private address", async () => {
    await expect(
      assertFetchableUrl("https://sneaky.example/", { lookup: privateDns }),
    ).rejects.toThrow("private_host");
  });

  it("rejects local-ish hostnames without needing DNS", async () => {
    for (const raw of [
      "http://localhost:8080/",
      "http://printer.local/",
      "http://svc.internal/",
    ]) {
      await expect(assertFetchableUrl(raw, { lookup: publicDns })).rejects.toThrow("private_host");
    }
  });

  it("rejects a host that does not resolve", async () => {
    await expect(
      assertFetchableUrl("https://nope.example/", { lookup: async () => [] }),
    ).rejects.toThrow("dns_failed");
  });
});

describe("pickDeclaredIcon", () => {
  it("reads ClickUp's declared icon, which /favicon.ico does NOT match", () => {
    // The bug this whole module exists for: app.clickup.com declares its real
    // mark at a relative path while /favicon.ico serves a stale legacy icon.
    const html = `
      <link rel="apple-touch-icon" href="assets/favicons/apple-touch-icon.png">
      <link rel="icon" type="image/png" href="assets/favicons/favicon-16x16.png" sizes="16x16">
      <link rel="icon" type="image/png" href="assets/favicons/favicon-32x32.png" sizes="32x32">`;
    const picked = pickDeclaredIcon(html, "https://app.clickup.com/");
    // apple-touch-icon (180px) beats the 32x32, and the relative href resolves
    expect(picked).toBe("https://app.clickup.com/assets/favicons/apple-touch-icon.png");
  });

  it("resolves relative, root-relative and protocol-relative hrefs", () => {
    expect(
      pickDeclaredIcon('<link rel="icon" href="/static/i.png" sizes="64x64">', "https://a.com/x/y"),
    ).toBe("https://a.com/static/i.png");
    expect(
      pickDeclaredIcon('<link rel="icon" href="i.png" sizes="64x64">', "https://a.com/x/y"),
    ).toBe("https://a.com/x/i.png");
    expect(
      pickDeclaredIcon('<link rel="icon" href="//cdn.b.com/i.png" sizes="64x64">', "https://a.com/"),
    ).toBe("https://cdn.b.com/i.png");
  });

  it("prefers the largest icon-sized asset over a tiny one", () => {
    const html = `
      <link rel="icon" href="/s.png" sizes="16x16">
      <link rel="icon" href="/m.png" sizes="64x64">`;
    expect(pickDeclaredIcon(html, "https://a.com/")).toBe("https://a.com/m.png");
  });

  it("does not let an oversized PWA asset beat a well-sized icon", () => {
    const html = `
      <link rel="icon" href="/huge.png" sizes="1024x1024">
      <link rel="icon" href="/good.png" sizes="192x192">`;
    expect(pickDeclaredIcon(html, "https://a.com/")).toBe("https://a.com/good.png");
  });

  it("accepts 'shortcut icon' and is case-insensitive", () => {
    expect(pickDeclaredIcon('<LINK REL="Shortcut Icon" HREF="/f.ico">', "https://a.com/")).toBe(
      "https://a.com/f.ico",
    );
  });

  it("ignores unrelated <link> tags", () => {
    const html = `
      <link rel="stylesheet" href="/app.css">
      <link rel="preconnect" href="https://fonts.gstatic.com">
      <link rel="canonical" href="https://a.com/">`;
    expect(pickDeclaredIcon(html, "https://a.com/")).toBeNull();
  });

  it("returns null when nothing is declared", () => {
    expect(pickDeclaredIcon("<html><head></head></html>", "https://a.com/")).toBeNull();
  });
});

describe("favicon cache", () => {
  let dir;
  beforeEach(() => {
    dir = fs.mkdtempSync(path.join(os.tmpdir(), "wahha-icons-"));
  });
  afterEach(() => {
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("round-trips an icon", async () => {
    const cache = createFaviconCache(dir);
    expect(cache.read("https://a.com/")).toBeNull();

    await cache.write("https://a.com/", {
      contentType: "image/png",
      buffer: Buffer.from([1, 2, 3, 4]),
    });
    const hit = cache.read("https://a.com/");
    expect(hit.contentType).toBe("image/png");
    expect([...hit.buffer]).toEqual([1, 2, 3, 4]);
  });

  it("keys per URL, so one site's icon never bleeds into another's", async () => {
    const cache = createFaviconCache(dir);
    await cache.write("https://a.com/", { contentType: "image/png", buffer: Buffer.from([1]) });
    expect(cache.read("https://b.com/")).toBeNull();
  });

  it("expires entries past the TTL so a changed logo is picked up", async () => {
    let clock = 1_000_000;
    const cache = createFaviconCache(dir, { now: () => clock });
    await cache.write("https://a.com/", { contentType: "image/png", buffer: Buffer.from([1]) });
    expect(cache.read("https://a.com/")).not.toBeNull();

    clock += LIMITS.ttlMs + 1;
    expect(cache.read("https://a.com/")).toBeNull();
  });

  it("survives a corrupt cache file", async () => {
    const cache = createFaviconCache(dir);
    await cache.write("https://a.com/", { contentType: "image/png", buffer: Buffer.from([1]) });
    for (const f of fs.readdirSync(dir)) fs.writeFileSync(path.join(dir, f), "{ broken", "utf8");
    expect(cache.read("https://a.com/")).toBeNull();
  });

  it("leaves no temp files behind", async () => {
    const cache = createFaviconCache(dir);
    await cache.write("https://a.com/", { contentType: "image/png", buffer: Buffer.from([1]) });
    expect(fs.readdirSync(dir).filter((f) => f.endsWith(".tmp"))).toEqual([]);
  });
});
