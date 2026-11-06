# WIA Meeting Analysis

Analysis of every meeting between E2M and Wedding Industry Ads (WIA), one meeting at a time.

## Layout

```
WIA_Meeting_Analysis/
├── README.md              ← this file + meeting index
├── _template.md           ← structure every per-meeting analysis follows
├── running_threads.md     ← cross-meeting ledger: decisions, commitments, open questions, corrections
├── access_wia.md          ← every access received from WIA: scope, where the credential lives (never the secret), how to revoke
├── viktor_at_wia.md       ← everything WIA uses Viktor (viktor.com, its Slack AI agent) for, by category: the incumbent to beat
├── viktor_samples.md      ← checklist of the 32 Viktor samples to gather: where each comes from, and collection status
├── received/              ← materials WIA sent, filed by date (e.g. 2026-09-08_chatgpt-project: custom instructions + 3 playbooks)
└── meetings/
    └── YYYY-MM-DD_short-topic/
        ├── source.*       ← transcript / recording / notes as provided
        └── analysis.md    ← analysis built from _template.md
```

Each new meeting gets its own folder. After its analysis is written, `running_threads.md`
is updated so commitments get closed out and superseded facts get flagged.

## Meeting index

| # | Date | Topic | Attendees | Analysis |
|---|------|-------|-----------|----------|
| 00 | 2026-08-11 | Discovery / sales call: Apollo pitch → switched to Audit & Blueprint | WIA: Whitney, Daniela · E2M: Kevin, Khushbu | [analysis](meetings/2026-08-11_discovery-call/analysis.md) |
| 01 | 2026-08-26 | Assessment kickoff: roll call + Gmail triage; Whitney widens the brief to onboarding, action-item chase, content | WIA: Whitney, Gisselle · E2M: Asha, Minu, Jainil | [analysis](meetings/2026-08-26_assessment-kickoff/analysis.md) |
| 02 | 2026-09-02 | Ops wrap-up + onboarding lifecycle: Dubsado trigger, Slack-not-ClickUp, Zoom-not-Fathom, Tina's monthly reporting | WIA: Whitney, Gisselle · E2M: Asha, Minu | [analysis](meetings/2026-09-02_ops-and-onboarding/analysis.md) |
| 03 | 2026-09-10 | Blueprint review: 29 automations / 3 phases + Command Center prototype; pricing; "pick two"; Whitney leaning Apollo | WIA: Whitney, Gisselle · E2M: Minu, Asha | [analysis](meetings/2026-09-10_blueprint-review/analysis.md) |
| 04 | 2026-09-16 | Content engine scoping: picks = Content → Reporting → KB; inputs/outputs locked; payment consent; OpenRouter + Railway | WIA: Whitney · E2M: Minu, Asha | [analysis](meetings/2026-09-16_content-engine-scoping/analysis.md) |
| 05 | 2026-09-22 | Knowledge base scoping: team named (Nandini, Jainil); Zoom keeps transcripts; `hello@` + 2FA handed over; Viktor is the incumbent; meeting > ClickUp rule | WIA: Whitney, Gisselle · E2M: Asha, Minu, Nandini, Jainil | [analysis](meetings/2026-09-22_knowledge-base-scoping/analysis.md) |
