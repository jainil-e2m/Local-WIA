# Client Requirements doc (E2M → WIA): content engine access

**Prepared by** Jainil. First version ~Sep 15, which Minu in M04 called "a requirement document like this from Asha probably yesterday". Updated after the Sep 16 scoping call (M04), and this content matches the post-M04 scope. **WIA's reply** is [`reply.md`](reply.md) (the Sep 21 access handover).
*The original's tables have been reformatted into markdown tables. The wording is unchanged, including the sentence that was cut off in the original.*

---

**CLIENT REQUIREMENTS**
Credentials necessary for Automation building for Wedding Industry Ads

## 1. Central Automation Google Account

| TYPE | Data Needed from Client | Purpose | Created By? | Operated By? |
|------|------------------------|---------|-------------|--------------|
| Gmail Account | Central Google Account (ai@weddingindustryads.com) | Centralized Gmail Account for all automations. | Team Wedding Industry Ads | Managed by E2M |

## 2. Automation Requirements

| TYPE | Data Needed from Client | Purpose | Pricing (per execution in USD) | How to Create one? |
|------|------------------------|---------|-------------------------------|--------------------|
| AI Provider Account | OpenRouter Account | To classify E-mail's and Prepare Task Manager | Pay per execution. 1st Recharge 20$. | Access Guide |
| Hosting platform | Railway | To host the Platform | 5$/month | Access Guide |
| Zoom Meeting links | Zoom Call Recordings of past 3 months | To classify meetings as potential Content Generators. | - | - |
| Fathom Meetings | Meeting links of calls where Fathom / any other AI Notetaker was present | To classify meetings as potential Content Generators and gather transcripts for | - | - |
| Knowledge Base Documents: Founder voice document | Document describing Founder (Whitney) voice, tone, and content framework | Ensures generated content matches the founder's voice and structure | - | - |
| Marketing Strategy Document | Content strategy document from outside marketing consultant | Guides topic selection and overall content direction | - | - |
| Historic Monthly Meetings Links / Transcripts | Historic monthly workshop transcripts for accelerator clients (past 3 months) | Provides context on past topics for thematic continuity | - | - |
| ChatGPT Account Access (hello@weddingindustryads.com) | Access to the chatGPT account hello@weddingindustryads.com | To review existing chat history, founder-voice context, and prior conversations for better understanding of the kind of content to be built. | - | To be Shared with ai@weddingindustryads.com via Lastpass |
| Slack Channel - Social Proof and Results | Access to the Slack Channel - Social Proof and Results | To capture client feedback/screenshots the team posts as potential content material | - | |

---

### Notes (added 2026-09-24, not part of the doc)
- **The doc asks for less than M04 scoped.** GHL API / email access, Instagram, Canva, Descript, a Fathom API or Team plan, and speech-to-text **aren't on it**.
  - *Update, Sep 24:* **GHL API access is in place anyway.** **Instagram and Canva were requested separately** through access guides shared with WIA (`access_wia.md`, Request 3).
  - Never requested: the Fathom API or Team plan, speech-to-text, and possibly Descript.
- **The OpenRouter purpose line** ("classify E-mail's and Prepare Task Manager") describes the ops-hub prototype, not the content engine that was actually picked.
- **It does state unit costs**: OpenRouter pay-per-execution with a $20 first top-up; Railway $5/month. That's the first written running-cost figure since M00's "$20–30 hosting". There's still no monthly model-spend estimate or cap.
- **The `hello@` request is written down here, for ChatGPT history only.** M05 (Sep 22) widened it to the calendar, and the 2FA phone widened it to the whole Google account.
