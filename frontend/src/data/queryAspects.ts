/**
 * The seven intent aspects an AI Presence query set is generated across.
 *
 * Ported from f-o_ai_readiness (`src/utils/aiVisibility.js`), where the same
 * seven drive the review UI. `aspectKey` is the contract — it is what
 * `GET /audits/:id/queries` returns per row and what the confirm payload sends
 * back, so it matches `query_aspects.aspect_key` in that service's database.
 * `aspectNumber` is only a display order and a bucketing key; note it is
 * deliberately NOT the array order — Use Case sits third by number but fifth in
 * the reading order the review screen wants.
 */

export interface QueryAspect {
  aspectNumber: number;
  aspectKey: string;
  title: string;
}

export const QUERY_ASPECTS: readonly QueryAspect[] = [
  { aspectNumber: 1, aspectKey: "brand_entity_recognition", title: "Entity / Brand Discovery" },
  { aspectNumber: 2, aspectKey: "core_solution_keyword", title: "Core Offering / Solution Intent" },
  { aspectNumber: 4, aspectKey: "persona_audience", title: "Target Audience / Persona" },
  { aspectNumber: 5, aspectKey: "local_geographic", title: "Geography / Local Intent" },
  { aspectNumber: 3, aspectKey: "situation_problem_trigger", title: "Use Case / Job-to-be-Done" },
  { aspectNumber: 6, aspectKey: "competitive_comparative", title: "Comparison / Alternatives" },
  { aspectNumber: 7, aspectKey: "trust_validation", title: "Trust / Proof / Decision Support" },
];

export const QUERY_ASPECT_BY_NUMBER: Record<number, QueryAspect> = Object.fromEntries(
  QUERY_ASPECTS.map((aspect) => [aspect.aspectNumber, aspect]),
);

export const QUERY_ASPECT_BY_KEY: Record<string, QueryAspect> = Object.fromEntries(
  QUERY_ASPECTS.map((aspect) => [aspect.aspectKey, aspect]),
);

/** Where an unrecognised query lands — Core Offering is the broadest bucket. */
export const FALLBACK_ASPECT_NUMBER = 2;
