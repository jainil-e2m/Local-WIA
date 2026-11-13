---
key: checkin
name: Programme check-in (1:1)
order: 50
detect: ['check[- ]?in', 'catch[- ]?up', 'touch[- ]?base']
not_if: []
purpose: Re-engage a member and find what's blocking them
type_block: Programme progress
sections: [since, asks, owed, agenda, watch, typeBlock, limits]
blocks:
  last_call: 1
  since_last_call: {max_chars: 5000}
  owed: {max_chars: 5000}
  email_since: {max_chars: 10000, max_threads: 8}
  internal_slack: {max_chars: 6000}
  leads: true
  ads: true
length: {points: 3, questions: 3, watch: 2, highlights: 3}
leave_out_terms: [programme-wide]
model: {reasoning: low}
---
## This call must decide
What is blocking them, and one concrete next step with a date.

## Agenda skeleton
1. What's getting in the way
2. Pick one concrete next step
3. Confirm the next session

## Leave out
Programme-wide news.

## Guidance
Be warm and specific: what is blocking them, and one small next step. Don't assume missed sessions mean unhappiness.

## Type-specific block
- What's waiting on whom
- Programme progress, as far as the tasks show
