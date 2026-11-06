# WIA Content Atelier — System Agenda & View Architecture

<!-- governing-plan-note -->
> **Historical (marked 18 October 2026, plan item S.B9).** This document is kept for traceability. The one governing plan is [the implementation plan](../backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md) (revision 6.1 or later); where they differ, the plan wins. Do not plan from this document.

## Executive Overview

**The Content Atelier** is a weekly intelligence and content synthesis engine custom-engineered for **Wedding Industry Ads (WIA)**. 

### The Core Problem It Solves
Whitney (Founder & Creative Director) and Giselle (Content Producer) spend dozens of hours manually reviewing client call transcripts, Slack wins, and market trends, or experiencing "blank-page syndrome." 

The Atelier turns unstructured raw inputs into ranked, research-backed, multi-format weekly content packs (Email, Carousel, 3 Reels scripts, Captions) with **under 10 minutes of total weekly review time for Whitney** across 3 lightweight approval gates.

---

## The Weekly Cadence (The Operating Rhythm)

```
[ CONTINUOUS INGESTION ]
Zoom / Fathom Calls + Slack Wins + Whitney Voice Notes
           │
           ▼
[ STAGE 1 & 2: THE MOMENTS LEDGER ]
Verbatim quote extraction, audio timestamps, client context & privacy clearance tagging
           │
           ▼
[ STAGE 3: THE IDEAS & ANGLES ENGINE (GATE 1) ]
4-Factor Scoring (Offer Fit, Recurrence, Novelty, Demand) ───► Whitney Angle Approval (~2 min)
           │
           ▼
[ STAGE 4 & 5: RESEARCH LAB & BRIEF FORMULATION (GATE 2) ]
SerpAPI People Also Ask + Google Trends + Message Spine ───► Whitney Brief Approval (~5 min)
           │
           ▼
[ STAGE 6: CONTENT PACKS SUITE (GATE 3 / GISELLE HANDOFF) ]
Founder Email + Carousel Slides + 3 Video Reels + Captions ───► Production Export (Canva / Descript)
```

---

## Comprehensive Agenda for Each & Every View

### 1. View: `Home` (The Weekly Executive Cockpit)
* **Target User:** Whitney (Weekly Review), Giselle (Production Glance)
* **Time to Complete:** ~3 minutes
* **Core Agenda:**
  - **Weekly Triage at a Glance:** Instantly shows Whitney the highest-ranked ideas mined this week from recent calls and Slack channels.
  - **Quick Metrics:** Count of fresh moments mined, pending approval gates, and production status.
  - **Fast-Filter Segmented Controls:** Filter ideas by source (`Top Ranked`, `Client Calls`, `Slack Wins`, `Saved Favorites`).
  - **Global Command & Search:** Rapid keyboard-driven lookup (`⌘K`) across client names, moments, angles, and transcript snippets.
  - **Direct Escalation:** Instant click into any card opens the 3-Gate Workbench Modal.

---

### 2. View: `Moments` (The Moments Ledger / Raw Intelligence Vault)
* **Target User:** System Automation, Whitney (Reviewing client quotes), Giselle (Mining context)
* **Time to Complete:** As needed / Continuous background
* **Core Agenda:**
  - **Atomic Knowledge Repository:** Every single client advisory call (Fathom), Zoom strategy session, and Slack `#wins` post is parsed into atomic verbatim moments.
  - **Speaker & Context Verification:** Identifies who said it, timestamp in the recording, and the client's business tier (e.g. Luxury Planner, Florist, Venue).
  - **Consent & Anonymisation Clearance:** Flags whether a quote can be published directly, needs explicit client consent, or must be anonymised into an industry archetype.
  - **Moment Promotion Action:** One-click promotion from a raw quote directly into a structured candidate Content Angle.

---

### 3. View: `Ideas` (Angles Pipeline & 4-Factor Ranking)
* **Target User:** Whitney & Giselle
* **Time to Complete:** ~3 minutes
* **Core Agenda:**
  - **Synthesizing Angles:** Takes raw moments and translates them into magnetic, high-authority marketing angles tailored to the luxury wedding audience.
  - **4-Vector Ranking Algorithm (The Atelier Score):**
    1. *Offer Fit (30%):* Does this directly lead to WIA's core offers (Elevate, Accelerators, LeadLock)?
    2. *Recurrence (25%):* How frequently has this obstacle or objection surfaced across calls this month?
    3. *Novelty (25%):* Is this a fresh contrarian take, or tired advice already saturating Instagram?
    4. *Market Demand (20%):* Are wedding vendors actively searching for this on Google & TikTok?
  - **CTA Alignment:** Automatically pairs the angle with the most effective WIA conversion funnel.

---

### 4. View: `Research` (The Intelligence Lab & SerpAPI Grounding)
* **Target User:** Whitney (Insight validation), Giselle (Contextual depth)
* **Time to Complete:** ~2 minutes
* **Core Agenda:**
  - **Search & Market Signals (SerpAPI):** Integrates live Google Trends indexes, query breakout patterns, and "People Also Ask" questions.
  - **Competitor & Discourse Gap Analysis:** Identifies what generic marketing coaches are preaching vs. what actually works for high-ticket $15k+ wedding bookings.
  - **Proof & Evidence Vault:** Gathers relevant benchmarks and data points to substantiate bold claims in the content, ensuring zero generic "slop."

---

### 5. View: `Content Packs` (The Multi-Asset Production Vault)
* **Target User:** Giselle (Production & Scheduling), Whitney (Final Sign-off)
* **Time to Complete:** Ongoing production
* **Core Agenda:**
  - **Complete 4-in-1 Asset Suite:** Displays fully-generated content suites derived from approved briefs:
    1. **Founder Email:** High-open story-driven newsletter ready for Klaviyo / Flodesk.
    2. **Educational Carousel:** Slide-by-slide graphic layout, headline hooks, visual composition notes, and swipe callouts.
    3. **3 Reels / Short-Form Video Scripts:** Hook (first 3 seconds), body with talking head or b-roll direction, sound recommendation, and audio pacing.
    4. **Captions & Engagement Prompts:** Ready-to-copy captions with conversation starters and comment triggers.
  - **One-Click Export:** Copy individual components with formatting intact or export all assets for Figma/Canva and Descript.

---

### 6. View: `Inbox & Approvals` (The 3-Gate Executive Decision Desk)
* **Target User:** Whitney (Strictly 5–10 minutes per week)
* **Time to Complete:** 5–10 minutes on designated "Review Day"
* **Core Agenda:**
  - **Frictionless Executive Approval:** Dedicated view structured specifically to prevent approval fatigue.
  - **Gate 1 (Pick the Angle - 2 min):** Whitney approves or steers the top 3 weekly angles and sets the CTA.
  - **Gate 2 (Approve the Brief - 5 min):** Whitney reviews the 3-point message spine, answers any open steering questions, and clears claim privacy.
  - **Gate 3 (Approve the Content Pack - 3 min):** Whitney or Giselle approves the final draft before publishing.
  - **Status Badges & Progress Indicators:** Clearly separates items awaiting Whitney's review from items currently in Giselle's production queue.

---

### 7. View: `Brand Kit & Voice Vault` (The Ground Truth Configuration)
* **Target User:** Whitney, Giselle, AI Prompt System
* **Time to Complete:** Setup once, update quarterly
* **Core Agenda:**
  - **Whitney’s Voice Profile:** Ground rules on tone (authoritative, chic, anti-hustle, unapologetic, luxury-focused).
  - **Anti-Words & Slop Filter:** Explicit list of banned generic phrases (e.g., "In today's fast-paced world", "Elevate your game", "Game changer", "Dive deep").
  - **Core Offer Architecture:** Value propositions and target customer avatars for Elevate, Accelerators, and LeadLock.
  - **Client Clearance Whitelist:** Pre-approved client case studies and guidelines for sensitive revenue disclosures.
