import type { ContentIdea } from '../types/atelier';
import { prepareFathomContentBrief } from './fathomContentBriefs';
import { hydrateFathomMockPack } from './fathomContentPacks';

// The three user-supplied concepts. Earlier fictional weeks remain in editorialMockData.ts.
export const FATHOM_EDITORIAL_WEEK = '2026-10-19';

const SOURCE_ANGLE_PROPOSALS: ContentIdea[] = [
  {
    "id": "mock-current-week-2026-10-19-1",
    "title": "How we approach a new client's ad budget, and why \"spend more\" isn't our first move",
    "suppliedCopy": {
      "angle": "# How we approach a new client's ad budget, and why \"spend more\" isn't our first move\n\n## Content angle\n\n### Content pillar / type\nATTRACT · Founder-forward and industry authority. It brings to life the team's founder-forward idea that spending more on ads isn't the same as making more, through a real decision.\n\n### Audience\nEstablished wedding pros who are already investing in Google or Meta, whether they run their ads themselves or work with someone, and whose budget has grown faster than their results.\n\n### Why this matters\nThe most common advice in our industry, and from the ad platforms themselves, is to spend more. But a bigger budget only helps once you know what your current budget is actually doing.\n\n### WIA's expertise or process\nWhen we start with a new client, we look at what their existing campaigns are producing before we talk about spending more. We stop what isn't earning its place, reset what has drifted, and put more money behind what proves itself.\n\n### Evidence in the referenced call\nOn a new ELEVATE venue's strategy call, we asked how the director felt about her budget.\n\n- **Her answer:** it had \"crept up over the year\" without \"noticeably better leads.\"\n- **Google:** her campaigns were performing, but you explained that a climbing budget can lead Google to \"read a higher spend as comfort with paying more per lead.\" You reset Google on a fresh campaign at about half the daily budget.\n- **Meta:** you turned off the campaign spending the most, which had no tracked leads: \"spending with no reason behind it isn't a plan.\"\n- **The plan:** \"begin with a smaller budget that earns its place… then scale up from there.\"\n\n### Editorial guardrail / next step\n- Her Google ads were working, so the copy says \"reset,\" never \"fixed.\"\n- No budgets or venue name.\n- No result without her permission.\n- Never criticize whoever built the earlier campaigns.",
      "brief": ""
    },
    "subtitle": "More budget is something your ads should earn. Before we put more money behind a client's advertising, we find out what their current spend is actually doing.",
    "isMock": true,
    "mockLayoutVersion": 5,
    "badge": "Client Call",
    "scoreBasis": "editorial",
    "score": 88,
    "scoresBreakdown": {
      "proof": 88,
      "audiencePain": 95,
      "offerFit": 91,
      "recurrence": 78,
      "novelty": 86,
      "demand": 90
    },
    "daysAgo": "Current week",
    "createdAt": "2026-10-20T06:30:00.000Z",
    "editorialWeek": "2026-10-19",
    "timestamp": "2026-10-20",
    "sourceType": "manual",
    "client": "Anonymised wedding professional",
    "sourceDetails": "Sample strategy call A (anonymised):\n- the budget discussion;\n- targeting, and the campaign that was turned off;\n- the rebuilt Meta structure.",
    "primaryQuote": "More budget is something your ads should earn. Before we put more money behind a client's advertising, we find out what their current spend is actually doing.",
    "suggestedCta": "Elevate",
    "gate": "gate1_angle",
    "editorialContext": {
      "audience": "Established wedding pros who are already investing in Google or Meta, whether they run their ads themselves or work with someone, and whose budget has grown faster than their results.",
      "objective": "ATTRACT. Reach established owners who are already spending on ads, and build trust that WIA isn't an agency chasing bigger budgets. The desired response: \"That's the kind of team I'd trust with my ad budget.\"",
      "funnelStage": "ATTRACT",
      "pillar": "ATTRACT · Founder-forward and industry authority. It brings to life the team's founder-forward idea that spending more on ads isn't the same as making more, through a real decision.",
      "beliefShift": "More budget is something your ads should earn. Before we put more money behind a client's advertising, we find out what their current spend is actually doing.",
      "suggestedInvitation": "CTA: No offer CTA on Instagram (ATTRACT), with a DM \"ADS\" variant for a CONVERT week. A reply in the email.",
      "sources": [],
      "brandReferences": [],
      "externalContext": []
    },
    "angleRationale": {
      "topic": "How we approach a new client's ad budget, and why \"spend more\" isn't our first move",
      "source": "editorial",
      "points": [
        {
          "label": "Content pillar / type",
          "text": "ATTRACT · Founder-forward and industry authority. It brings to life the team's founder-forward idea that spending more on ads isn't the same as making more, through a real decision."
        },
        {
          "label": "Audience",
          "text": "Established wedding pros who are already investing in Google or Meta, whether they run their ads themselves or work with someone, and whose budget has grown faster than their results."
        },
        {
          "label": "Why this matters",
          "text": "The most common advice in our industry, and from the ad platforms themselves, is to spend more. But a bigger budget only helps once you know what your current budget is actually doing."
        },
        {
          "label": "WIA's expertise or process",
          "text": "When we start with a new client, we look at what their existing campaigns are producing before we talk about spending more. We stop what isn't earning its place, reset what has drifted, and put more money behind what proves itself."
        },
        {
          "label": "Evidence in the referenced call",
          "text": "On a new ELEVATE venue's strategy call, we asked how the director felt about her budget.\n\n- Her answer: it had \"crept up over the year\" without \"noticeably better leads.\"\n- Google: her campaigns were performing, but you explained that a climbing budget can lead Google to \"read a higher spend as comfort with paying more per lead.\" You reset Google on a fresh campaign at about half the daily budget.\n- Meta: you turned off the campaign spending the most, which had no tracked leads: \"spending with no reason behind it isn't a plan.\"\n- The plan: \"begin with a smaller budget that earns its place… then scale up from there.\""
        },
        {
          "label": "Editorial guardrail / next step",
          "text": "- Her Google ads were working, so the copy says \"reset,\" never \"fixed.\"\n- No budgets or venue name.\n- No result without her permission.\n- Never criticize whoever built the earlier campaigns."
        }
      ]
    },
    "brief": {
      "coreInsight": "More budget is something your ads should earn. Before we put more money behind a client's advertising, we find out what their current spend is actually doing.",
      "audiencePain": "Owners whose spend has crept up a little at a time while their inquiries haven't noticeably improved, and who are tired of platforms suggesting a bigger daily budget. They believe in advertising and want it to grow their business. They just don't want to waste money doing it.",
      "messageSpine": [
        "Hook: A new client asked to spend less, and an ads agency agreed.",
        "Problems, desires, symptoms: Your budget has crept up. Traffic looks good. Your inquiries aren't noticeably better. The platforms keep suggesting you spend more.",
        "Main point: Budget should follow proof. Find out what each campaign is doing before you scale it.",
        "Transformation: Knowing what your budget is doing, and having a real basis for deciding when to spend more.",
        "CTA: No offer CTA on Instagram (ATTRACT), with a DM \"ADS\" variant for a CONVERT week. A reply in the email."
      ],
      "formatSplit": {
        "emailFocus": "Email: the whole story, how WIA approaches budget across its offers, and a question back to the reader.",
        "carouselFocus": "Carousel: the reader's situation, then the story, then the principle, then a CTA for both ways of working with WIA.",
        "reelsFocus": "Reel 1 (face to camera, story): what we did with a new client's budget, and why.\nReel 2 (face to camera, stance): how we think about budget with new clients.\nReel 3 (b-roll with on-screen text): two lines to stop the scroll; the caption carries the story."
      },
      "contentPlan": {
        "email": "Email: the whole story, how WIA approaches budget across its offers, and a question back to the reader.",
        "carousel": "Carousel: the reader's situation, then the story, then the principle, then a CTA for both ways of working with WIA.",
        "reels": [
          "Reel 1 (face to camera, story): what we did with a new client's budget, and why.",
          "Reel 2 (face to camera, stance): how we think about budget with new clients.",
          "Reel 3 (b-roll with on-screen text): two lines to stop the scroll; the caption carries the story."
        ]
      },
      "claimsRequiringConsent": [
        "- Her Google ads were working, so the copy says \"reset,\" never \"fixed.\"\n- No budgets or venue name.\n- No result without her permission.\n- Never criticize whoever built the earlier campaigns.",
        "Google was performing, so it was reset, not fixed. No budgets, venue names or results."
      ],
      "openQuestionsForWhitney": [
        "SEND TIME: your usual Tuesday morning send (confirm)",
        "RECIPIENTS: full WIA list (confirm segment)"
      ]
    },
    "research": {
      "origin": "editorial",
      "searchQuery": "How we approach a new client's ad budget, and why \"spend more\" isn't our first move",
      "googleTrendsScore": null,
      "trendDirection": null,
      "peopleAlsoAsk": [],
      "autocomplete": [],
      "forumDiscussions": [],
      "note": "Editorial content supplied by the user."
    }
  },
  {
    "id": "mock-current-week-2026-10-19-2",
    "title": "What our strategy calls actually cover, and why the most useful part often isn't about the ads",
    "suppliedCopy": {
      "angle": "# What our strategy calls actually cover, and why the most useful part often isn't about the ads\n\n## Content angle\n\n### Content pillar / type\nWARM · UVP and behind-the-scenes process. It's the team's UVP idea, \"Most agencies run your ads in a vacuum and send you a report. We build an entire system for sales around your ads,\" shown through a real account.\n\n### Audience\nEstablished wedding pros who are running ads, or considering an ads partner, and who book tours or consultations: venues, planners, photographers and entertainment. Especially owners whose current reporting starts and ends with cost per lead.\n\n### Why this matters\nAds can bring couples to you. But what happens between an inquiry and a booked tour or consult depends on things only the owner knows, and that's often where the next layer of results is.\n\n### WIA's expertise or process\nOur strategy calls look at the whole path from inquiry to visit, alongside the ad results. We ask about tours, calendars, team capacity and why couples are lost. Then we turn the answers into the follow-up and messaging we build.\n\n### Evidence in the referenced call\n- **The situation.** At one venue, inquiries and tours were up, and so was ghosting. You opened with \"Good to hear it… so this is the moment to look at the rest.\"\n- **What the owner told you.** Couples who book more than two weeks out often go elsewhere. Saturdays are weddings, and her team is small. The rain plan was a worry for couples, and she showed her rain-plan photos on a tablet during tours.\n- **What you suggested.** A personal video by text, real photos in the first messages, and making the marketing say \"you need to see this venue in person before you decide.\"\n- **Your view.** \"On a call like this, the most useful time goes to the things around the ads.\"\n- **What was built by September.** A welcome video by text, a selfie in the tour confirmation, real photos in the first texts, and extra follow-up for couples whose tours are weeks away.\n\n### Editorial guardrail / next step\n- No funnel numbers.\n- No claim that ghosting dropped.\n- Don't name the venue, the owner, or the former team member who led the analysis.\n- WIA built her follow-up in LeadLock. She runs her own tours and sales.",
      "brief": ""
    },
    "subtitle": "The most useful part of an ads strategy call is often the part that isn't about the ads. That's where we learn what changes what we build.",
    "isMock": true,
    "mockLayoutVersion": 5,
    "badge": "Client Call",
    "scoreBasis": "editorial",
    "score": 91,
    "scoresBreakdown": {
      "proof": 92,
      "audiencePain": 94,
      "offerFit": 97,
      "recurrence": 86,
      "novelty": 88,
      "demand": 91
    },
    "daysAgo": "Current week",
    "createdAt": "2026-10-20T06:30:00.000Z",
    "editorialWeek": "2026-10-19",
    "timestamp": "2026-10-20",
    "sourceType": "manual",
    "client": "Anonymised wedding professional",
    "sourceDetails": "- Sample strategy call B (anonymised): the opening update, the questions about tours and team capacity, and the follow-up ideas.\n- The build is recorded in the sample follow-up notes and the sample team meeting notes.",
    "primaryQuote": "The most useful part of an ads strategy call is often the part that isn't about the ads. That's where we learn what changes what we build.",
    "suggestedCta": "Elevate",
    "gate": "gate1_angle",
    "editorialContext": {
      "audience": "Established wedding pros who are running ads, or considering an ads partner, and who book tours or consultations: venues, planners, photographers and entertainment. Especially owners whose current reporting starts and ends with cost per lead.",
      "objective": "WARM. Show what working with WIA is actually like, and make ELEVATE's value concrete without a pitch. The desired response: \"I want an ads partner who understands my business, not just my cost per lead.\"",
      "funnelStage": "WARM",
      "pillar": "WARM · UVP and behind-the-scenes process. It's the team's UVP idea, \"Most agencies run your ads in a vacuum and send you a report. We build an entire system for sales around your ads,\" shown through a real account.",
      "beliefShift": "The most useful part of an ads strategy call is often the part that isn't about the ads. That's where we learn what changes what we build.",
      "suggestedInvitation": "CTA: No offer CTA on Instagram (WARM), with a DM \"ADS\" variant for a CONVERT week. A reply in the email.",
      "sources": [],
      "brandReferences": [],
      "externalContext": []
    },
    "angleRationale": {
      "topic": "What our strategy calls actually cover, and why the most useful part often isn't about the ads",
      "source": "editorial",
      "points": [
        {
          "label": "Content pillar / type",
          "text": "WARM · UVP and behind-the-scenes process. It's the team's UVP idea, \"Most agencies run your ads in a vacuum and send you a report. We build an entire system for sales around your ads,\" shown through a real account."
        },
        {
          "label": "Audience",
          "text": "Established wedding pros who are running ads, or considering an ads partner, and who book tours or consultations: venues, planners, photographers and entertainment. Especially owners whose current reporting starts and ends with cost per lead."
        },
        {
          "label": "Why this matters",
          "text": "Ads can bring couples to you. But what happens between an inquiry and a booked tour or consult depends on things only the owner knows, and that's often where the next layer of results is."
        },
        {
          "label": "WIA's expertise or process",
          "text": "Our strategy calls look at the whole path from inquiry to visit, alongside the ad results. We ask about tours, calendars, team capacity and why couples are lost. Then we turn the answers into the follow-up and messaging we build."
        },
        {
          "label": "Evidence in the referenced call",
          "text": "- The situation. At one venue, inquiries and tours were up, and so was ghosting. You opened with \"Good to hear it… so this is the moment to look at the rest.\"\n- What the owner told you. Couples who book more than two weeks out often go elsewhere. Saturdays are weddings, and her team is small. The rain plan was a worry for couples, and she showed her rain-plan photos on a tablet during tours.\n- What you suggested. A personal video by text, real photos in the first messages, and making the marketing say \"you need to see this venue in person before you decide.\"\n- Your view. \"On a call like this, the most useful time goes to the things around the ads.\"\n- What was built by September. A welcome video by text, a selfie in the tour confirmation, real photos in the first texts, and extra follow-up for couples whose tours are weeks away."
        },
        {
          "label": "Editorial guardrail / next step",
          "text": "- No funnel numbers.\n- No claim that ghosting dropped.\n- Don't name the venue, the owner, or the former team member who led the analysis.\n- WIA built her follow-up in LeadLock. She runs her own tours and sales."
        }
      ]
    },
    "brief": {
      "coreInsight": "The most useful part of an ads strategy call is often the part that isn't about the ads. That's where we learn what changes what we build.",
      "audiencePain": "Owners whose inquiries are coming in but who watch couples go quiet before a tour or consultation. They're too busy serving booked clients to chase every one personally, and they get reports that stop at cost per lead.",
      "messageSpine": [
        "Hook: When more inquiries aren't enough.",
        "Problems, desires, symptoms: Inquiries are up, but couples still go quiet, cancel or book elsewhere before the visit. You can't add more hours to your week, and your reports stop at cost per lead.",
        "Main point: Your ads partner should want to understand what happens after the inquiry, because those answers change what gets built.",
        "Transformation: Follow-up that sounds and looks like you and keeps couples connected while you're busy hosting weddings, and an ads partner working with the whole picture.",
        "CTA: No offer CTA on Instagram (WARM), with a DM \"ADS\" variant for a CONVERT week. A reply in the email."
      ],
      "formatSplit": {
        "emailFocus": "Email: the whole story, what we built, and how ELEVATE works.",
        "carouselFocus": "Carousel: the reader's situation, the call, what we built, the belief, and a CTA for both ways of working with WIA.",
        "reelsFocus": "Reel 1 (face to camera, story): the strategy call, and what it led to.\nReel 2 (face to camera, stance): what cost per lead can't tell you.\nReel 3 (b-roll with on-screen text): the questions we ask that aren't about ads."
      },
      "contentPlan": {
        "email": "Email: the whole story, what we built, and how ELEVATE works.",
        "carousel": "Carousel: the reader's situation, the call, what we built, the belief, and a CTA for both ways of working with WIA.",
        "reels": [
          "Reel 1 (face to camera, story): the strategy call, and what it led to.",
          "Reel 2 (face to camera, stance): what cost per lead can't tell you.",
          "Reel 3 (b-roll with on-screen text): the questions we ask that aren't about ads."
        ]
      },
      "claimsRequiringConsent": [
        "- No funnel numbers.\n- No claim that ghosting dropped.\n- Don't name the venue, the owner, or the former team member who led the analysis.\n- WIA built her follow-up in LeadLock. She runs her own tours and sales.",
        "- No funnel numbers.\n- No named people.\n- Nothing that suggests WIA runs her tours or sales."
      ],
      "openQuestionsForWhitney": [
        "SEND TIME: your usual Tuesday morning send (confirm)",
        "RECIPIENTS: full WIA list (confirm segment)"
      ]
    },
    "research": {
      "origin": "editorial",
      "searchQuery": "What our strategy calls actually cover, and why the most useful part often isn't about the ads",
      "googleTrendsScore": null,
      "trendDirection": null,
      "peopleAlsoAsk": [],
      "autocomplete": [],
      "forumDiscussions": [],
      "note": "Editorial content supplied by the user."
    }
  },
  {
    "id": "mock-current-week-2026-10-19-3",
    "title": "How we help wedding pros understand their own ad accounts, now that AI can change them in minutes",
    "suppliedCopy": {
      "angle": "# How we help wedding pros understand their own ad accounts, now that AI can change them in minutes\n\n## Content angle\n\n### Content pillar / type\nCONVERT · Solution selling for the Ads Accelerators. It's the team's idea: \"The platform buttons are the easy part… knowing which move to make is the skill… We teach both.\"\n\n### Audience\nCapable, hands-on wedding pros who run their own ads or want to, including the growing number using ChatGPT or AI tools to help. These are resourceful owners who want to stay in control, not beginners in a panic.\n\n### Why this matters\nAI makes it easier than ever to change a campaign, and just as easy to lose track of what changed. When results drop, knowing what happened and what to do next is the skill that keeps your advertising working.\n\n### WIA's expertise or process\nIn the Ads Accelerators, we launch your campaigns. Then you run them, with weekly office hours where our Google and Meta experts look at your actual account with you, so you learn the why behind every decision.\n\n### Evidence in the referenced calls\n- **Her setup.** A prospect had built an AI assistant that writes her blog posts, updates her website, and helped her set up her Google Ads.\n- **What happened.** On a small budget, she got four good leads in her first week. After she made changes across the campaigns she'd built, the one that had been working went quiet: \"I'm not sure what I did. I'm not sure what we changed.\"\n- **Your response.** \"It's a familiar feeling… it was working, then it stops, and the reason isn't clear.\" The Accelerators' goal \"is to help you decide like a strategist.\"\n- **Office hours.** A member asked our strategist whether he'd set up a test campaign wrong. He hadn't, and he left understanding why.\n\n### Editorial guardrail / next step\n- The prospect didn't join the Accelerators. Never imply she did.\n- Her AI helped set up her ads. It didn't \"run\" them.\n- No promise of results or speed.\n- Members do the ongoing work with guidance. It's never a course and never full management.\n- Confirm your stance on AI before publishing.",
      "brief": ""
    },
    "subtitle": "AI makes it easy to change your ads, and just as easy to lose track of what changed. The Ads Accelerators help you understand your own account, so when something that was working stops, you know what to look at.",
    "isMock": true,
    "mockLayoutVersion": 5,
    "badge": "Client Call",
    "scoreBasis": "editorial",
    "score": 92,
    "scoresBreakdown": {
      "proof": 86,
      "audiencePain": 93,
      "offerFit": 98,
      "recurrence": 85,
      "novelty": 95,
      "demand": 92
    },
    "daysAgo": "Current week",
    "createdAt": "2026-10-20T06:30:00.000Z",
    "editorialWeek": "2026-10-19",
    "timestamp": "2026-10-20",
    "sourceType": "manual",
    "client": "Anonymised wedding professional",
    "sourceDetails": "- Sample discovery call (anonymised): the prospect's setup, what happened after her changes, and the response.\n- Sample Google Ads office hours session (anonymised).",
    "primaryQuote": "AI makes it easy to change your ads, and just as easy to lose track of what changed. The Ads Accelerators help you understand your own account, so when something that was working stops, you know what to look at.",
    "suggestedCta": "Accelerators",
    "gate": "gate1_angle",
    "editorialContext": {
      "audience": "Capable, hands-on wedding pros who run their own ads or want to, including the growing number using ChatGPT or AI tools to help. These are resourceful owners who want to stay in control, not beginners in a panic.",
      "objective": "CONVERT. Sell the Ads Accelerators through a timely, relatable story. The desired response: \"I want to run my own ads, and I want experts beside me while I learn to read them.\"",
      "funnelStage": "CONVERT",
      "pillar": "CONVERT · Solution selling for the Ads Accelerators. It's the team's idea: \"The platform buttons are the easy part… knowing which move to make is the skill… We teach both.\"",
      "beliefShift": "AI makes it easy to change your ads, and just as easy to lose track of what changed. The Ads Accelerators help you understand your own account, so when something that was working stops, you know what to look at.",
      "suggestedInvitation": "CTA: DM \"ADS\" (the week's offer CTA). The email links to the Ads Accelerators, with a reply option.",
      "sources": [],
      "brandReferences": [],
      "externalContext": []
    },
    "angleRationale": {
      "topic": "How we help wedding pros understand their own ad accounts, now that AI can change them in minutes",
      "source": "editorial",
      "points": [
        {
          "label": "Content pillar / type",
          "text": "CONVERT · Solution selling for the Ads Accelerators. It's the team's idea: \"The platform buttons are the easy part… knowing which move to make is the skill… We teach both.\""
        },
        {
          "label": "Audience",
          "text": "Capable, hands-on wedding pros who run their own ads or want to, including the growing number using ChatGPT or AI tools to help. These are resourceful owners who want to stay in control, not beginners in a panic."
        },
        {
          "label": "Why this matters",
          "text": "AI makes it easier than ever to change a campaign, and just as easy to lose track of what changed. When results drop, knowing what happened and what to do next is the skill that keeps your advertising working."
        },
        {
          "label": "WIA's expertise or process",
          "text": "In the Ads Accelerators, we launch your campaigns. Then you run them, with weekly office hours where our Google and Meta experts look at your actual account with you, so you learn the why behind every decision."
        },
        {
          "label": "Evidence in the referenced calls",
          "text": "- Her setup. A prospect had built an AI assistant that writes her blog posts, updates her website, and helped her set up her Google Ads.\n- What happened. On a small budget, she got four good leads in her first week. After she made changes across the campaigns she'd built, the one that had been working went quiet: \"I'm not sure what I did. I'm not sure what we changed.\"\n- Your response. \"It's a familiar feeling… it was working, then it stops, and the reason isn't clear.\" The Accelerators' goal \"is to help you decide like a strategist.\"\n- Office hours. A member asked our strategist whether he'd set up a test campaign wrong. He hadn't, and he left understanding why."
        },
        {
          "label": "Editorial guardrail / next step",
          "text": "- The prospect didn't join the Accelerators. Never imply she did.\n- Her AI helped set up her ads. It didn't \"run\" them.\n- No promise of results or speed.\n- Members do the ongoing work with guidance. It's never a course and never full management.\n- Confirm your stance on AI before publishing."
        }
      ]
    },
    "brief": {
      "coreInsight": "AI makes it easy to change your ads, and just as easy to lose track of what changed. The Ads Accelerators help you understand your own account, so when something that was working stops, you know what to look at.",
      "audiencePain": "Owners who are already experimenting: running their own campaigns, using AI to help, seeing early wins. They've had, or will have, the moment when something stops working and they can't tell why.",
      "messageSpine": [
        "Hook: She used AI to set up her Google Ads. Four good leads in week one. Then it went quiet.",
        "Problems, desires, symptoms: You're resourceful and you want to run your own ads. Something works, then it stops, and you can't tell what changed. Every tool makes it easier to change more things at once.",
        "Main point: Understanding your own account is the skill. That's what the Accelerators build: we launch your campaigns, and you run them with experts looking at your real account with you.",
        "Transformation: A quiet campaign becomes something you can figure out, not something that just happens to you, and you can use any tool, AI included, with confidence.",
        "CTA: DM \"ADS\" (the week's offer CTA). The email links to the Ads Accelerators, with a reply option."
      ],
      "formatSplit": {
        "emailFocus": "Email: the full story, the principle, who the Accelerators are for, and a link.",
        "carouselFocus": "Carousel: the story, the reader's situation, how the Accelerators work, and a CTA.",
        "reelsFocus": "Reel 1 (face to camera, story): the AI story, with DM \"ADS\".\nReel 2 (face to camera, story): office hours, \"Did I set this up wrong?\"\nReel 3 (b-roll with on-screen text): the story told in three screens."
      },
      "contentPlan": {
        "email": "Email: the full story, the principle, who the Accelerators are for, and a link.",
        "carousel": "Carousel: the story, the reader's situation, how the Accelerators work, and a CTA.",
        "reels": [
          "Reel 1 (face to camera, story): the AI story, with DM \"ADS\".",
          "Reel 2 (face to camera, story): office hours, \"Did I set this up wrong?\"",
          "Reel 3 (b-roll with on-screen text): the story told in three screens."
        ]
      },
      "claimsRequiringConsent": [
        "- The prospect didn't join the Accelerators. Never imply she did.\n- Her AI helped set up her ads. It didn't \"run\" them.\n- No promise of results or speed.\n- Members do the ongoing work with guidance. It's never a course and never full management.\n- Confirm your stance on AI before publishing.",
        "- One offer CTA a week on Instagram (Reel 1).\n- No results or timelines promised.\n- Keep the office-hours member and the prospect separate and unnamed."
      ],
      "openQuestionsForWhitney": [
        "SEND TIME: your usual Tuesday morning send (confirm)",
        "RECIPIENTS: full WIA list (confirm segment)"
      ]
    },
    "research": {
      "origin": "editorial",
      "searchQuery": "How we help wedding pros understand their own ad accounts, now that AI can change them in minutes",
      "googleTrendsScore": null,
      "trendDirection": null,
      "peopleAlsoAsk": [],
      "autocomplete": [],
      "forumDiscussions": [],
      "note": "Editorial content supplied by the user."
    }
  }
];

export const FATHOM_STARTER_PLANS = Object.fromEntries(SOURCE_ANGLE_PROPOSALS.map(idea => [idea.id, idea.brief.contentPlan]));
export const FATHOM_WEEKLY_ANGLES = SOURCE_ANGLE_PROPOSALS.map(idea => hydrateFathomMockPack(prepareFathomContentBrief(idea, idea.brief.contentPlan)));
