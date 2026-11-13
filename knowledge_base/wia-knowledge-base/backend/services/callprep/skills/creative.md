---
key: creative
name: Creative review
order: 60
detect: ['creative', 'landing page review', 'page review', 'ad review']
not_if: []
purpose: Approve creative and page changes
type_block: Approvals & voice
sections: [since, asks, owed, agenda, typeBlock, limits]
blocks:
  last_call: 1
  since_last_call: {max_chars: 5000}
  owed: {max_chars: 6000}
  email_since: {max_chars: 12000, max_threads: 10}
  internal_slack: {max_chars: 8000}
  profile: [Voice, Differentiators & proof]
length: {points: 5, questions: 3, watch: 2, highlights: 3}
leave_out_terms: [inquiries, tours, booked, cost per lead]
model: {reasoning: low}
---
## This call must decide
Which pieces are approved, what changes on the rest, and the next delivery date.

## Agenda skeleton
1. What's ready to review
2. Feedback and decisions
3. Approval and next delivery date

## Leave out
Lead numbers and ad performance.

## Guidance
List exactly what is ready for approval (from the open tasks and Slack) and the decision needed on each. Keep the client's voice notes from the profile next to each item.

## Type-specific block
- Each item waiting for approval, with its task
- Voice: words to use and words to avoid, from the profile
