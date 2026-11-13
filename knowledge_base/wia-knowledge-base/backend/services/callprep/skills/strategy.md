---
key: strategy
name: Monthly strategy
order: 70
detect: ['monthly strategy', 'strategy (call|meeting|session)', 'monthly (meeting|review|consulting|reporting)', 'strategy']
not_if: ['consultation', '\bdemo\b', 'coffee chat', 'discovery call']
purpose: Review the month and plan the next
type_block: Results & ads context
sections: [since, asks, owed, agenda, questions, watch, opportunity, typeBlock, limits]
blocks:
  last_call: 2
  since_last_call: {max_chars: 8000}
  owed: {max_chars: 6000}
  email_since: {max_chars: 16000, max_threads: 12}
  internal_slack: {max_chars: 10000}
  leads: true
  ads: true
  profile: [Goals, Offer]
length: {points: 5, questions: 3, watch: 2, highlights: 4}
leave_out_terms: [onboarding checklist, questionnaire]
model: {reasoning: low}
---
## This call must decide
Whether next month's plan changes (budget, focus, creative), based on how inquiries are turning into tours and bookings and what the ad figures show.

## Agenda skeleton
1. The client's open questions first
2. What we delivered since the last call and what's next
3. Results and what they mean
4. Decisions needed

## Leave out
Onboarding detail. Tasks the client doesn't need to hear about. Internal tooling problems unless they changed results (mark those internal).

## Guidance
Start with the client's open questions. Explain results in plain language against WIA's playbook thresholds (Google: CTR 3–5%, conversion rate under about 3.5% needs attention, 40% or more impression share lost to budget means budget is limiting; Meta: link CTR at least 1%, landing page views at least half of link clicks, landing page conversion about 1–3%) and label interpretations as interpretations. Use only the figures in the ads and leads blocks. If the last client email signals stress or bad news, say so in the risk and suggest a lighter call. One opportunity at most, and only when something the client said supports it.

## Type-specific block
- Spend, leads and cost per lead per platform: last 30 days against the 30 before (from the ads block)
- Inquiries, tours and booked: last 30 days against the 30 before (from the leads block)
- Say "not connected" for any platform the ads block marks so
