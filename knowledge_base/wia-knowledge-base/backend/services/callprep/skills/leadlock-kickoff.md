---
key: leadlock-kickoff
name: LeadLock kickoff
order: 20
detect: ['lead\s*lock\s*(kick-?off|onboarding|setup|build)']
not_if: ['lead\s*lock\s*demo']
purpose: Plan the LeadLock build
type_block: CRM & setup facts
sections: [since, asks, owed, agenda, watch, typeBlock, limits]
blocks:
  last_call: 1
  since_last_call: {max_chars: 5000}
  owed: {max_chars: 6000}
  email_since: {max_chars: 14000, max_threads: 10}
  internal_slack: {max_chars: 8000}
  leads: true
  profile: [Business, Ideal client]
length: {points: 5, questions: 3, watch: 2, highlights: 3}
leave_out_terms: [ad spend, cost per lead, CPC, CTR]
model: {reasoning: low}
---
## This call must decide
What WIA sets up and what stays with the client, who answers new inquiries, and the setup milestones with dates.

## Agenda skeleton
1. Current inquiry workflow and CRM
2. Who answers new inquiries
3. What WIA sets up and what stays with the client
4. Setup milestones

## Leave out
Ads strategy and ad performance.

## Guidance
Make the split between WIA's setup work and the client's own work explicit. Flag any missing CRM, form, calendar or access detail as a question. If the leads block shows the sub-account is already linked, say what it shows; otherwise say it isn't linked yet.

## Type-specific block
- Current CRM and inquiry workflow, as far as the sources say
- Who answers inquiries today
- Forms, calendar and access still missing
