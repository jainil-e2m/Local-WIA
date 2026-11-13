---
key: office-hours
name: Office hours (group)
order: 40
detect: ['office\s*hours', 'group coaching', 'roll[- ]?call']
not_if: []
purpose: Programme coaching for several members
type_block: Members expected
sections: [asks, agenda, typeBlock, limits]
blocks:
  owed: {max_chars: 3000}
  internal_slack: {max_chars: 4000}
length: {points: 3, questions: 2, watch: 1, highlights: 2}
leave_out_terms: []
model: {reasoning: low}
---
## This call must decide
One task each for next week.

## Agenda skeleton
1. Quick wins from last week
2. Member questions in turn
3. One task each for next week

## Leave out
Any member's details beyond their own parts.

## Guidance
One short line per expected member. Never show one member's details to another.

## Type-specific block
- Members expected
