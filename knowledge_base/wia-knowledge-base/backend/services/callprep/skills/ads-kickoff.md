---
key: ads-kickoff
name: Ads kickoff
order: 10
detect: ['ads?\s*kick-?off']
not_if: []
purpose: Introductions, set expectations, connect ad accounts
type_block: Access checklist & what was sold
sections: [owed, agenda, questions, typeBlock, limits]
blocks:
  owed: {max_chars: 6000}
  email_since: {max_chars: 12000, max_threads: 10}
  internal_slack: {max_chars: 6000}
  ads: true
  profile: [Business, Offer, Goals]
length: {points: 4, questions: 4, watch: 2, highlights: 3}
leave_out_terms: [cost per lead, ROAS, price, pricing]
model: {reasoning: low}
---
## This call must decide
Who does what on both sides, which ad accounts still need access, and the date of the next step (usually the messaging interview).

## Agenda skeleton
1. Introductions and who does what
2. How the work runs and what to expect
3. Connect ad accounts live
4. Next steps and the messaging interview

## Leave out
Performance figures, strategy opinions and price.

## Guidance
Keep it practical. List what was sold and which ad accounts the ads block shows as connected or missing. Every onboarding task waiting on the client goes in the talking points with its due date. No performance talk yet.

## Type-specific block
- Ad accounts: which platforms the ads block shows as connected to this client, and which are missing
- What was sold (from the profile or the onboarding tasks)
- Onboarding steps waiting on the client
