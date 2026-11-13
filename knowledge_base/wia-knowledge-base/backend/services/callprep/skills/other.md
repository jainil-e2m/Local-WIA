---
key: other
name: Other / unclassified
order: 999
detect: []
not_if: ['\bconsultation\b', '\bdemo\b', 'coffee chat', 'discovery call', 'interview with', 'job interview']
purpose: General client call
type_block: ''
sections: [since, asks, owed, agenda, limits]
blocks:
  last_call: 1
  since_last_call: {max_chars: 6000}
  owed: {max_chars: 6000}
  email_since: {max_chars: 12000, max_threads: 10}
  internal_slack: {max_chars: 6000}
  leads: true
  ads: true
length: {points: 4, questions: 2, watch: 2, highlights: 3}
leave_out_terms: []
model: {reasoning: low}
---
## This call must decide
What the client needs from this call, and anything owed either way.

## Agenda skeleton
1. The client's open questions first
2. What we owe and what they owe
3. Decisions needed before the next call

## Leave out
Anything not supported by an approved source.

## Guidance
Summarise recent context and anything owed either way. The call type is unknown: say so in the risk and ask the host to set the type if the purpose is unclear.

## Type-specific block
- None
