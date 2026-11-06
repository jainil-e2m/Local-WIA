import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { parseDubsadoAlert } from "./onboarding-alert-parser.mjs";
import {
  createOnboardingStore,
  fingerprintAlert,
  OnboardingError,
  OFFERS,
} from "./onboarding-store.mjs";

let dir;
let file;
let opened;
let clock;

const DAY = 24 * 60 * 60 * 1000;

beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "wia-onboarding-"));
  file = path.join(dir, "nested", "onboarding.json");
  opened = [];
  clock = Date.parse("2026-09-07T12:00:00.000Z");
});

afterEach(async () => {
  // Let queued writes land before the directory disappears, otherwise an
  // in-flight rename races teardown and logs a spurious ENOENT.
  await Promise.all(opened.map((store) => store.flush().catch(() => {})));
  fs.rmSync(dir, { recursive: true, force: true });
});

const open = (options) => {
  const store = createOnboardingStore(file, { now: () => clock, ...options });
  opened.push(store);
  return store;
};

/** A seeded store is the only kind that will ingest anything. */
const openSeeded = async (options) => {
  const store = open(options);
  await store.seed({ projectNames: [], note: "test" });
  return store;
};

const signed = (project, firstName = "Brittanie") =>
  parseDubsadoAlert({ subject: `${firstName} has signed your contract for ${project}` });

const paid = (project, { firstName = "Alina", amount = "1997.00" } = {}) =>
  parseDubsadoAlert({ subject: `${firstName} has paid ${amount} USD - ${project}` });

/* ────────────────────────────────────────────────────────────────
   1. The seed gate
   ──────────────────────────────────────────────────────────────── */
describe("the seed gate", () => {
  it("refuses to ingest before seeding, and creates nothing", async () => {
    /* An unseeded first poll would read 90 days of Dubsado history as a queue
       of brand-new signings and try to onboard the entire client book. */
    const store = open();
    const result = await store.ingest(signed("The Elia"));
    expect(result.outcome).toBe("not_seeded");
    expect(result.client).toBeNull();
    expect(store.read().clients).toHaveLength(0);
  });

  it("ingests once seeded", async () => {
    const store = await openSeeded();
    const result = await store.ingest(signed("The Elia"));
    expect(result.outcome).toBe("half_pending");
  });

  it("marks the existing client book as already onboarded", async () => {
    const store = open();
    const { added } = await store.seed({
      projectNames: ["Dogwood Reserve", "The Elia"],
      note: "existing book as of Sept 7",
    });
    expect(added).toBe(2);
    expect(store.status().counts.PRE_EXISTING).toBe(2);
    expect(store.status().seeded).toBe(true);
  });

  it("is idempotent and additive on a second seed", async () => {
    const store = open();
    await store.seed({ projectNames: ["Dogwood Reserve"] });
    const second = await store.seed({ projectNames: ["Dogwood Reserve", "The Elia"] });
    expect(second.added).toBe(1);
    expect(second.total).toBe(2);
  });

  it("does not re-onboard a seeded client", async () => {
    const store = open();
    await store.seed({ projectNames: ["Dogwood Reserve"] });
    const result = await store.ingest(paid("Dogwood Reserve"));
    expect(result.outcome).toBe("recurring_payment");
    expect(result.client.state).toBe("PRE_EXISTING");
  });
});

/* ────────────────────────────────────────────────────────────────
   2. The conjunction gate — one alert is never a green light
   ──────────────────────────────────────────────────────────────── */
describe("the conjunction gate", () => {
  it("holds a lone SIGNED alert at AWAITING_PAIR", async () => {
    const store = await openSeeded();
    const { outcome, client } = await store.ingest(signed("The Elia"));
    expect(outcome).toBe("half_pending");
    expect(client.state).toBe("AWAITING_PAIR");
    expect(client.halves.signed).not.toBeNull();
    expect(client.halves.paid).toBeNull();
  });

  it("holds a lone PAID alert at AWAITING_PAIR", async () => {
    const store = await openSeeded();
    const { client } = await store.ingest(paid("Dogwood Reserve"));
    expect(client.state).toBe("AWAITING_PAIR");
    expect(client.halves.paid).not.toBeNull();
    expect(client.halves.signed).toBeNull();
  });

  it("completes the pair when signed arrives first", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"));
    const { outcome, client } = await store.ingest(paid("The Elia"));
    expect(outcome).toBe("pair_completed");
    expect(client.state).toBe("READY");
    expect(client.pairedAt).not.toBeNull();
  });

  it("completes the pair when paid arrives first", async () => {
    /* Order is NOT guaranteed — the correlator must be order-agnostic. */
    const store = await openSeeded();
    await store.ingest(paid("The Elia"));
    const { outcome, client } = await store.ingest(signed("The Elia"));
    expect(outcome).toBe("pair_completed");
    expect(client.state).toBe("READY");
  });

  it("keeps two different clients' halves apart", async () => {
    /* Exactly the shape of the real evidence: Dogwood Reserve has only a paid
       alert, The Elia only a signed one. Two halves, two clients, no pair. */
    const store = await openSeeded();
    await store.ingest(paid("Dogwood Reserve"));
    await store.ingest(signed("The Elia"));
    const board = store.read();
    expect(board.clients).toHaveLength(2);
    expect(board.clients.every((c) => c.state === "AWAITING_PAIR")).toBe(true);
  });
});

/* ────────────────────────────────────────────────────────────────
   3. Identity is the project, never the person
   ──────────────────────────────────────────────────────────────── */
describe("correlation identity", () => {
  it("pairs halves whose signatory and payer are different people", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia", "Brittanie"));
    const { outcome, client } = await store.ingest(paid("The Elia", { firstName: "Marcus" }));
    expect(outcome).toBe("pair_completed");
    expect(client.halves.signed.firstName).toBe("Brittanie");
    expect(client.halves.paid.firstName).toBe("Marcus");
  });

  it("treats one person signing for two venues as two clients", async () => {
    const store = await openSeeded();
    await store.ingest(signed("Dogwood Reserve", "Alina"));
    await store.ingest(signed("The Elia", "Alina"));
    expect(store.read().clients).toHaveLength(2);
  });

  it("correlates across case and spacing differences in the project name", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"));
    const { outcome } = await store.ingest(paid("  THE   ELIA  "));
    expect(outcome).toBe("pair_completed");
  });
});

/* ────────────────────────────────────────────────────────────────
   4. Poll idempotency and the recurring-payment guard
   ──────────────────────────────────────────────────────────────── */
describe("re-reading the same mailbox", () => {
  it("ignores a re-read of the identical alert", async () => {
    const store = await openSeeded();
    const alert = signed("The Elia");
    await store.ingest(alert);
    const again = await store.ingest(alert);
    expect(again.outcome).toBe("duplicate_half");
    expect(store.read().clients).toHaveLength(1);
  });

  it("dedupes on the mailbox message id when one is supplied", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"), { messageId: "msg-1" });
    const again = await store.ingest(signed("The Elia"), { messageId: "msg-1" });
    expect(again.outcome).toBe("duplicate_half");
  });

  it("fingerprints month 2 of a retainer differently from month 1", async () => {
    /* If the fingerprint ignored date and amount, month 2 would look like a
       duplicate and be silently swallowed — hiding the recurring payment
       instead of recording that the guard fired. */
    const month1 = parseDubsadoAlert({
      subject: "Alina has paid 2500.00 USD - Dogwood Reserve",
      body: [
        "---------- Forwarded message ---------",
        "From: Dubsado <noreply@dubsado.com>",
        "Date: Mon, Aug 3, 2026 at 9:00 AM",
        "Subject: Alina has paid 2500.00 USD - Dogwood Reserve",
      ].join("\n"),
    });
    const month2 = parseDubsadoAlert({
      subject: "Alina has paid 2500.00 USD - Dogwood Reserve",
      body: [
        "---------- Forwarded message ---------",
        "From: Dubsado <noreply@dubsado.com>",
        "Date: Thu, Sep 3, 2026 at 9:00 AM",
        "Subject: Alina has paid 2500.00 USD - Dogwood Reserve",
      ].join("\n"),
    });
    expect(fingerprintAlert(month1)).not.toBe(fingerprintAlert(month2));
  });

  it("refuses to re-onboard an approved client when the retainer bills again", async () => {
    /* THE TRAP. Elevate is a monthly retainer, so month 2's payment fires a
       subject identical in shape to month 1's. Nothing in the alert marks it
       as a repeat — only this store's own record does. */
    const store = await openSeeded();
    await store.ingest(signed("Dogwood Reserve"));
    await store.ingest(paid("Dogwood Reserve"));
    await store.activate("Dogwood Reserve", {
      offers: ["elevate"],
      draft: { tasks: [{ title: "Kickoff call" }] },
    });
    await store.approve("Dogwood Reserve");

    clock += 30 * DAY;
    const month2 = await store.ingest(
      parseDubsadoAlert({
        subject: "Alina has paid 2500.00 USD - Dogwood Reserve",
        receivedAt: new Date(clock).toISOString(),
      }),
    );

    expect(month2.outcome).toBe("recurring_payment");
    expect(month2.client.state).toBe("APPROVED");
    expect(month2.client.repeatAlerts).toHaveLength(1);
    expect(month2.client.repeatAlerts[0]).toMatchObject({ kind: "paid", amount: 2500 });
  });

  it("keeps the repeat-alert trail bounded", async () => {
    const store = await openSeeded();
    await store.ingest(signed("Dogwood Reserve"));
    await store.ingest(paid("Dogwood Reserve"));
    await store.activate("Dogwood Reserve", {
      offers: ["elevate"],
      draft: { tasks: [{ title: "Kickoff call" }] },
    });
    await store.approve("Dogwood Reserve");
    for (let month = 0; month < 30; month += 1) {
      clock += 30 * DAY;
      await store.ingest(
        parseDubsadoAlert({
          subject: "Alina has paid 2500.00 USD - Dogwood Reserve",
          receivedAt: new Date(clock).toISOString(),
        }),
      );
    }
    const client = store.read().clients[0];
    expect(client.repeatAlerts.length).toBeLessThanOrEqual(20);
  });
});

/* ────────────────────────────────────────────────────────────────
   5. Activate -> edit -> approve, and the states that refuse
   ──────────────────────────────────────────────────────────────── */
describe("activation and the approval gate", () => {
  const readyStore = async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"));
    await store.ingest(paid("The Elia"));
    return store;
  };

  const DRAFT = {
    tasks: [
      { id: "t1", title: "Send welcome email", assignee: "Gisselle", dueState: "dated", dueDate: "2026-09-08" },
      { id: "t2", title: "Keyword research", assignee: "Carmen", dueState: "pending", dueAnchor: "Ad strategy call" },
      { id: "t3", title: "Approve Meta retargeting", assignee: "Jacqueline", dueState: "gated" },
    ],
    templates: ["ads"],
  };

  it("requires an offer selection, because no alert carries the offer", async () => {
    const store = await readyStore();
    await expect(store.activate("The Elia", { offers: [], draft: DRAFT })).rejects.toThrow(
      OnboardingError,
    );
  });

  it("rejects an offer key it does not know", async () => {
    const store = await readyStore();
    await expect(
      store.activate("The Elia", { offers: ["not-an-offer"], draft: DRAFT }),
    ).rejects.toMatchObject({ code: "invalid_offers" });
  });

  it("accepts the additive both-offers case", async () => {
    /* Whitney @19:59: "we're going off BOTH of those onboarding templates" —
       a set, not a 1-of-N switch. */
    const store = await readyStore();
    const client = await store.activate("The Elia", {
      offers: ["leadlock", "ads"],
      draft: DRAFT,
    });
    expect(client.offers).toEqual(["leadlock", "ads"]);
    expect(client.state).toBe("DRAFTED");
  });

  it("refuses to activate a record that is still awaiting its pair", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"));
    await expect(
      store.activate("The Elia", { offers: ["ads"], draft: DRAFT }),
    ).rejects.toMatchObject({ code: "invalid_state", status: 409 });
  });

  it("persists a reviewer's edits to the draft", async () => {
    const store = await readyStore();
    await store.activate("The Elia", { offers: ["ads"], draft: DRAFT });
    const edited = {
      ...DRAFT,
      tasks: [
        { ...DRAFT.tasks[0], title: "Send welcome email (Whitney reviews first)" },
        { ...DRAFT.tasks[1], assignee: "Carmen" },
        { ...DRAFT.tasks[2], include: false },
      ],
    };
    const client = await store.updateDraft("The Elia", { draft: edited });
    expect(client.draft.tasks[0].title).toBe("Send welcome email (Whitney reviews first)");
    expect(client.draft.tasks[2].include).toBe(false);
    expect(client.state).toBe("DRAFTED");
  });

  it("refuses to approve a record that was never drafted", async () => {
    const store = await readyStore();
    await expect(store.approve("The Elia")).rejects.toMatchObject({
      code: "invalid_state",
      status: 409,
    });
  });

  it("freezes what a human actually authorised, excluded rows included", async () => {
    /* "Will not write" is half of what makes the gate reviewable. The record
       has to answer what a human authorised, not what the planner proposed. */
    const store = await readyStore();
    await store.activate("The Elia", { offers: ["ads"], draft: DRAFT });
    const client = await store.approve("The Elia", {
      draft: {
        ...DRAFT,
        tasks: [DRAFT.tasks[0], DRAFT.tasks[1], { ...DRAFT.tasks[2], include: false }],
      },
    });
    expect(client.state).toBe("APPROVED");
    expect(client.provisioned).toBe(true);
    expect(client.approvedBatch.tasks).toHaveLength(3);
    expect(client.approvedBatch.tasks.filter((t) => t.include)).toHaveLength(2);
    expect(client.approvedBatch.tasks.find((t) => !t.include).title).toBe(
      "Approve Meta retargeting",
    );
  });

  it("keeps the three due-date states distinct through approval", async () => {
    const store = await readyStore();
    await store.activate("The Elia", { offers: ["ads"], draft: DRAFT });
    const client = await store.approve("The Elia");
    const states = client.approvedBatch.tasks.map((t) => t.dueState);
    expect(states).toEqual(["dated", "pending", "gated"]);
  });

  it("defaults an unknown due state to unscheduled rather than inventing a date", async () => {
    const store = await readyStore();
    const client = await store.activate("The Elia", {
      offers: ["ads"],
      draft: { tasks: [{ title: "Mystery task", dueState: "whenever" }] },
    });
    /* `unscheduled`, not `pending`: an unrecognised state means we have no
       scheduling rule for it, which is a stronger and more useful statement
       than "waiting". */
    expect(client.draft.tasks[0].dueState).toBe("unscheduled");
  });

  it("refuses to approve an empty batch", async () => {
    const store = await readyStore();
    await store.activate("The Elia", { offers: ["ads"], draft: { tasks: [] } });
    await expect(store.approve("The Elia")).rejects.toMatchObject({ code: "invalid_draft" });
  });

  it("marks a placeholder draft as such", async () => {
    /* A reviewer must never mistake an invented task list for their own
       ClickUp template. */
    const store = await readyStore();
    const client = await store.activate("The Elia", {
      offers: ["ads"],
      draft: { tasks: [{ title: "Placeholder task" }], placeholder: true },
    });
    expect(client.draft.placeholder).toBe(true);
  });
});

/* ────────────────────────────────────────────────────────────────
   6. Ignoring, and the half-pair that never completes
   ──────────────────────────────────────────────────────────────── */
describe("ignoring and expiry", () => {
  it("dismisses a record with a reason on it", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"));
    const client = await store.ignore("The Elia", { reason: "dismissed", note: "duplicate deal" });
    expect(client.state).toBe("IGNORED");
    expect(client.ignoreReason).toBe("dismissed");
    expect(client.ignoreNote).toBe("duplicate deal");
  });

  it("will not ignore an approved record", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"));
    await store.ingest(paid("The Elia"));
    await store.activate("The Elia", { offers: ["ads"], draft: { tasks: [{ title: "x" }] } });
    await store.approve("The Elia");
    await expect(store.ignore("The Elia")).rejects.toMatchObject({ status: 409 });
  });

  it("withdraws a half-pair that never completed", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"));
    clock += 15 * DAY;
    const { expired } = await store.expireStalePairs({ ttlDays: 14 });
    expect(expired).toEqual(["the elia"]);
    expect(store.read().clients[0].ignoreReason).toBe("half_pair_timeout");
  });

  it("leaves a fresh half-pair alone", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"));
    clock += 3 * DAY;
    const { expired } = await store.expireStalePairs({ ttlDays: 14 });
    expect(expired).toEqual([]);
    expect(store.read().clients[0].state).toBe("AWAITING_PAIR");
  });

  it("does not expire a completed pair waiting on a human", async () => {
    const store = await openSeeded();
    await store.ingest(signed("The Elia"));
    await store.ingest(paid("The Elia"));
    clock += 60 * DAY;
    const { expired } = await store.expireStalePairs({ ttlDays: 14 });
    expect(expired).toEqual([]);
    expect(store.read().clients[0].state).toBe("READY");
  });

  it("404s on a project it has never seen", async () => {
    const store = await openSeeded();
    await expect(store.ignore("Nowhere Farm")).rejects.toMatchObject({
      code: "not_found",
      status: 404,
    });
  });
});

/* ────────────────────────────────────────────────────────────────
   7. Durability
   ──────────────────────────────────────────────────────────────── */
describe("durability", () => {
  it("survives a reopen from disk", async () => {
    const first = await openSeeded();
    await first.ingest(signed("The Elia"));
    await first.ingest(paid("The Elia"));
    await first.activate("The Elia", { offers: ["leadlock", "ads"], draft: { tasks: [{ title: "Kickoff" }] } });
    await first.flush();

    const second = open();
    const board = second.read();
    expect(board.seeded).toBe(true);
    expect(board.clients).toHaveLength(1);
    expect(board.clients[0]).toMatchObject({
      projectKey: "the elia",
      state: "DRAFTED",
      offers: ["leadlock", "ads"],
    });
  });

  it("starts empty on a corrupt file, and therefore UNSEEDED", async () => {
    /* The stakes are higher here than for the leads store: an empty store is
       an unseeded store, so ingest refuses instead of re-onboarding the whole
       client book off a corrupt read. */
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, "{ not json", "utf8");
    const store = open();
    expect(store.status().loadError).toBeTruthy();
    expect(store.status().seeded).toBe(false);
    const result = await store.ingest(signed("The Elia"));
    expect(result.outcome).toBe("not_seeded");
  });

  it("drops duplicate project keys when loading a hand-edited file", async () => {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(
      file,
      JSON.stringify({
        version: 1,
        seededAt: "2026-09-07T00:00:00.000Z",
        clients: [
          { projectKey: "the elia", projectName: "The Elia", state: "READY" },
          { projectKey: "the elia", projectName: "The Elia (dupe)", state: "AWAITING_PAIR" },
        ],
      }),
      "utf8",
    );
    const store = open();
    expect(store.read().clients).toHaveLength(1);
    expect(store.read().clients[0].projectName).toBe("The Elia");
  });

  it("rejects a non-array seed", async () => {
    const store = open();
    await expect(store.seed({ projectNames: "The Elia" })).rejects.toMatchObject({
      code: "invalid_seed",
    });
  });
});

/* ────────────────────────────────────────────────────────────────
   8. The offer vocabulary carries its own provenance
   ──────────────────────────────────────────────────────────────── */
describe("offer vocabulary", () => {
  it("marks an offer confirmed only when a real ClickUp template was read for it", async () => {
    /* This assertion USED to read "only the two offers Whitney named on Sept 2
       @19:59". Reading their workspace superseded that: Ridgefield Weddings and
       Events, a live ELEVATE client, holds both onboarding lists plus Client
       Management, which confirms elevate and full_service map to real
       templates. `templateConfirmed` now means "a template was read", not
       "Whitney mentioned one". */
    expect(OFFERS.leadlock.templateConfirmed).toBe(true);
    expect(OFFERS.ads.templateConfirmed).toBe(true);
    expect(OFFERS.elevate.templateConfirmed).toBe(true);
    expect(OFFERS.full_service.templateConfirmed).toBe(true);

    /* The two accelerators have their own ClickUp templates ("Google Ads VIP
       Day", "Ads Traffic Landing Page") that are not yet mapped to an offer, so
       they still contribute no tasks and the UI must say so. */
    expect(OFFERS.google_accelerator.templateConfirmed).toBe(false);
    expect(OFFERS.meta_accelerator.templateConfirmed).toBe(false);
  });

  it("maps every confirmed offer to at least one real template list", async () => {
    const { OFFER_TO_TEMPLATES } = await import("./onboarding-plan.mjs");
    for (const [key, offer] of Object.entries(OFFERS)) {
      const mapped = OFFER_TO_TEMPLATES[key] ?? [];
      expect(mapped.length > 0, `${key} confirmed but unmapped`).toBe(offer.templateConfirmed);
    }
  });
});

describe("wave 2 — applying an anchor date", () => {
  const drafted = async () => {
    const store = await openSeeded();
    await store.ingest(signed("Ridgefield Weddings and Events"));
    await store.ingest(paid("Ridgefield Weddings and Events"));
    const { buildDraft } = await import("./onboarding-plan.mjs");
    await store.activate("Ridgefield Weddings and Events", {
      offers: ["elevate"],
      draft: buildDraft({ offers: ["elevate"] }),
    });
    return store;
  };

  it("computes nothing at signature, because no call has been booked yet", async () => {
    const store = await drafted();
    const client = store.read().clients[0];
    expect(client.draft.tasks.some((t) => t.dueDate)).toBe(false);
    expect(client.draft.anchors).toEqual({});
  });

  it("dates ONLY the tasks that hang off the anchor supplied", async () => {
    /* The correction. One "kickoff" used to date every phase-driven task on
       both tracks, inventing LeadLock deadlines from an ads call. */
    const store = await drafted();
    const { computed, client } = await store.applyAnchorDate("Ridgefield Weddings and Events", {
      anchor: "leadlock_kickoff",
      date: "2026-03-25T00:00:00.000Z",
    });
    expect(computed).toBeGreaterThan(50);
    expect(client.draft.anchors.leadlock_kickoff).toBe("2026-03-25");

    /* Ridgefield's real LeadLock schedule: Tech Setup landed at +14. */
    const techSetup = client.draft.tasks.filter((t) => t.phase === "Tech Setup" && t.dueDate);
    expect(techSetup.length).toBeGreaterThan(0);
    for (const task of techSetup) expect(task.dueDate).toBe("2026-04-08");

    /* And nothing on the ADS track moved, because its kickoff is a
       different call on a different date. */
    const adsDated = client.draft.tasks.filter(
      (t) => t.templateKey === "ads" && t.dueDate,
    );
    expect(adsDated).toHaveLength(0);
  });

  it("never dates a client-gated task, however much is known", async () => {
    const store = await drafted();
    const { client } = await store.applyAnchorDate("Ridgefield Weddings and Events", {
      anchor: "leadlock_kickoff",
      date: "2026-03-25T00:00:00.000Z",
    });
    const gated = client.draft.tasks.filter((t) => t.dueState === "gated");
    expect(gated.length).toBeGreaterThan(0);
    for (const task of gated) expect(task.dueDate).toBeNull();
  });

  it("preserves a deliberate override and RECOMPUTES a calculated one", async () => {
    /* Both halves matter. The previous version skipped every task that
       already had a date, including dates it had calculated itself, so a
       postponed call could not move anything. */
    const store = await drafted();
    await store.applyAnchorDate("Ridgefield Weddings and Events", {
      anchor: "leadlock_kickoff",
      date: "2026-03-25T00:00:00.000Z",
    });

    const before = store.read().clients[0].draft;
    const target = before.tasks.find((t) => t.dateSource === "calculated");
    const other = before.tasks.find(
      (t) => t.dateSource === "calculated" && t.id !== target.id,
    );
    const edited = {
      ...before,
      tasks: before.tasks.map((t) =>
        t.id === target.id ? { ...t, dueDate: "2026-01-01", dateSource: "manual" } : t,
      ),
    };
    await store.updateDraft("Ridgefield Weddings and Events", { draft: edited });

    /* The call moves a week later. */
    const { client, preserved } = await store.applyAnchorDate("Ridgefield Weddings and Events", {
      anchor: "leadlock_kickoff",
      date: "2026-04-01T00:00:00.000Z",
    });

    expect(preserved).toBeGreaterThan(0);
    expect(client.draft.tasks.find((t) => t.id === target.id).dueDate).toBe("2026-01-01");
    /* The derived one followed the call. */
    const movedOther = client.draft.tasks.find((t) => t.id === other.id);
    expect(movedOther.dueDate).not.toBe(
      before.tasks.find((t) => t.id === other.id).dueDate,
    );
  });

  it("refuses a record that is not drafted", async () => {
    const store = await openSeeded();
    await store.ingest(signed("Ridgefield Weddings and Events"));
    await expect(
      store.applyAnchorDate("Ridgefield Weddings and Events", {
        anchor: "leadlock_kickoff",
        date: "2026-03-25",
      }),
    ).rejects.toMatchObject({ code: "invalid_state", status: 409 });
  });

  it("refuses a date it cannot parse", async () => {
    const store = await drafted();
    await expect(
      store.applyAnchorDate("Ridgefield Weddings and Events", {
        anchor: "leadlock_kickoff",
        date: "next Tuesday",
      }),
    ).rejects.toMatchObject({ code: "invalid_date" });
  });
});

describe("approval is two waves, and the first is not the end", () => {
  const drafted = async () => {
    const store = await openSeeded();
    await store.ingest(signed("Ridgefield Weddings and Events"));
    await store.ingest(paid("Ridgefield Weddings and Events"));
    const { buildDraft } = await import("./onboarding-plan.mjs");
    await store.activate("Ridgefield Weddings and Events", {
      offers: ["elevate"],
      draft: buildDraft({ offers: ["elevate"] }),
    });
    return store;
  };

  it("still accepts a date AFTER the setup batch is approved", async () => {
    /* THE DEFECT THIS COVERS. Approving the pre-booking batch used to lock
       the schedule out permanently — the date call accepted only DRAFTED —
       which made the two-wave design impossible to actually run. */
    const store = await drafted();
    const approved = await store.approve("Ridgefield Weddings and Events", {});
    expect(approved.state).toBe("APPROVED");
    expect(approved.provisioned).toBe(true);

    const { computed, client } = await store.applyAnchorDate("Ridgefield Weddings and Events", {
      anchor: "leadlock_kickoff",
      date: "2026-03-25",
    });
    expect(computed).toBeGreaterThan(0);
    expect(client.state).toBe("APPROVED");
  });

  it("records the scheduling wave as its own approval", async () => {
    const store = await drafted();
    await store.approve("Ridgefield Weddings and Events", {});
    await store.applyAnchorDate("Ridgefield Weddings and Events", {
      anchor: "leadlock_kickoff",
      date: "2026-03-25",
    });
    const scheduled = await store.approve("Ridgefield Weddings and Events", {
      wave: "schedule",
    });
    expect(scheduled.state).toBe("SCHEDULED");
    expect(scheduled.scheduleApprovedAt).toBeTruthy();
  });

  it("re-opens for approval when a booked call moves again", async () => {
    const store = await drafted();
    await store.approve("Ridgefield Weddings and Events", {});
    await store.applyAnchorDate("Ridgefield Weddings and Events", {
      anchor: "leadlock_kickoff",
      date: "2026-03-25",
    });
    await store.approve("Ridgefield Weddings and Events", { wave: "schedule" });

    const { client } = await store.applyAnchorDate("Ridgefield Weddings and Events", {
      anchor: "leadlock_kickoff",
      date: "2026-04-01",
    });
    expect(client.state).toBe("APPROVED");
  });
});

describe("wave 2 — warning hygiene", () => {
  it("drops the waiting-on-this-anchor warning once the date exists", async () => {
    const store = await openSeeded();
    await store.ingest(signed("Ridgefield Weddings and Events"));
    await store.ingest(paid("Ridgefield Weddings and Events"));
    const { buildDraft } = await import("./onboarding-plan.mjs");
    await store.activate("Ridgefield Weddings and Events", {
      offers: ["elevate"],
      draft: buildDraft({ offers: ["elevate"] }),
    });

    const before = store.read().clients[0].draft;
    expect(before.anchorWarnings.leadlock_kickoff).toBeTruthy();

    const { client } = await store.applyAnchorDate("Ridgefield Weddings and Events", {
      anchor: "leadlock_kickoff",
      date: "2026-03-25T00:00:00.000Z",
    });
    expect(client.draft.anchorWarnings.leadlock_kickoff).toBeUndefined();
    /* The ads kickoff is still unbooked, so its line must survive. */
    expect(client.draft.anchorWarnings.ads_kickoff).toBeTruthy();
    /* The Ads Manager warnings are still true and must survive. */
    expect(client.draft.warnings.some((w) => /Ads Manager/.test(w))).toBe(true);
  });
});

/* ────────────────────────────────────────────────────────────────
   Steps 2-4 — the Drive / email / Slack progression that opens once
   the ClickUp batch is approved.
   ──────────────────────────────────────────────────────────────── */
describe("steps 2-4", () => {
  const PROJECT = "Ridgefield Weddings and Events";

  /** A record standing at step 1 with a real draft on it. */
  const drafted = async ({ kickoffDate } = {}) => {
    const store = await openSeeded();
    await store.ingest(signed(PROJECT));
    await store.ingest(paid(PROJECT));
    const { buildDraft } = await import("./onboarding-plan.mjs");
    await store.activate(PROJECT, {
      offers: ["elevate"],
      draft: buildDraft({ offers: ["elevate"], projectName: PROJECT, kickoffDate }),
    });
    return store;
  };

  /** …and past it, with steps 2-4 open. */
  const staged = async ({ kickoffDate, adsKickoffDate } = {}) => {
    const store = await drafted({ kickoffDate });
    const client = store.read().clients[0];
    await store.approve(PROJECT, { draft: client.draft });
    const { buildStagePlans } = await import("./onboarding-stages.mjs");
    await store.initStages(PROJECT, {
      stages: buildStagePlans({
        projectName: PROJECT,
        firstName: "Scott",
        offers: ["elevate"],
        templates: client.draft.templates,
        kickoffDate,
        /* Ridgefield's real ads kickoff — 34 days AFTER its LeadLock one, and
           the reverse of what their own welcome email asks for. */
        adsKickoffDate: adsKickoffDate ?? null,
        offerLabel: "ELEVATE",
      }),
    });
    return store;
  };

  it("will not open the steps before the ClickUp batch is approved", async () => {
    /* Approving step 1 is the commitment. Opening the rest first would let a
       reviewer authorise a Slack announcement for an onboarding nobody has
       agreed to run. */
    const store = await drafted();
    await expect(store.initStages(PROJECT, { stages: [] })).rejects.toMatchObject({
      code: "invalid_state",
      status: 409,
    });
  });

  it("opens all three steps in flow order, whatever order they arrive in", async () => {
    const store = await staged();
    const client = store.read().clients[0];
    expect(client.stages.map((s) => s.key)).toEqual(["drive", "email", "slack"]);
    expect(client.stages.every((s) => s.state === "OPEN")).toBe(true);
    /* Step 1's meaning is untouched: it still approves, and still sets the
       flag that makes month 2 of a retainer inert. */
    expect(client.state).toBe("APPROVED");
    expect(client.provisioned).toBe(true);
  });

  it("is idempotent, so a retried approval cannot discard a reviewer's edits", async () => {
    const store = await staged();
    const before = store.read().clients[0].stages[0].plan;
    const edited = { ...before, items: before.items.slice(0, 2) };
    await store.updateStage(PROJECT, { stage: "drive", plan: edited });

    const { buildStagePlans } = await import("./onboarding-stages.mjs");
    await store.initStages(PROJECT, {
      stages: buildStagePlans({
        projectName: PROJECT,
        offers: ["elevate"],
        templates: ["ads", "leadlock"],
      }),
    });
    expect(store.read().clients[0].stages[0].plan.items).toHaveLength(2);
  });

  it("records what a reviewer authorised, including the rows they dropped", async () => {
    const store = await staged();
    const plan = store.read().clients[0].stages[0].plan;
    const dropped = {
      ...plan,
      items: plan.items.map((item, i) => (i === 0 ? { ...item, include: false } : item)),
    };
    const client = await store.approveStage(PROJECT, { stage: "drive", plan: dropped });
    const stage = client.stages.find((s) => s.key === "drive");
    expect(stage.state).toBe("APPROVED");
    expect(stage.approvedAt).toBeTruthy();
    /* The excluded row survives on the record — "will not create" is half of
       what makes the gate reviewable. */
    expect(stage.approvedPlan.items).toHaveLength(plan.items.length);
    expect(stage.approvedPlan.items[0].include).toBe(false);
  });

  it("refuses to approve the same step twice", async () => {
    const store = await staged();
    const plan = store.read().clients[0].stages[0].plan;
    await store.approveStage(PROJECT, { stage: "drive", plan });
    await expect(store.approveStage(PROJECT, { stage: "drive", plan })).rejects.toMatchObject({
      code: "invalid_state",
      status: 409,
    });
  });

  it("refuses edits to an approved step", async () => {
    const store = await staged();
    const plan = store.read().clients[0].stages[0].plan;
    await store.approveStage(PROJECT, { stage: "drive", plan });
    await expect(store.updateStage(PROJECT, { stage: "drive", plan })).rejects.toMatchObject({
      code: "invalid_state",
    });
  });

  it("404s on a step that does not exist", async () => {
    const store = await staged();
    await expect(
      store.updateStage(PROJECT, { stage: "carrier-pigeon", plan: {} }),
    ).rejects.toMatchObject({ code: "unknown_stage", status: 404 });
  });

  /* ── the gate ─────────────────────────────────────────────────── */

  it("gates Slack until BOTH kickoffs are booked, and refuses to approve it", async () => {
    /* Their own team brief names two kickoff dates. Approving while the gate
       stands would authorise posting two messages full of placeholders. */
    const store = await staged();
    const slack = store.read().clients[0].stages.find((s) => s.key === "slack");
    expect(slack.plan.gate).not.toBeNull();
    expect(slack.plan.gate.label).toMatch(/LeadLock kickoff and the ads kickoff/);
    expect(slack.plan.messages.some((m) => m.body.includes("(DATE)"))).toBe(true);
    await expect(
      store.approveStage(PROJECT, { stage: "slack", plan: slack.plan }),
    ).rejects.toMatchObject({ code: "stage_gated", status: 409 });
  });

  it("still gates on the ads kickoff when only step 1's anchor is known", async () => {
    /* THE BUG THIS PINS: step 1 collects ONE date and it is the LEADLOCK
       kickoff (its phase cadence was recovered from Ridgefield's LeadLock
       list). Ridgefield's ads kickoff was 34 days later, and their own welcome
       email asks for the reverse order — so the second date can never be
       derived from the first. */
    const store = await staged({ kickoffDate: "2026-03-25" });
    const slack = store.read().clients[0].stages.find((s) => s.key === "slack");
    expect(slack.plan.gate).not.toBeNull();
    expect(slack.plan.gate.label).toBe("Waiting on the ads kickoff");
    expect(slack.plan.anchors).toEqual({ leadlock: "2026-03-25", ads: null });
  });

  it("clears the gate and renders both real dates once both anchors are in", async () => {
    const store = await staged({ kickoffDate: "2026-03-25", adsKickoffDate: "2026-04-28" });
    const slack = store.read().clients[0].stages.find((s) => s.key === "slack");
    expect(slack.plan.gate).toBeNull();
    expect(slack.plan.messages.every((m) => !m.body.includes("(DATE)"))).toBe(true);
    const brief = slack.plan.messages.find((m) => m.id === "slack-post-brief");
    /* Each date against its own call, in their template's own order. */
    expect(brief.body).toContain("Ads Kickoff Call for Tuesday, April 28");
    expect(brief.body).toContain("LeadLock Kickoff call for Wednesday, March 25");
    /* The ads timeline counts weeks from the ADS kickoff, not the LeadLock one. */
    const timeline = slack.plan.messages.find((m) => m.id === "slack-post-timeline");
    expect(timeline.body).toContain("Week 1 (Apr 28");
  });

  /* ── the late kickoff ─────────────────────────────────────────── */

  it("counts each date once when draft and approvedBatch are the same object", async () => {
    /* approve() assigns one batch to both fields, so an unconditional /2
       halved the count and an unconditional double-walk doubled it. */
    const store = await staged();
    const { computed, client } = await store.recordKickoff(PROJECT, {
      kickoffDate: "2026-03-25T00:00:00.000Z",
    });
    const dated = client.approvedBatch.tasks.filter((t) => t.dueState === "dated").length;
    expect(computed).toBe(dated);
    expect(computed).toBeGreaterThan(50);
    expect(client.approvedBatch.kickoffDate).toBe("2026-03-25");
  });

  it("still never dates a client-gated task", async () => {
    const store = await staged();
    const { client } = await store.recordKickoff(PROJECT, { kickoffDate: "2026-03-25" });
    const gated = client.approvedBatch.tasks.filter((t) => t.dueState === "gated");
    expect(gated.length).toBeGreaterThan(0);
    for (const task of gated) expect(task.dueDate).toBeNull();
  });

  it("refuses to schedule from here before step 1 is approved", async () => {
    const store = await drafted();
    await expect(
      store.recordKickoff(PROJECT, { kickoffDate: "2026-03-25" }),
    ).rejects.toMatchObject({ code: "invalid_state", status: 409 });
  });

  it("rejects an unparseable date rather than nulling every due date", async () => {
    const store = await staged();
    await expect(
      store.recordKickoff(PROJECT, { kickoffDate: "next Tuesday" }),
    ).rejects.toMatchObject({ code: "invalid_date" });
  });

  /* ── durability ───────────────────────────────────────────────── */

  it("survives a reload with step state, approvals and message bodies intact", async () => {
    const store = await staged({ kickoffDate: "2026-03-25" });
    const plan = store.read().clients[0].stages[0].plan;
    await store.approveStage(PROJECT, { stage: "drive", plan });
    await store.flush();

    const reopened = open();
    const client = reopened.read().clients[0];
    const [drive, email, slack] = client.stages;
    expect(drive.state).toBe("APPROVED");
    expect(email.state).toBe("OPEN");
    expect(slack.plan.messages).toHaveLength(2);
    expect(slack.plan.messages[0].body).toContain("@channel");
  });

  it("drops an unknown step key on read rather than trusting the file", async () => {
    const store = await staged();
    await store.flush();
    const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
    parsed.clients[0].stages.push({
      key: "smoke-signal",
      state: "OPEN",
      plan: { key: "smoke-signal" },
    });
    fs.writeFileSync(file, JSON.stringify(parsed));

    const reopened = open();
    expect(reopened.read().clients[0].stages.map((s) => s.key)).toEqual([
      "drive",
      "email",
      "slack",
    ]);
  });
});

describe("the destination is decided by the package, not by click order", () => {
  it("gives the same space whichever order the offers were picked", async () => {
    const { resolveDestination } = await import("./onboarding-plan.mjs");
    expect(resolveDestination(["leadlock", "ads"]).space).toBe(
      resolveDestination(["ads", "leadlock"]).space,
    );
  });

  it("refuses to send new work into an archive", async () => {
    const { resolveDestination, FORBIDDEN_SPACES } = await import("./onboarding-plan.mjs");
    const full = resolveDestination(["full_service"]);
    expect(full.space).toBeNull();
    expect(full.manualSetup).toBe(true);
    expect(FORBIDDEN_SPACES).toContain("ARCHIVES - Full Service");
  });

  it("does not treat an accelerator space as a managed-service destination", async () => {
    const { resolveDestination } = await import("./onboarding-plan.mjs");
    for (const offers of [["ads"], ["google_accelerator"], ["meta_accelerator"]]) {
      const d = resolveDestination(offers);
      expect(d.space).not.toBe("Google Search Accelerator");
      expect(d.manualSetup).toBe(true);
    }
  });

  it("blocks approval readiness while the destination is unagreed", async () => {
    const { buildDraft, summarizeDraft } = await import("./onboarding-plan.mjs");
    const draft = buildDraft({ offers: ["ads"] });
    const summary = summarizeDraft(draft);
    expect(summary.blockers.some((b) => b.kind === "destination")).toBe(true);
  });
});

describe("the draft keeps the context ClickUp already holds", () => {
  it("carries the parent relationship, not just the fact of one", async () => {
    const { buildDraft } = await import("./onboarding-plan.mjs");
    const draft = buildDraft({ offers: ["elevate"] });
    const child = draft.tasks.find((t) => t.isSubtask);
    expect(child.parentId).toBeTruthy();
    expect(child.parentTitle).toBeTruthy();
    expect(draft.tasks.some((t) => t.id === child.parentId)).toBe(true);
  });

  it("separates a task waiting for a call from one with no rule at all", async () => {
    const { buildDraft } = await import("./onboarding-plan.mjs");
    const draft = buildDraft({ offers: ["elevate"] });
    expect(draft.tasks.some((t) => t.dueState === "awaiting_anchor")).toBe(true);
    expect(draft.tasks.some((t) => t.dueState === "unscheduled")).toBe(true);
  });

  it("marks the tasks one shared provisioning run already satisfies", async () => {
    const { buildDraft, provisioningOverlap } = await import("./onboarding-plan.mjs");
    const draft = buildDraft({ offers: ["elevate"] });
    const overlap = provisioningOverlap(draft);
    /* Both lists contain a "Create Slack Channel" — running both would make
       the channel twice, which is what ON-04 exists to prevent. */
    expect(Object.keys(overlap).length).toBeGreaterThan(1);
    expect(Object.values(overlap)).toContain("slack_channel");
  });
});
