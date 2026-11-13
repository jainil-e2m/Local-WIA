---
key: messaging
name: Messaging & positioning interview
order: 30
detect: ['messaging', 'positioning', 'brand interview']
not_if: []
purpose: Deep-dive on the business, audience and voice
type_block: Questionnaire answers
sections: [asks, agenda, questions, typeBlock, limits]
blocks:
  owed: {max_chars: 3000}
  email_since: {max_chars: 10000, max_threads: 8}
  profile: all
length: {points: 4, questions: 6, watch: 2, highlights: 3}
leave_out_terms: [ad spend, cost per lead, CPC, CTR, campaign budget]
model: {reasoning: low}
---
## This call must decide
The gaps in the client's story, ideal couple, offer and voice that the questionnaire left thin or contradictory.

## Agenda skeleton
1. Their story in their words
2. Ideal couple and objections
3. Offer and what sets them apart
4. Voice: words to use and avoid

## Leave out
Ads and unrelated actions.

## Guidance
Quote the questionnaire in the client's own words when a profile field has it. Questions go only where a profile field is empty, thin or contradicts another. Never invent an answer for an empty field.

## Type-specific block
- Each profile section with what the questionnaire says, or "not answered"
