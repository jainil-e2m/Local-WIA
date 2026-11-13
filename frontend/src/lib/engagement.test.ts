import { describe, expect, it } from "vitest";
import {
  DEMO_NOW_MS,
  ENGAGEMENTS,
  LANE_META,
  type EngagementRecord,
} from "@/data/engagement";
import { CLIENTS, CLIENT_INVOICES } from "@/data/opsHub";
import {
  citationCoverage,
  currentPhase,
  engagementAgeDays,
  engagementStart,
  fmtDuration,
  fmtRel,
  gapsFor,
  laneHealth,
  liveAssets,
  ms,
  pctOf,
  spanFor,
  supersededAssets,
  ticksFor,
  watchList,
} from "@/lib/engagement";

const rec = (id: string): EngagementRecord => ENGAGEMENTS[id];

/* The corpus is authored against a frozen clock. If DEMO_NOW ever moves, the
   numbers below move with it — which is the point of asserting them: a demo
   that silently re-anchors to the wall clock would pass every other test in
   this file while every date on screen quietly went wrong. */
describe("the frozen clock", () => {
  it("is 4 September 2026, matching DEMO_DATE in the Ops Hub corpus", () => {
    const d = new Date(DEMO_NOW_MS);
    expect(d.getFullYear()).toBe(2026);
    expect(d.getMonth()).toBe(8);
    expect(d.getDate()).toBe(4);
  });

  it("never reads Date.now — two calls a day apart agree", () => {
    expect(engagementAgeDays(rec("bloom"))).toBe(
      engagementAgeDays(rec("bloom"), DEMO_NOW_MS),
    );
  });
});

describe("engagement age", () => {
  it("counts from the day both halves paired, not from first contact", () => {
    /* Bloom's record begins 10 Feb 2025 with an inbound enquiry, 32 days
       before signature. Counting from there would turn a sales conversation
       into a month of engagement that never happened. */
    expect(engagementStart(rec("bloom"))).toBe("2025-03-14T18:07:00");
    expect(engagementAgeDays(rec("bloom"))).toBe(538);
    expect(fmtDuration(538)).toBe("18 months");
  });

  it("returns null for a prospect rather than counting from the enquiry", () => {
    expect(engagementStart(rec("magnolia"))).toBeNull();
    expect(engagementAgeDays(rec("magnolia"))).toBeNull();
  });

  it("stays in months until two years, then switches to years", () => {
    /* 22 months reads better than "1y 10m" at this length; past two years the
       month count stops being something anyone can picture. */
    expect(fmtDuration(engagementAgeDays(rec("rosewood"))!)).toBe("22 months");
    expect(fmtDuration(800)).toBe("2y 2m");
  });
});

describe("relative dates stay coarse as they get older", () => {
  it("degrades from days to weeks to months", () => {
    expect(fmtRel("2026-09-04T09:00:00")).toBe("today");
    expect(fmtRel("2026-09-03T09:00:00")).toBe("yesterday");
    expect(fmtRel("2026-08-28T09:00:00")).toBe("7 days ago");
    expect(fmtRel("2026-08-10T09:00:00")).toBe("3 weeks ago");
    expect(fmtRel("2026-05-04T09:00:00")).toBe("4 months ago");
    expect(fmtRel("2024-10-15T09:00:00")).toBe("1y 10m ago");
  });
});

describe("lane health", () => {
  it("measures each lane against its own cadence, not the account's", () => {
    /* Rosewood's money lane is current — an invoice went out in August — while
       nobody has been on a call since 20 July. An account-level staleness
       score would average those into something meaningless. */
    const health = laneHealth(rec("rosewood"));
    const meetings = health.find((h) => h.lane === "meetings")!;
    const money = health.find((h) => h.lane === "money")!;

    expect(meetings.days).toBe(46);
    expect(meetings.expectDays).toBe(35);
    expect(meetings.state).toBe("aging");
    expect(money.state).toBe("fresh");
  });

  it("calls a lane stale past twice its interval", () => {
    const comms = laneHealth(rec("everly")).find((h) => h.lane === "comms")!;
    expect(comms.days).toBeGreaterThan(comms.expectDays! * 2);
    expect(comms.state).toBe("stale");
  });

  it("says when silence might be coverage rather than inactivity", () => {
    /* Harbor's Drive mapping broke in April, so an empty work lane is not
       proof that no work happened. The note has to admit that, or someone
       chases a client about a problem we caused. */
    const work = laneHealth(rec("harbor")).find((h) => h.lane === "work")!;
    expect(work.state).toBe("stale");
    expect(work.blindSources).toContain("drive");
    expect(work.note).toMatch(/coverage rather than inactivity/);
  });

  it("will not call a lane stale when it never had a cadence", () => {
    /* A retainer has no office hours. Bloom's engagement lane holds two
       contact changes across eighteen months, which is not a rhythm anyone
       broke — and flagging it put a red alarm on the healthiest account. */
    const engagement = laneHealth(rec("bloom")).find((h) => h.lane === "engagement")!;
    expect(engagement.count).toBeLessThan(3);
    expect(engagement.state).toBe("n/a");
    expect(engagement.note).toMatch(/no cadence on this lane/);

    /* An Accelerator member does have one, and it has genuinely broken. */
    const everly = laneHealth(rec("everly")).find((h) => h.lane === "engagement")!;
    expect(everly.count).toBeGreaterThan(10);
    expect(everly.state).not.toBe("n/a");
  });

  it("keeps a no-cadence lane out of what to watch", () => {
    const items = watchList(rec("bloom"), CLIENTS.find((c) => c.id === "bloom")!);
    expect(items.some((w) => /engagement health/i.test(w.text))).toBe(false);
  });

  it("never marks onboarding stale — it is a period, not a cadence", () => {
    expect(LANE_META.onboarding.expectDays).toBeNull();
    const ob = laneHealth(rec("bloom")).find((h) => h.lane === "onboarding")!;
    expect(ob.state).toBe("n/a");
  });
});

describe("gaps", () => {
  it("attributes a gap to the source that went blind, when one did", () => {
    const span = spanFor(rec("harbor"), "all");
    const gaps = gapsFor(rec("harbor"), "work", span);
    expect(gaps.length).toBeGreaterThan(0);
    expect(gaps.at(-1)!.explainedBy).toBe("drive");
    expect(gaps.at(-1)!.why).toMatch(/mapping for Harbor House is unresolved/);
  });

  it("leaves an unexplained silence unattributed", () => {
    const span = spanFor(rec("everly"), "all");
    const gaps = gapsFor(rec("everly"), "comms", span);
    expect(gaps.length).toBeGreaterThan(0);
    expect(gaps.every((g) => g.explainedBy === null)).toBe(true);
  });

  it("draws no gap where the meetings kept happening", () => {
    /* Harbor's calls did NOT stop in April — the transcripts did. A silence
       drawn across that stretch would be a lie; the ring treatment on
       uncitable marks is what carries that story instead. The one gap this
       lane does have is real: nothing between discovery and the first monthly
       call, because the kickoffs sit on the onboarding lane. */
    const span = spanFor(rec("harbor"), "all");
    const gaps = gapsFor(rec("harbor"), "meetings", span);
    expect(gaps).toHaveLength(1);
    expect(new Date(gaps[0].toMs).getFullYear()).toBe(2025);
    expect(gaps.some((g) => g.fromMs > ms("2026-04-01T00:00:00"))).toBe(false);
  });
});

describe("citation coverage", () => {
  it("scores only the lanes where a citation means something", () => {
    /* An invoice does not need a transcript second. Scoring money rows as
       uncited would drag every account toward the same meaningless number. */
    const bloom = citationCoverage(rec("bloom"));
    const harbor = citationCoverage(rec("harbor"));

    /* Bloom is the reference record and still does not reach 100: its own
       pre-retention calls are uncitable too. A corpus where the healthy
       account scored perfectly would teach the wrong thing about real data. */
    expect(bloom.pct).toBeGreaterThan(80);
    expect(bloom.pct).toBeLessThan(100);

    /* Harbor is materially worse, and the margin is the point — it had a
       normal cited history until April and lost it, so its score is dragged
       down by a run of recent rows rather than being low throughout. */
    expect(bloom.pct - harbor.pct).toBeGreaterThan(20);
  });

  it("reports no score rather than zero when there is nothing to cite", () => {
    /* Willow has no meetings or commitments on record at all. 0% would read
       as "nothing is cited", which is a different and much worse claim than
       "there is nothing here to cite". */
    const willow = citationCoverage(rec("willow"));
    expect(willow.total).toBe(0);
    expect(willow.pct).toBe(0);
  });

  it("counts Harbor's five summary-only calls against it", () => {
    const missing = rec("harbor").events.filter(
      (e) => e.kind === "transcript_missing",
    );
    expect(missing).toHaveLength(5);
    expect(missing.every((e) => e.citation === null)).toBe(true);
  });

  it("puts every one of Harbor's uncitable rows after the key went blind", () => {
    /* The shape that matters: cited before 14 April, uncited after. A record
       that was simply patchy throughout would be a data-quality problem; this
       one is a dated, explainable loss of access. */
    const blind = ms("2026-04-14T00:00:00");
    const scored = rec("harbor").events.filter(
      (e) => e.lane === "meetings" || e.lane === "commitments",
    );
    const uncited = scored.filter((e) => e.citation === null && ms(e.occurredAt) > blind);
    /* A ClickUp task id is still a legitimate citation after the key went
       blind — it is the TRANSCRIPT second that stops being available, and
       conflating the two would make this test demand that Harbor lose
       evidence it still has. */
    const transcriptCited = scored.filter(
      (e) => e.citation !== null && /^\d{2}:\d{2}$/.test(e.citation) && ms(e.occurredAt) > blind,
    );
    expect(uncited.length).toBeGreaterThanOrEqual(8);
    expect(transcriptCited).toHaveLength(0);

    /* And before it, transcript seconds are the norm. */
    const transcriptCitedBefore = scored.filter(
      (e) => e.citation !== null && /^\d{2}:\d{2}$/.test(e.citation) && ms(e.occurredAt) < blind,
    );
    expect(transcriptCitedBefore.length).toBeGreaterThan(5);
  });
});

describe("asset supersede chain", () => {
  it("returns only what nothing else replaced", () => {
    const live = liveAssets(rec("bloom")).map((a) => a.id);
    const old = supersededAssets(rec("bloom")).map((a) => a.id);

    expect(live).toContain("bloom-a5"); // landing page v2
    expect(live).not.toContain("bloom-a2"); // v1, superseded by v2
    expect(old).toContain("bloom-a2");
    expect(live).toContain("bloom-a7"); // 2026 messaging
    expect(old).toContain("bloom-a1"); // 2025 messaging it replaced
    expect(live.length + old.length).toBe(rec("bloom").assets.length);
  });

  it("leaves an account with no supersessions entirely live", () => {
    expect(supersededAssets(rec("harbor"))).toHaveLength(0);
    expect(liveAssets(rec("harbor"))).toHaveLength(4);
  });
});

describe("phases", () => {
  it("makes the last phase the current one", () => {
    expect(currentPhase(rec("everly"))!.key).toBe("at_risk");
    expect(currentPhase(rec("bloom"))!.key).toBe("steady");
    expect(currentPhase(rec("magnolia"))!.key).toBe("prospect");
  });
});

describe("spine geometry", () => {
  it("runs the whole-engagement span from the record boundary, not the signature", () => {
    /* The boundary marker needs somewhere to sit, and the pre-signature sales
       conversation is part of the story. */
    const span = spanFor(rec("bloom"), "all");
    expect(span.startMs).toBeLessThan(ms(rec("bloom").backfill.beginsAt));
    expect(pctOf(ms(rec("bloom").backfill.beginsAt), span)).toBeGreaterThan(0);
    expect(pctOf(DEMO_NOW_MS, span)).toBeLessThan(100);
  });

  it("switches tick granularity with the span so the rail never crowds", () => {
    expect(ticksFor(spanFor(rec("rosewood"), "all"))[0].label).toMatch(/^Q[1-4] \d\d$/);
    expect(ticksFor(spanFor(rec("rosewood"), "year"))[0].label).toMatch(/^[A-Z][a-z]{2} \d\d$/);
    expect(ticksFor(spanFor(rec("rosewood"), "month")).length).toBeLessThan(8);
  });

  it("keeps every event inside its own whole-engagement span", () => {
    for (const id of Object.keys(ENGAGEMENTS)) {
      const span = spanFor(rec(id), "all");
      for (const e of rec(id).events) {
        const p = pctOf(ms(e.occurredAt), span);
        expect(p).toBeGreaterThanOrEqual(0);
        expect(p).toBeLessThanOrEqual(100);
      }
    }
  });
});

describe("corpus integrity", () => {
  it("keeps every record's events sorted and inside its declared boundary", () => {
    for (const id of Object.keys(ENGAGEMENTS)) {
      const r = rec(id);
      const times = r.events.map((e) => ms(e.occurredAt));
      expect([...times].sort((a, b) => a - b)).toEqual(times);
      expect(Math.min(...times)).toBeGreaterThanOrEqual(ms(r.backfill.beginsAt));
      expect(Math.max(...times)).toBeLessThanOrEqual(DEMO_NOW_MS);
    }
  });

  it("gives every supersedes pointer a real asset to point at", () => {
    for (const id of Object.keys(ENGAGEMENTS)) {
      const ids = new Set(rec(id).assets.map((a) => a.id));
      for (const a of rec(id).assets) {
        if (a.supersedes) expect(ids.has(a.supersedes)).toBe(true);
      }
    }
  });

  /* The guard that would have caught it: the engagement record was briefly
     giving Harbor a $1,850 retainer and an invoice number that already
     belonged to Rosewood, while the Money tab three clicks away showed
     $1,750. One record that contradicts the ledger it is drawn from is worse
     than no record, because it is the one people will quote. */
  it("never lets two accounts share an invoice number", () => {
    const owner = new Map<string, string>();
    for (const [id, r] of Object.entries(ENGAGEMENTS)) {
      for (const e of r.events) {
        if (!e.citation || !/^INV-\d+$/.test(e.citation)) continue;
        const seen = owner.get(e.citation);
        expect(seen === undefined || seen === id).toBe(true);
        owner.set(e.citation, id);
      }
    }
  });

  it("puts every invoice the Money tab shows onto the engagement record", () => {
    for (const [id, rows] of Object.entries(CLIENT_INVOICES)) {
      const cited = new Set(
        ENGAGEMENTS[id].events.map((e) => e.citation).filter(Boolean),
      );
      for (const inv of rows) expect(cited.has(inv.id)).toBe(true);
    }
  });

  it("agrees with the ledger on what the account pays each month", () => {
    for (const [id, rows] of Object.entries(CLIENT_INVOICES)) {
      if (!rows.length) continue;
      expect(ENGAGEMENTS[id].terms.monthly).toBe(rows[0].amount);
    }
  });

  it("declares a boundary for every account, including the prospect", () => {
    for (const id of Object.keys(ENGAGEMENTS)) {
      expect(rec(id).backfill.summary.length).toBeGreaterThan(20);
      expect(rec(id).phases.length).toBeGreaterThan(0);
    }
    expect(rec("magnolia").backfill.mode).toBe("no-engagement");
  });
});
