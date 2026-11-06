import { describe, it, expect } from "vitest";
import {
  buildConfirmQueriesPayload,
  getMaxQueryNumber,
  type QuerySection,
} from "./queryReview";

/**
 * The confirm payload must never repeat a query_number.
 *
 * This is a hard server-side constraint, not a nicety: apply_confirmed_queries
 * rejects the whole submission with 422 "Duplicate query_number values
 * submitted" before it writes anything. A duplicate therefore does not degrade
 * the audit, it blocks the review gate outright — and the gate is the only way a
 * run reaches evaluation, so the audit can never finish.
 *
 * Two client behaviours combine to keep numbers unique, and the risky
 * combination is remove-then-add: removing frees a number while adding needs a
 * new one, so a naive "next = count + 1" would hand out a number that is still
 * in use. useQueryReview.addQuery avoids that by taking
 * max(highest number present, highest ever issued) + 1. These cases pin that
 * invariant to the numbering helpers directly, so a refactor of either one
 * cannot quietly reintroduce the collision.
 */

let aspectCounter = 0;
const section = (aspectKey: string, queries: QuerySection["queries"]): QuerySection => ({
  aspectNumber: ++aspectCounter,
  aspectKey,
  title: aspectKey,
  categoryName: aspectKey,
  queries,
});

/** Mirrors useQueryReview.addQuery's numbering rule. */
const nextNumber = (sections: QuerySection[], highestEverIssued: number) =>
  Math.max(getMaxQueryNumber(sections), highestEverIssued) + 1;

const numbersIn = (sections: QuerySection[]) =>
  buildConfirmQueriesPayload(sections).queries.map((q) => q.query_number);

describe("confirm payload numbering", () => {
  it("keeps numbers unique when a query is removed and another added", () => {
    // The generated set, as the service returns it.
    let sections = [
      section("brand", [
        { query_number: 1, query_text: "who is acme dental" },
        { query_number: 2, query_text: "acme dental reviews" },
      ]),
      section("local", [
        { query_number: 3, query_text: "dentist phoenix" },
        { query_number: 4, query_text: "dentist near me" },
      ]),
    ];

    // Remove the FIRST query — this is the case that frees a low number while
    // higher ones stay in use.
    sections = sections.map((s, i) =>
      i === 0 ? { ...s, queries: s.queries.slice(1) } : s,
    );

    // Then add a replacement, using the hook's rule.
    const added = nextNumber(sections, 0);
    sections = sections.map((s, i) =>
      i === 0 ? { ...s, queries: [...s.queries, { query_number: added, query_text: "new one" }] } : s,
    );

    const numbers = numbersIn(sections);
    expect(new Set(numbers).size).toBe(numbers.length);
    // Specifically: the new query must not reuse a number still in the set.
    expect(added).toBeGreaterThan(4);
  });

  it("keeps numbers unique when the highest query is removed and another added", () => {
    // Removing the highest lowers getMaxQueryNumber, so the rule must also
    // remember the highest number it has already issued.
    let sections = [
      section("brand", [
        { query_number: 1, query_text: "a" },
        { query_number: 2, query_text: "b" },
      ]),
    ];
    let highestEverIssued = 0;

    const first = nextNumber(sections, highestEverIssued);
    highestEverIssued = first;
    sections = [
      section("brand", [...sections[0].queries, { query_number: first, query_text: "c" }]),
    ];

    // Drop that newly added highest one, then add again.
    sections = [section("brand", sections[0].queries.slice(0, -1))];
    const second = nextNumber(sections, highestEverIssued);
    sections = [
      section("brand", [...sections[0].queries, { query_number: second, query_text: "d" }]),
    ];

    const numbers = numbersIn(sections);
    expect(new Set(numbers).size).toBe(numbers.length);
    expect(second).not.toBe(first);
  });

  it("assigns unique numbers to queries that arrive without one", () => {
    // The fallback branch in buildConfirmQueriesPayload. Ported rows and any
    // hand-built section can lack a number entirely.
    const sections = [
      section("brand", [{ query_text: "no number" }, { query_text: "also none" }]),
      section("local", [{ query_text: "third" }]),
    ];

    const numbers = numbersIn(sections);
    expect(numbers).toHaveLength(3);
    expect(new Set(numbers).size).toBe(numbers.length);
  });

  it("drops blank queries instead of submitting them", () => {
    // A blank added query would fail the service's min_length=1 validator and
    // reject the whole set, so it must never reach the payload.
    const sections = [
      section("brand", [
        { query_number: 1, query_text: "real" },
        { query_number: 2, query_text: "   " },
        { query_number: 3, query_text: "" },
      ]),
    ];

    const payload = buildConfirmQueriesPayload(sections);
    expect(payload.queries.map((q) => q.query_text)).toEqual(["real"]);
  });
});
