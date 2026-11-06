# Week 4 rejected extraction: source review

The model returned 17 proposals, but the whole extraction failed exact-quote validation. No proposals were admitted and no Week 4 angle model was called. Individual checks below are diagnostics only, not partial acceptance or a recovered evidence pool.

The response passed the strategic response contract and compact-reference resolution. Fifteen proposals pass the normal parser individually; two fail literal quote matching. This does not establish semantic correctness or exhaustive source coverage.

## Two literal-quote failures

### m4_google_conversion_correction

During an account walkthrough, Whitney corrected a potentially misleading description of a tracked conversion: a book-a-tour page view was not a completed tour booking.

**Model quote:** "Um, or I guess this wouldn't be if they've actually booked the tour, this is them looking at the book a tour page."

**Failure:** ValueError: Moment quote must match an existing anchor span

**Original m4.t0256:** Whitney Hodges: Um, if they have booked a tour or not. Like, um, or I guess this wouldn't be if they've actually booked the tour, this is them looking at the book a tour page.

### m6_adjacent_search_intent

The exchange distinguished truthful promotion of an existing service in the context of adjacent wedding interests from implying that the business sells services it does not offer.

**Model quote:** "Um, so we wouldn't want you ranking to say, like, marquee lights available, and then people click on an ad and get there, and then they're not there"

**Failure:** ValueError: Moment quote must match an existing anchor span

**Original m6.t0429:** Emily Foster: Um, but, like, we wouldn't want you ranking to say, like, marquee lights available, and then people click on an ad and get there, and then they're not there, because I feel like that could just get into, like, mostly legal issues in the future, um, or if anything, like, frustrated clients.

## All rejected proposals with original source context

Model interpretations below are retained as rejected proposals. Speaker labels are supplied transcript labels. Elapsed timestamps and original turn text are projected directly from the frozen source map.

### m1_email_safeguards

A suspected email-delivery failure prompted Whitney to acknowledge a monitoring gap and propose recurring safeguards, while keeping the cause unresolved and assigning immediate follow-up.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["wia_expertise", "service_value", "broader_principle"], "destination": "internal_intelligence", "wia_contribution": "Whitney identified the need for recurring DNS and lead-performance checks, assigned follow-up, and separated known symptoms from her guess about the cause.", "attention_reason": "This is a consequential service-reliability concern, but the client-specific incident and unresolved cause make it internal intelligence rather than a public example.", "research_questions": ["Were the email records restored, what caused them to become unverified, and were the proposed recurring checks adopted?"]}

**Qualifications:** ["Whitney did not know how or when the records became unverified; the staff-transition explanation was a guess.", "The proposed recurring checks and the attempted fixes are not shown as completed, and no client outcome is reported.", "The client incident and internal response are sensitive operational information."]

**[00:05:14] m1.t0079** Whitney Hodges: Um… I don't… I mean, I guess, like, the big thing is… honestly, I'll be, like, fully transparent just with you. I don't know that I'll be like this on the team call necessarily, but the whole, like, Ridgefield situation…

**[00:05:27] m1.t0080** Gisselle Jiménez: Mm-hmm.

**[00:05:30] m1.t0081** Whitney Hodges: I'm pretty, like, mortified by it, to be honest. Um, and… I mean, it…

**[00:05:35] m1.t0082** Gisselle Jiménez: Oh.

**[00:05:38] m1.t0083** Whitney Hodges: It's not like anybody necessarily did anything.

**[00:05:43] m1.t0084** Whitney Hodges: wrong. Like, in an ideal world, though, like.

**[00:05:47] m1.t0085** Whitney Hodges: an ads manager, like, once the ads are launched, they're actually, like, looking at what's happening with the leads, right? And, like, ideally, it would have been, like.

**[00:05:54] m1.t0086** Gisselle Jiménez: Okay.

**[00:05:56] m1.t0087** Whitney Hodges: caught, right, that nobody is basically opening the emails. Um, but at the same time, too, it's like we're in the process of, like, kind of.

**[00:06:06] m1.t0088** Whitney Hodges: transitioning with Fallon, like, there's not necessarily anybody on Ridgefield who has had, like, true ownership sort of thing. Um, and…

**[00:06:13] m1.t0089** Gisselle Jiménez: Mm-hmm.

**[00:06:15] m1.t0090** Whitney Hodges: those email records, they must have been verified at some point. I don't think that we got any sort of, like, email alert or anything like that about them, like, becoming.

**[00:06:26] m1.t0091** Whitney Hodges: unverified, which is interesting, because it's like, I keep seeing emails that will come through for, like, Straylitzia, that say, like, hey, if you don't verify this soon, like, it's gonna get deleted, sort of thing. But it's not like that was coming through for Ridgefield, so…

**[00:06:38] m1.t0092** Gisselle Jiménez: Mm-hmm.

**[00:06:43] m1.t0093** Whitney Hodges: I mean, really what it tells me is that we just need to be putting more safeguards in place. So, um, what I'm potentially thinking on, like, the email DNS side of things, right, is that maybe there's, like, a monthly recurring task for.

**[00:06:50] m1.t0094** Gisselle Jiménez: None.

**[00:07:00] m1.t0095** Whitney Hodges: Danielle, to where she is going into every subaccount, and just, like, making sure that.

**[00:07:07] m1.t0096** Whitney Hodges: domain records, like, across the board, like, email and subdomains are still verified, sort of thing. Hopefully she'll be able to attend our, um…

**[00:07:17] m1.t0097** Whitney Hodges: Team call tomorrow, and we can kind of bring it up then.

**[00:07:21] m1.t0098** Whitney Hodges: But I feel like this does kind of mirror the areas of opportunity that Fallon brought up and that doc that she sent over to me, which I think she shared with you as well. Right? Of, like, you know, there being something on there now where I think it's, like, once or twice a week.

**[00:07:21] m1.t0099** Gisselle Jiménez: Thanks.

**[00:07:28] m1.t0100** Gisselle Jiménez: Mm-hmm.

**[00:07:32] m1.t0101** Gisselle Jiménez: Mm-hmm.

**[00:07:38] m1.t0102** Whitney Hodges: the account manager is actually, like, looking at lead lock performance and, like, seeing how things are happening, right? Because if that had been happening, then we would have caught this earlier. Um, and at the end of the day, like, we still caught it before.

**[00:07:43] m1.t0103** Gisselle Jiménez: Mm-hmm.

**[00:07:54] m1.t0104** Whitney Hodges: the client caught it sort of thing.

**[00:07:57] m1.t0105** Gisselle Jiménez: Mm-hmm.

**[00:07:58] m1.t0106** Whitney Hodges: I'm just, like, again, kind of, like, mortified because if Scott, like, can, like, ask more questions, right, it's basically, like, well, this whole month, like, people really haven't been, like, all of your emails have been going to spam, basically. So.

**[00:08:14] m1.t0107** Whitney Hodges: I am…

**[00:08:17] m1.t0108** Whitney Hodges: I'm anxious for Amy to get back to me because I want to get those.

**[00:08:23] m1.t0109** Whitney Hodges: records created again? Like, I don't know, I don't even know what happened. Like, I don't know where they would have went. I assume that something happened in the transition from them working with Elizabeth to now working with.

**[00:08:27] m1.t0110** Gisselle Jiménez: Mm-hmm.

**[00:08:34] m1.t0111** Gisselle Jiménez: Mmm.

**[00:08:35] m1.t0112** Whitney Hodges: Amy would be my guess. I emailed Scott this morning because he had emailed on Friday night saying, like.

**[00:08:36] m1.t0113** Gisselle Jiménez: Yeah.

**[00:08:37] m1.t0114** Gisselle Jiménez: Yeah, that makes sense.

**[00:08:45] m1.t0115** Whitney Hodges: I don't understand how this could have happened, sort of thing. Um, so hopefully I kind of explained it okay. Um, but what I told him was that, like, if I don't hear back from Amy this morning, I'll follow up with her this afternoon. So, I think if you could just go ahead and, like, draft.

**[00:08:58] m1.t0116** Gisselle Jiménez: Mm-hmm.

**[00:09:02] m1.t0117** Whitney Hodges: an email to Amy that's, like, piggybacking off of the email that I sent to her on Friday, um, that would be great. Danielle is still out of office today, right?

**[00:09:12] m1.t0118** Gisselle Jiménez: Yep.

**[00:09:15] m1.t0119** Whitney Hodges: I think.

**[00:09:16] m1.t0120** Gisselle Jiménez: I think so… yes, yes, but she should be back tomorrow.

**[00:09:20] m1.t0121** Whitney Hodges: Okay.

**[00:09:21] m1.t0122** Whitney Hodges: Yeah. So, like, this just needs to be, like, high priority for her when she…

**[00:09:28] m1.t0123** Whitney Hodges: gets back, like, getting that resolved. Um…

**[00:09:31] m1.t0124** Gisselle Jiménez: Yeah.

**[00:09:32] m1.t0125** Whitney Hodges: In the meantime, I do want us to see if we can, like, get that Canva doc that they sent over to us, if we can get the images in it compressed. I don't know, honestly, if there's a way to do that within…

**[00:09:43] m1.t0126** Whitney Hodges: Canva sort of thing, if you could maybe kind of, like, do some research and look into that, and just kind of, like, take the lead, um, on that, because it sounds like Tina's kind of out of pocket today, um, and I do want to make sure that we're getting to that piece of it.

**[00:09:44] m1.t0127** Gisselle Jiménez: Mm-hmm.

**[00:09:47] m1.t0128** Gisselle Jiménez: Mm-hmm.

**[00:09:58] m1.t0129** Whitney Hodges: As quickly as possible. Because honestly, like, what it sounds like is happening is that the emails were ending up in spam.

**[00:10:05] m1.t0130** Whitney Hodges: People were seeing on the thank you page, hey, if it's in spam, check your spam. So the people who are really interested are going to spam and checking it, but there's still no way for them to open.

**[00:10:14] m1.t0131** Whitney Hodges: those links because the email wasn't verified, you know? So, um, yeah, I'm on… I'm just kind of, like, anxious and on edge about it, so I'm hoping we can get it all, um, fixed soon.

**[00:10:19] m1.t0132** Gisselle Jiménez: Yeah.

**[00:10:31] m1.t0133** Gisselle Jiménez: Mm-hmm. Yeah, no, definitely. Um, yeah, I'll drop that follow-up to Amy and, uh, look into compressing that Canva file, and hopefully we can…

**[00:10:38] m1.t0134** Whitney Hodges: Okay.

**[00:10:40] m1.t0135** Gisselle Jiménez: Try to get it resolved shortly.

### m1_vault_prompt_accountability

The proposed member-engagement routine exposed a choice between ensuring the prompt gets posted and maintaining clear staff ownership through a recurring task and existing SOP.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["wia_expertise", "service_value", "broader_principle"], "destination": "internal_intelligence", "wia_contribution": "Whitney proposed the member prompt, reasoned through ownership and timing, and directed that the instruction be added to an existing Vault SOP rather than standing alone.", "attention_reason": "This is a concrete service-operations decision, but it remains an internal plan with no evidence of execution or member impact.", "research_questions": ["Was the recurring task added to the SOP and ClickUp, and did the team settle on Monday or Tuesday for the prompt?"]}

**Qualifications:** ["The task and SOP were proposed for later team discussion; implementation and staff awareness are not established.", "No evidence is given about member participation or the effect of the prompt."]

**[00:31:55] m1.t0412** Whitney Hodges: Okay, sounds good. Oh, the other thing, and I'll bring this up on the team call tomorrow, but this will be something that we, like, need to create an SOP for, that we need to start creating recurring ClickUp tasks.

**[00:32:11] m1.t0413** Whitney Hodges: for is basically that I want, uh, Jacqueline and Carmen at the start of each week to post in the Vault in the respective, like, Google Search Accelerator channel, Meta Ads Accelerator channel.

**[00:32:14] m1.t0414** Gisselle Jiménez: Okay.

**[00:32:26] m1.t0415** Whitney Hodges: Like, tagging anybody who is still currently in the program, and saying, you know, like.

**[00:32:31] m1.t0416** Gisselle Jiménez: Mm-hmm.

**[00:32:33] m1.t0417** Whitney Hodges: Happy Monday. Hope your week is off to a great start. Let us know what you're working on this week related to your ads. Hope to see you in office hours.

**[00:32:33] m1.t0418** Gisselle Jiménez: Hello?

**[00:32:48] m1.t0419** Whitney Hodges: whether you can make it or not, if you have questions that you want me to address in office hours, like, you know, leave it in the comments, something like that. Like, I don't want it to…

**[00:32:57] m1.t0420** Whitney Hodges: I don't want them to say like the exact same thing necessarily like verbatim every week. But.

**[00:33:02] m1.t0421** Gisselle Jiménez: No.

**[00:33:06] m1.t0422** Whitney Hodges: Something along those lines.

**[00:33:10] m1.t0423** Whitney Hodges: And…

**[00:33:11] m1.t0424** Whitney Hodges: I don't know, part of me, like…

**[00:33:15] m1.t0425** Whitney Hodges: Like, you could log in as any of us, right? And just, like…

**[00:33:20] m1.t0426** Whitney Hodges: do it on our behalf, like, do it on their behalf, I think. But a part of me really wants them to be…

**[00:33:26] m1.t0427** Whitney Hodges: accountable, too. You know what I mean? So, um…

**[00:33:28] m1.t0428** Gisselle Jiménez: Mm-hmm.

**[00:33:33] m1.t0429** Whitney Hodges: yeah, I guess I'm just kind of, like, thinking through that, like, do I want to just… us to just, like, do it for them to make sure that it gets done, or… but I think…

**[00:33:42] m1.t0430** Whitney Hodges: that it needs to be just, like, a recurring ClickUp task for them, basically every Monday, or if they think Tuesday would be better, because, you know, wedding pros are normally out of the office on Monday, like, that's fine too, but it'll be something we talk about on the team call tomorrow. That doc that Fallon put together.

**[00:33:46] m1.t0431** Gisselle Jiménez: Mm-hmm.

**[00:33:53] m1.t0432** Gisselle Jiménez: Hmm.

**[00:33:58] m1.t0433** Whitney Hodges: We'll be reviewing on the team call tomorrow as well.

**[00:33:59] m1.t0434** Gisselle Jiménez: Yeah.

**[00:34:04] m1.t0435** Whitney Hodges: So.

**[00:34:04] m1.t0436** Gisselle Jiménez: Yeah, I think you mentioned that in the last team call, but…

**[00:34:10] m1.t0437** Whitney Hodges: I think I mentioned it on our last one-on-one call, but then I forgot to mention it on the actual team call, so, like, I don't think Jacqueline and Carmen are aware yet that I want them to start doing that.

**[00:34:10] m1.t0438** Gisselle Jiménez: With…

**[00:34:14] m1.t0439** Gisselle Jiménez: Oh.

**[00:34:18] m1.t0440** Gisselle Jiménez: Okay.

**[00:34:23] m1.t0441** Gisselle Jiménez: Okay, okay, go ahead. Okay, perfect. Then, yeah, I'll make a list of those items that we need to touch base tomorrow.

**[00:34:24] m1.t0442** Whitney Hodges: Okay.

**[00:34:30] m1.t0443** Whitney Hodges: Okay, yeah, but even if you already have, like, an SOP that's kind of… you've gotten started, that we can…

**[00:34:37] m1.t0444** Whitney Hodges: just even have to share on the team call tomorrow, or to share after the team call tomorrow, like, I want to make sure that I'm not just, like, saying it, and then there's not ever any actual, like, follow-up or, like, accountability to actually, like, get it done. Like, once I've told them that, like.

**[00:34:46] m1.t0445** Gisselle Jiménez: Mm-hmm.

**[00:34:52] m1.t0446** Whitney Hodges: It needs to be a recurring weekly task in ClickUp.

**[00:34:56] m1.t0447** Gisselle Jiménez: Mm-hmm. Yeah. Um, what type of SOP do you want for that?

**[00:35:02] m1.t0448** Whitney Hodges: I don't… I mean, do we have an SOP on the vault, or, like, what channels are supposed to be used for what sort of thing?

**[00:35:10] m1.t0449** Gisselle Jiménez: Oh, yeah, yeah, yeah, mm-hmm. So just add it there.

**[00:35:11] m1.t0450** Whitney Hodges: I would think it should kind of be added to that, like, I don't think it needs to be its own separate thing.

**[00:35:17] m1.t0451** Gisselle Jiménez: Okay, yeah, that sounds good, yeah.

**[00:35:19] m1.t0452** Whitney Hodges: Mm-hmm.

**[00:35:23] m1.t0453** Gisselle Jiménez: Perfect, yeah, I'll add that.

### m2_investment_hesitation

Emily described investment hesitation after extended sales conversations as a pattern she encounters in her own inquiries, while distinguishing self-directed work from hiring help.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["audience_insight"], "destination": "internal_intelligence", "wia_contribution": null, "attention_reason": "The prospect's hesitation may be commercially relevant, but it is not a WIA client outcome or a verified pattern across WIA leads.", "research_questions": []}

**Qualifications:** ["Emily is describing her own inquiries, not a measured WIA trend.", "Sean was explicitly identified as not being a WIA client, and no eventual purchase outcome is supplied.", "The conversation concerns a third party and another provider's potential prospect."]

**[00:01:42] m2.t0003** Whitney Hodges: Yeah, okay.

**[00:01:43] m2.t0004** Whitney Hodges: Yeah. Um, that Sean guy, he's not actually a client of ours, but he, um… I had, like, so many sales calls with him, I want to say at, like, the end of the year, last year, and he made it really sound like he was, like, gonna sign on with us, and then he, like.

**[00:01:45] m2.t0005** Emily Foster: Yeah.

**[00:02:00] m2.t0006** Whitney Hodges: I don't know. I think he just got, like, scared or something, and then he was like, oh, I'm gonna do it after, like, the first of the year, and I just, like, haven't… haven't heard. He obviously still needs help, but honestly, it would be better if he worked with you first, because it's… his website is not in a good spot. So.

**[00:02:06] m2.t0007** Emily Foster: Yeah, it…

**[00:02:14] m2.t0008** Emily Foster: Yeah. What's his business name? I'll follow him on Instagram.

**[00:02:18] m2.t0009** Whitney Hodges: Um, full spectrum ice.

**[00:02:21] m2.t0010** Emily Foster: Okay, perfect. Yeah, um, I feel like I get so many of those kinds of leads that do the same thing. Like, they invest so much time in the whole sales process, and then they decide not to work together, because I think they get scared of the investment. Uh, and I could tell, like, he had some great questions, but I feel like sometimes it's hard, because the questions eventually kind of get to, like.

**[00:02:28] m2.t0011** Whitney Hodges: Mmhm.

**[00:02:29] m2.t0012** Whitney Hodges: Mm-hmm.

**[00:02:35] m2.t0013** Whitney Hodges: Mm-hmm.

**[00:02:41] m2.t0014** Emily Foster: we really just have to do it for you, or you have to, like, get in the weeds of, you know, doing it. Like, that's kind of, like, what I was mentioning about keyword research, and then I thought about mentioning, like, we do blogging services, so reach out if you want that, but…

**[00:02:49] m2.t0015** Whitney Hodges: Mm-hmm.

**[00:02:55] m2.t0016** Whitney Hodges: Mmhm.

**[00:02:56] m2.t0017** Emily Foster: Yeah, I'm glad I'm not the only one that gets those kinds of inquiries.

### m2_ads_and_downstream_funnel

Whitney reported challenging an ad-only success measure when downstream sales from challenge signups were unproven, and recommended resolving the funnel question before treating low lead costs as sufficient value.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["wia_expertise", "broader_principle", "audience_insight"], "destination": "internal_intelligence", "wia_contribution": "Whitney reports challenging the focus on discrepant platform counts, asking whether challenge participants became buyers, recommending a funnel with demonstrated conversion, and distinguishing the client's funnel from WIA's wedding focus.", "attention_reason": "The reasoning is strategically meaningful, but the account is a third-party, non-wedding client situation and the recommended changes are not confirmed.", "research_questions": ["Was an evergreen webinar or other funnel later built, and is there evidence about whether challenge participants became paying clients?"]}

**Qualifications:** ["The account and client reaction are described by Whitney, not independently corroborated.", "The client reportedly lacked data about whether challenge participants became paid clients; that is not proof that none did.", "The webinar recommendation was not shown as implemented, and no sale or ROI result is established.", "The funnel belonged to a coach/course creator rather than WIA's core wedding-business audience."]

**[00:06:47] m2.t0072** Whitney Hodges: So we had been running ads to her challenge, like the get a win a client in five days challenge or something like that. And like leads were coming in, like lead cost was good.

**[00:06:52] m2.t0073** Emily Foster: Mm-hmm.

**[00:06:55] m2.t0074** Emily Foster: Wow.

**[00:07:03] m2.t0075** Emily Foster: Yeah.

**[00:07:03] m2.t0076** Whitney Hodges: Honestly. Um, but what… I feel like we couldn't get through to her was, like…

**[00:07:12] m2.t0077** Whitney Hodges: like, why are you running these ads? Because nothing is happening beyond the people sign… like, beyond the people doing the challenge, right? Like.

**[00:07:23] m2.t0078** Whitney Hodges: to run ads effectively, and to really, like, be seeing an ROI, like.

**[00:07:30] m2.t0079** Whitney Hodges: they need to be able to move through your funnel. Like, you need to be able to see that, like, okay, the people who are signing up for this challenge eventually down the line are becoming irresistible selling clients.

**[00:07:40] m2.t0080** Emily Foster: Yeah, I…

**[00:07:41] m2.t0081** Whitney Hodges: But you were, but what was interesting was that, like.

**[00:07:44] m2.t0082** Whitney Hodges: she wasn't the one that was like noticing that, or like looking at that like we were. We were the ones that were having to say like, Okay, yes, like from an ad like the ads look good. The ads are performing well, but none of this is happening beyond that, and like.

**[00:08:01] m2.t0083** Emily Foster: All right.

**[00:08:01] m2.t0084** Whitney Hodges: It was just interesting to me that she wasn't the one to ever be looking into that, but that also, like, across the board.

**[00:08:10] m2.t0085** Whitney Hodges: Like she couldn't say she didn't have any data to say that like, yes, when people do this challenge, whether it's organic or through ads, I know that they're going to become an irresistible selling client sort of thing. Right. And so.

**[00:08:23] m2.t0086** Emily Foster: Yeah.

**[00:08:26] m2.t0087** Whitney Hodges: She was like…

**[00:08:28] m2.t0088** Whitney Hodges: there was a report, I think, that Jacqueline had sent her, where some of the numbers, like, didn't, like, quite add up, and she's like, I don't understand why when I look at, you know, my landing page views in.

**[00:08:42] m2.t0089** Whitney Hodges: uh… I can't remember what she does… lead pages, like, it looks so different than my landing page views in Meta, and like, you know, why is there this discrepancy between the number of leads that I see in ConvertKit versus the number of leads that.

**[00:08:57] m2.t0090** Whitney Hodges: I see from my meta ads, and, like, she was, like.

**[00:09:02] m2.t0091** Whitney Hodges: was really, like, wanting an answer, and wanting to know, like, why it wasn't working, and kept saying stuff of, like, well, how do I make the right decisions, or make data-driven decisions when the data isn't even, like, right, sort of thing. And that's when I kept just having to be, like, whoa, like, let's back up.

**[00:09:14] m2.t0092** Emily Foster: Right.

**[00:09:18] m2.t0093** Whitney Hodges: And almost, like, in a nice way, say, who cares if the landing page numbers or the lead numbers, like, don't fully add up? Like, there are always gonna be some differences.

**[00:09:19] m2.t0094** Emily Foster: Got it.

**[00:09:27] m2.t0095** Emily Foster: Um…

**[00:09:30] m2.t0096** Whitney Hodges: If they're not turning into sales for you regardless, like why are you spending the money to run the ads? Why are you paying us to run the ads? Like there's not, that's not a benefit to you. You should put your effort into.

**[00:09:37] m2.t0097** Emily Foster: Ah, yes.

**[00:09:43] m2.t0098** Emily Foster: Yeah, I…

**[00:09:46] m2.t0099** Whitney Hodges: a funnel that you know is going to convert. Like, we kept telling her, like, create an evergreen webinar that sells irresistible selling, like…

**[00:09:49] m2.t0100** Emily Foster: Wow.

**[00:09:54] m2.t0101** Emily Foster: Why?

**[00:09:55] m2.t0102** Whitney Hodges: Run ads to that, and…

**[00:09:57] m2.t0103** Emily Foster: That's a great idea. Yeah.

**[00:09:59] m2.t0104** Whitney Hodges: But thus far, you know, she hasn't done that. So I recommended this this this girl who I keep seeing her ads as well. Her name's Anna Concher, and she teaches, like, basically how to create an evergreen webinar that converts and, like, how to run ads to it.

**[00:10:15] m2.t0105** Emily Foster: Yeah, I…

**[00:10:18] m2.t0106** Whitney Hodges: Um, and just tried to explain to her, like.

**[00:10:21] m2.t0107** Whitney Hodges: like, I haven't worked with her personally, but from what she is teaching, like, this is what you need to know if you want to be successful running ads. Like, you have to keep in mind that, like.

**[00:10:31] m2.t0108** Whitney Hodges: And I didn't say it this way, but, like, you're not our ideal client. We work with wedding pros and venues. Like, yes, we do have some experience in the coaches and course creators world from, like, our past, but that's not what we're doing.

**[00:10:34] m2.t0109** Emily Foster: Yeah.

**[00:10:42] m2.t0110** Emily Foster: Bye.

**[00:10:46] m2.t0111** Whitney Hodges: in this business, and those are very different funnels, like, what you're trying to do versus what we're trying to do. So…

**[00:10:47] m2.t0112** Emily Foster: Yeah.

**[00:10:50] m2.t0113** Emily Foster: Yeah, right.

**[00:10:54] m2.t0114** Emily Foster: Okay.

**[00:10:55] m2.t0115** Whitney Hodges: Finally, like, at the end of the call, she really, like, started to get it, and was kind of, like, at least from what it seemed, like, appreciative.

### m3_support_options_after_management

When Kelly wanted to keep running ads but not continue proactive management, she preferred the offered pay-as-needed consultation option to a recurring support program.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["audience_insight", "service_value"], "destination": "internal_intelligence", "wia_contribution": "Whitney asked what support Kelly needed and described recurring and one-off options, with the prices stated at the time of the call.", "attention_reason": "This is useful offer-fit and price-objection intelligence, but the prices are historical and the client's financial choice is not cleared for public use.", "research_questions": ["Did Kelly subsequently book either consultation, and what support did she use after this call?"]}

**Qualifications:** ["The fees and program details are historical as described in this call and do not establish current pricing or availability.", "Kelly's stated preference is not evidence that she booked a consultation or achieved an outcome.", "The exchange includes an individual client's financial decision."]

**[00:00:47] m3.t0008** Whitney Hodges: Yeah, okay, so, um, I'm glad we have some time to kind of, um, catch up and, uh, check in, because, you know, I know you had mentioned wanting to keep.

**[00:00:58] m3.t0009** Whitney Hodges: ads running, right? But kind of, like, foregoing our kind of proactive ads management services, which I totally get, especially, you know, when revenue dips and things like that. It's like, you don't want to stop running the ads, but then when you add up all of, like, the.

**[00:01:14] m3.t0010** Whitney Hodges: Cost to, you know, actually have the agency fees and things like that, that it doesn't always, um…

**[00:01:21] m3.t0011** Whitney Hodges: the numbers just don't always add up, right? Um, but you did say that you wanted to continue with LeadLock, right?

**[00:01:23] m3.t0012** Kelly Scaramella: Right.

**[00:01:28] m3.t0013** Kelly Scaramella: Yeah.

**[00:01:29] m3.t0014** Whitney Hodges: Okay, perfect. So, um, so that's great. That's kind of all, you know, um, in, in place for you moving forward. As far as you kind of, like, keeping the ads running and essentially kind of handling them themselves, yourself, you know, I just wanted to kind of get with you and see what kind of.

**[00:01:48] m3.t0015** Whitney Hodges: support you feel like you might need, if any. Um, because we do have a program called our Google Search Accelerator, and we have our Meta Ads Accelerator as well, and so we've had some clients who have been kind of in a similar position as you, right, where they're like.

**[00:02:05] m3.t0016** Whitney Hodges: The numbers aren't just quite adding up. We want to keep running ads. We want to learn actually how to do this ourselves, right, and have kind of like transitioned into our community called The Vault, which has a lot of curriculum to help you really understand.

**[00:02:22] m3.t0017** Whitney Hodges: the ads performance, the foundations behind the ads, and then there are also weekly office hours calls for both Google Ads and Meta Ads. So, you can still, like, pop into those calls and actually, you know, still get Carmen and Jacqueline to be able to actually look at your ad accounts in real time.

**[00:02:40] m3.t0018** Whitney Hodges: Um, and offer advice and suggestions. So, I wanted to see if that's something that was of interest to you, and if you wanted to kind of take a closer look, um, at any of that. Um, it's definitely a lot more cost-effective than the ongoing.

**[00:02:55] m3.t0019** Whitney Hodges: agency fees. So just wanted to kind of.

**[00:02:59] m3.t0020** Whitney Hodges: See what you thought.

**[00:03:00] m3.t0021** Kelly Scaramella: Does it cost money to join those weekly calls?

**[00:03:04] m3.t0022** Whitney Hodges: So, it's a monthly fee to kind of be a part of the, um, accelerators. So, for both, like, the Google Ads support and the Meta Ads support, it's just a recurring monthly fee of $397, and then you can join those weekly calls anytime, and that's included.

**[00:03:22] m3.t0023** Whitney Hodges: Now, if you didn't necessarily want to be, like, locked into a monthly recurring thing, um, what I could do is just share links with you for you to be able to, like, on a one-off book, a paid consultation with Jacqueline to look at Meta Ads, or a paid consultation to look at Carmen, or to meet with Carmen to look at Google Ads.

**[00:03:40] m3.t0024** Whitney Hodges: Um, and those calls are $297 each, right? So you could kind of just, like, book those as needed a couple of times a year, or maybe once a quarter, or something like that. So that's an option for you, too.

**[00:03:50] m3.t0025** Kelly Scaramella: Okay.

**[00:03:51] m3.t0026** Kelly Scaramella: Yeah, that probably would make more sense for me.

**[00:03:54] m3.t0027** Whitney Hodges: Okay, got it. Sounds good. Um, so I can definitely get you the links to those, just so that you, like, you know, have them, um, so you can kind of, like, book in for that, um, as needed. And what I'll also do…

**[00:04:09] m3.t0028** Whitney Hodges: is… if it would be helpful for you, Kelly, I'll go ahead and, like, send you some resources, some videos of, like, how to be able to access your ad account data, right? How to, like, log in, like, what to look out for in terms of, like, metrics and benchmarks, just so you're not, you know.

**[00:04:25] m3.t0029** Whitney Hodges: feeling like you're kind of like totally in the dark right about how to like check on things and and look at how things are are going. Would that be helpful?

**[00:04:32] m3.t0030** Kelly Scaramella: Okay.

**[00:04:34] m3.t0031** Kelly Scaramella: Yeah.

**[00:04:34] m3.t0032** Whitney Hodges: Okay, perfect. Great. What other questions, concerns can I help you with at this point?

### m3_leadlock_pricing_guide_help

A client asked for help with a specific LeadLock update, and Whitney demonstrated the relevant workflow while identifying additional routes for real-time support.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["wia_expertise", "service_value", "audience_insight"], "destination": "public_opportunity", "wia_contribution": "Whitney located the pricing link within the inquiry workflow, showed how to update and save it, and pointed Kelly to the support form and office hours.", "attention_reason": "This may reveal how hands-on guidance helps a business owner maintain inquiry materials, without claiming that a single demonstration resolved all future support needs.", "research_questions": ["Did Kelly complete the update after the call, and are the demonstrated LeadLock workflow and support routes still current?"]}

**Qualifications:** ["The workflow and support options are described as they appeared in this account at the time of the call; current product details are not verified.", "The exchange does not confirm that Kelly completed the pricing-guide update.", "No publication permission is supplied."]

**[00:04:40] m3.t0033** Kelly Scaramella: Well, I don't really know how to use LeadLock, um, so I was hoping maybe you could show me a few things on LeadLock, like, especially, like, how to change, um, when I have a new pricing guide, like, how to swap that out.

**[00:04:55] m3.t0034** Kelly Scaramella: Like, things like that.

**[00:04:56] m3.t0035** Whitney Hodges: Definitely, yes. Happy to show you more about that. And then also, so you're aware as well, Danielle, who's our Lead Lock Specialist, does have weekly office hours for Lead Lock on Wednesdays that you can always come to.

**[00:05:13] m3.t0036** Whitney Hodges: if there's ever, like, a question or something that kind of, like, pops up and, you know, you want her to show you how to do things in real time, you totally can. Um, there's also… here, let me share my screen really quick.

**[00:05:26] m3.t0037** Whitney Hodges: Uh…

**[00:05:31] m3.t0038** Whitney Hodges: So, inside of your LeadLock account, there's this button here called Get Support.

**[00:05:39] m3.t0039** Whitney Hodges: So at any point, if you have a question for us, you can just fill out this. It can be as simple as like you just like letting us know of a question that that you have. And we'll get back to you on that. I'll also make sure when I follow up with you via email to give you the the link.

**[00:05:59] m3.t0040** Whitney Hodges: And kind of, like, the timing of that weekly office hours meeting for LeadLock, so that you have that as well. Um, but as far as, like, updating pricing brochures, things like that, um…

**[00:06:12] m3.t0041** Whitney Hodges: Your… everything that's kind of related to your inquiries and how they are being responded to.

**[00:06:20] m3.t0042** Whitney Hodges: is…

**[00:06:23] m3.t0043** Whitney Hodges: within this kind of automation tab here. It's gonna be your inquiry workflows.

**[00:06:29] m3.t0044** Whitney Hodges: So, inside your inquiry form workflow here.

**[00:06:34] m3.t0045** Whitney Hodges: um, we can see, like, this is where the majority of leads are… are being, um, responded to when they, you know, submit that inquiry form. Um, so in here…

**[00:06:48] m3.t0046** Whitney Hodges: All you would need to do would be to go into this first inquiry welcome email right here.

**[00:06:58] m3.t0047** Whitney Hodges: And then, like, this is the email itself, which has the details inside. And let's see, I don't know that it has an actual attachment. So if you wanted to include it actually as an attachment, you can click this Add Attachments here and add it as an attachment.

**[00:07:15] m3.t0048** Whitney Hodges: But I think what's going on currently is it's probably a link.

**[00:07:20] m3.t0049** Whitney Hodges: Um, that's in here.

**[00:07:24] m3.t0050** Whitney Hodges: So just give it a second to load.

**[00:07:29] m3.t0051** Whitney Hodges: Yeah, so right here it says, I've attached our packages and pricing for your review, so that's a link. So you would just go in here to the link text.

**[00:07:39] m3.t0052** Whitney Hodges: Update that to your, you know, updated link, whatever you're using as far as your Google Drive. Click Save here, and then you'd click Save here, and then, uh, the email itself would be updated.

**[00:07:54] m3.t0053** Whitney Hodges: But then what you would also want to do here is save the action, like, you just want to save everything, right, whenever you're making updates. Save the action, and then save the workflow, and that would all be updated. Um, but of course, you know, you can pop into Danielle's office hours, too, if you kind of want some.

**[00:08:12] m3.t0054** Whitney Hodges: hand-holding in real time to make sure that it gets done the right way.

**[00:08:15] m3.t0055** Kelly Scaramella: Okay.

**[00:08:17] m3.t0056** Whitney Hodges: Any other questions about lead block?

**[00:08:17] m3.t0057** Kelly Scaramella: Great!

**[00:08:19] m3.t0058** Kelly Scaramella: No, that was my main question.

**[00:08:21] m3.t0059** Whitney Hodges: Okay.

**[00:08:23] m3.t0060** Whitney Hodges: Perfect.

**[00:08:24] m3.t0061** Whitney Hodges: All right. Well, um, I'll be in touch with kind of all those resources, links, um, things like that, because I want you to kind of, like, feel empowered, right, to be taking this on on your own and not like you're just kind of, you know, DIYing it, um, in the dark.

### m4_realistic_ad_monitoring

Whitney tailored a proposed monitoring routine to a time-constrained venue owner by separating spend limits from performance risk and explaining which account signals might justify closer investigation.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["audience_insight", "wia_expertise", "service_value"], "destination": "public_opportunity", "wia_contribution": "Whitney clarified the difference between budget limits and inefficient spend, compared platform behavior, demonstrated account signals, and offered a recurring review as an accountability option.", "attention_reason": "The exchange shows how monitoring advice can be scaled to an owner's time and risk concerns rather than assuming daily review is feasible.", "research_questions": []}

**Qualifications:** ["Account performance and examples were discussed during one live review and are not independently corroborated.", "The suggested check-in routine and support options were recommendations; Kate did not report adopting them in this interval.", "No subsequent performance or monitoring outcome is given."]

**[00:09:17] m4.t0088** Kate Walton - Hazelwood Weddings: I guess my… I'm so confident that, like, the ads are running. The ads are the ads. We got all the different levels, top of funnel, middle. It's all happening. I guess the biggest issue is if something like the high spend would happen again.

**[00:09:22] m4.t0089** Whitney Hodges: Right.

**[00:09:32] m4.t0090** Whitney Hodges: Mm-hmm.

**[00:09:32] m4.t0091** Kate Walton - Hazelwood Weddings: And…

**[00:09:34] m4.t0092** Kate Walton - Hazelwood Weddings: I… the problem is that it's more money going toward…

**[00:09:39] m4.t0093** Kate Walton - Hazelwood Weddings: the same amount of money is being spent, but it's being shown to less people when the cost gets that high, is that correct? So, really, that's the worst thing that could happen. Like, if that happened again, that's what would happen, and… but it's not like I would be charged more money, my ad just wouldn't be shown as much.

**[00:09:45] m4.t0094** Whitney Hodges: Correct.

**[00:09:50] m4.t0095** Whitney Hodges: Mm-hmm.

**[00:09:56] m4.t0096** Kate Walton - Hazelwood Weddings: So is that, that's like the worst thing that could happen, right?

**[00:10:02] m4.t0097** Whitney Hodges: Mm-hmm. Yeah, I mean…

**[00:10:03] m4.t0098** Kate Walton - Hazelwood Weddings: ads aren't gonna break or stop showing, they're just… it's the… the spend could get to a point that's not great. That's something that I would… I could miss, right? Is that, like, the worst thing that could happen?

**[00:10:12] m4.t0099** Whitney Hodges: Yeah.

**[00:10:14] m4.t0100** Whitney Hodges: So the budget's set, right? Like to where there's like a cap on it. It's not like Google or Meta is just going to start charging you like even more, right? But it is a matter of like, is that spend worth it? Kind of like you were saying, right?

**[00:10:30] m4.t0101** Kate Walton - Hazelwood Weddings: Mmhm.

**[00:10:30] m4.t0102** Whitney Hodges: You could be spending, you know, $500 a month on the meta ads, but, you know, if performance has fallen off, they're not necessarily generating leads. Right? Or, you know, it costs a lot more just to kind of, like, get in front of people, get in front of audiences.

**[00:10:46] m4.t0103** Whitney Hodges: Other things that could potentially happen could be that the ads stop running, you know, sometimes it's, like, if a payment doesn't go through, or, um, I don't know, we'll come across weird, like, glitchy things every once in a while, where, for whatever reason, an ad stops running. Now, usually you would get some sort of, like.

**[00:10:47] m4.t0104** Kate Walton - Hazelwood Weddings: Mm-hmm.

**[00:11:00] m4.t0105** Kate Walton - Hazelwood Weddings: Yes.

**[00:11:04] m4.t0106** Whitney Hodges: Alert about that, like an email sent to you, um, if an ad were to ever, you know.

**[00:11:11] m4.t0107** Whitney Hodges: get rejected, or if there's an issue within the account, or a payment doesn't go through, or… or something like that. Um, so… so those are kind of, like, the two scenarios, right? Like, that ads actually do stop running, or that…

**[00:11:13] m4.t0108** Kate Walton - Hazelwood Weddings: No.

**[00:11:18] m4.t0109** Kate Walton - Hazelwood Weddings: Okay.

**[00:11:25] m4.t0110** Kate Walton - Hazelwood Weddings: Okay.

**[00:11:26] m4.t0111** Whitney Hodges: You know, they're spending money, but it's not necessarily bringing in great results. So typically, the way to mitigate that, right, would be doing, like, a quick 5-minute check of your Google Ads and your Meta Ads, like, once a week.

**[00:11:32] m4.t0112** Kate Walton - Hazelwood Weddings: Right.

**[00:11:40] m4.t0113** Kate Walton - Hazelwood Weddings: Mmhm.

**[00:11:41] m4.t0114** Whitney Hodges: Sort of thing, kind of based on those metrics and benchmarks that we shared here for you. Um, but sometimes we see, you know, with, like, busy venue owners, that that's maybe not necessarily realistic, or, like, balls get dropped, or something kind of, like, falls through the cracks. And that's when some venue owners really like having that, like, a recurring meeting on their calendar.

**[00:11:46] m4.t0115** Kate Walton - Hazelwood Weddings: Mm-hmm.

**[00:11:56] m4.t0116** Kate Walton - Hazelwood Weddings: Okay.

**[00:12:02] m4.t0117** Whitney Hodges: Once a month, because it's something that helps hold them accountable to where they know, okay, this is… it's gonna get checked on at least once a month, because this meeting is on the calendar, and it's gonna happen with a wedding industry ads person, you know?

**[00:12:05] m4.t0118** Kate Walton - Hazelwood Weddings: Uh-huh.

**[00:12:12] m4.t0119** Kate Walton - Hazelwood Weddings: Right.

**[00:12:15] m4.t0120** Kate Walton - Hazelwood Weddings: Right.

**[00:12:15] m4.t0121** Whitney Hodges: So…

**[00:12:17] m4.t0122** Kate Walton - Hazelwood Weddings: Yeah, I… I'm not gonna be able to look at it every week, not right now, but eventually I'll be able to do that, but I… what I do see every week is the receipt, like, the meta receipt gets sent to our email, so I see that… I think it's every week, it feels like it's all the time, like, I'm getting those.

**[00:12:21] m4.t0123** Whitney Hodges: Mm-hmm. Right.

**[00:12:23] m4.t0124** Whitney Hodges: Great.

**[00:12:26] m4.t0125** Whitney Hodges: Mm-hmm.

**[00:12:28] m4.t0126** Whitney Hodges: Good.

**[00:12:30] m4.t0127** Whitney Hodges: Mm-hmm.

**[00:12:32] m4.t0128** Whitney Hodges: Yeah.

**[00:12:33] m4.t0129** Kate Walton - Hazelwood Weddings: So I can at least see the amount, but I look at it, but I don't really know what it means. So to actually tell, like, when I'm in the Meta Business Suite, like.

**[00:12:38] m4.t0130** Whitney Hodges: Right.

**[00:12:43] m4.t0131** Whitney Hodges: Mm-hmm.

**[00:12:45] m4.t0132** Kate Walton - Hazelwood Weddings: do I need to go and look in that document you shared to see, like, what I need to look for? Like, I'm kind of familiar… last time I looked at it was probably with Christina, so that was a long time ago, like, when I was actually logged in and looking at it. Um…

**[00:12:54] m4.t0133** Whitney Hodges: Mm-hmm.

**[00:12:57] m4.t0134** Whitney Hodges: Yeah, thanks.

**[00:12:58] m4.t0135** Whitney Hodges: Mm-hmm.

**[00:13:00] m4.t0136** Whitney Hodges: Mm-hmm.

**[00:13:02] m4.t0137** Kate Walton - Hazelwood Weddings: Yeah, and when Jacqueline had found the thing that was too expensive, that was Meta, not Google, right?

**[00:13:07] m4.t0138** Whitney Hodges: Mm-hmm.

**[00:13:09] m4.t0139** Whitney Hodges: Right. Mm-hmm. Yeah. Mm-hmm.

**[00:13:11] m4.t0140** Kate Walton - Hazelwood Weddings: Google, we haven't… Google, we haven't done as much. That's been more kind of just going, and you checked on it, and you said things looked good, right?

**[00:13:18] m4.t0141** Whitney Hodges: Google's been really steady for a long time. Um, Christina actually moved on to a new opportunity, and so she hasn't been on the team since February, and I think that's when she kind of, like, last looked at things for you, and then we had Carmen go in last week and take a look.

**[00:13:22] m4.t0142** Kate Walton - Hazelwood Weddings: Okay.

**[00:13:35] m4.t0143** Whitney Hodges: Um, and she said that, like, everything was, like, looking perfect, and, like, she wouldn't recommend any changes. So Google…

**[00:13:42] m4.t0144** Whitney Hodges: is in a really good spot, and it's been in a really good spot for a while. Meta is oftentimes where we can see the potential of there being more volatility because of creative fatigue or or things like that.

**[00:13:47] m4.t0145** Kate Walton - Hazelwood Weddings: Uh-huh.

**[00:13:57] m4.t0146** Kate Walton - Hazelwood Weddings: So, Google would be more of, like, a safe, like… I haven't even… I can… I'm sure I just go in and… I haven't even looked at Google Ads, I can't tell you the last time I did that. Again, it was probably with Christina in February, um, so…

**[00:14:05] m4.t0147** Whitney Hodges: Mm-hmm.

**[00:14:09] m4.t0148** Whitney Hodges: Right. Mm-hmm.

**[00:14:12] m4.t0149** Kate Walton - Hazelwood Weddings: That one…

**[00:14:14] m4.t0150** Kate Walton - Hazelwood Weddings: how would I know? I guess I just need to check that every week, or I need to go in and look, because…

**[00:14:17] m4.t0151** Whitney Hodges: Mm-hmm.

**[00:14:20] m4.t0152** Kate Walton - Hazelwood Weddings: that is being just shown to the same couples who search certain things. It's not the retargeting logistics, like…

**[00:14:29] m4.t0153** Kate Walton - Hazelwood Weddings: the meta ads are, right? So Google is, like, safer to assume it's running properly.

**[00:14:34] m4.t0154** Whitney Hodges: Right. Yeah. So on Google, you know, it, your ads are showing up based on the keywords that people are actually searching for, right? So it's like, you know, couples with high intent looking for a venue in your area, your ad is going to show up. They are not actually going, you're not actually going to pay ad spend to Google unless someone is actually clicking on your ad.

**[00:14:43] m4.t0155** Kate Walton - Hazelwood Weddings: Mm-hmm.

**[00:14:47] m4.t0156** Kate Walton - Hazelwood Weddings: Mm-hmm.

**[00:14:56] m4.t0157** Kate Walton - Hazelwood Weddings: Mmhm.

**[00:14:57] m4.t0158** Whitney Hodges: Versus Meta, where it's like, if your ad is being shown to people, like, you're… you're being charged for that, no matter what, sort of thing. Um, I would definitely recommend checking out the resources that I kind of shared inside that doc, but at, like, a high level, if I were you, just, like, wanting to check in on things.

**[00:15:17] m4.t0159** Whitney Hodges: Um, as far as your ad account, so, um, it's adsmanager.facebook.com that you should be able to just.

**[00:15:25] m4.t0160** Whitney Hodges: type into your browser, and it should take you here. And then you can really easily change the date ranges in this section here. So, like, it's defaulting to, like, the last 30 days, right?

**[00:15:39] m4.t0161** Whitney Hodges: And, um…

**[00:15:42] m4.t0162** Whitney Hodges: It's gonna tell you, right, the conversion campaign has brought in 28 leads in the last 30 days.

**[00:15:47] m4.t0163** Kate Walton - Hazelwood Weddings: Okay.

**[00:15:49] m4.t0164** Whitney Hodges: $21 a week. So that's great, right? But if you were to log in next month, or a couple of weeks from now, and this number is.

**[00:15:50] m4.t0165** Kate Walton - Hazelwood Weddings: Mmhm.

**[00:16:00] m4.t0166** Whitney Hodges: considerably lower, right? Or the cost per lead is considerably higher, or it's showing, like, zero website leads, something like that, then that's when there would be, like.

**[00:16:02] m4.t0167** Kate Walton - Hazelwood Weddings: Right.

**[00:16:10] m4.t0168** Whitney Hodges: That should raise a red flag for you, essentially.

**[00:16:13] m4.t0169** Kate Walton - Hazelwood Weddings: Okay, this is very helpful. This is what I need to know, because I can quick log in, and I remember seeing this before, so when I'm looking at the results, would it be highlighted in red if it was something drastic?

**[00:16:18] m4.t0170** Whitney Hodges: No.

**[00:16:24] m4.t0171** Whitney Hodges: Not necessarily, no. I mean, sometimes you'll get alerts from Meta of, like, your cost per lead is going up, or your cost per impression is going up, or things like that, but that doesn't necessarily always mean that you need to pay attention to it, honestly, if that makes sense, because sometimes they're just trying to get you to, like.

**[00:16:25] m4.t0172** Kate Walton - Hazelwood Weddings: Okay.

**[00:16:35] m4.t0173** Kate Walton - Hazelwood Weddings: Mmhm.

**[00:16:39] m4.t0174** Kate Walton - Hazelwood Weddings: Mm-hmm.

**[00:16:43] m4.t0175** Whitney Hodges: spend more money, or, like, change things necessarily. Um, but yeah, if you were even just, like, once a week, or able to just check in and make sure that this campaign is still generating leads, you know, at a cost per lead, essentially, that you are comfortable with, like.

**[00:16:44] m4.t0176** Kate Walton - Hazelwood Weddings: Right.

**[00:16:54] m4.t0177** Kate Walton - Hazelwood Weddings: Mm-hmm.

**[00:17:00] m4.t0178** Whitney Hodges: that really is all you need to check. It's only when you don't see the leads coming in, or you see the cost per lead, you know, going up, that at that point, it's really time to, like.

**[00:17:11] m4.t0179** Whitney Hodges: dig in and look deeper in terms of, okay, well, what is cost per click looking like? Or, you know, has my cost per impression gone way up? And again, in that kind of metrics and benchmarks curriculum that I provided, like, it goes into more detail, kind of, about what to look out for.

### m4_google_conversion_correction

During an account walkthrough, Whitney corrected a potentially misleading description of a tracked conversion: a book-a-tour page view was not a completed tour booking.

**Individual parser check (diagnostic only):** failed

**Provisional discovery:** {"lenses": ["wia_expertise", "broader_principle"], "destination": "public_opportunity", "wia_contribution": "Whitney reviewed the account's conversion actions and explicitly corrected the interpretation of a book-a-tour page view.", "attention_reason": "The correction is a compact example of why measurement labels should be checked against the action they actually represent.", "research_questions": []}

**Qualifications:** ["The correction concerns conversion actions shown in this account; it does not establish how other accounts are configured.", "The exchange does not verify that every reported conversion was an actual inquiry or booking."]

**[00:23:37] m4.t0248** Whitney Hodges: So it's gonna tell us here. So these are all of your conversion actions, and it's basically things that people are doing on the website, right? So when they get to that first, uh, looks like your home page, right? The different buttons that are available to them for them to be able to click on.

**[00:23:41] m4.t0249** Kate Walton - Hazelwood Weddings: No.

**[00:23:49] m4.t0250** Kate Walton - Hazelwood Weddings: Okay.

**[00:23:53] m4.t0251** Whitney Hodges: Um, so…

**[00:23:53] m4.t0252** Kate Walton - Hazelwood Weddings: Mmhm.

**[00:23:54] m4.t0253** Whitney Hodges: Going to the contact page, so that the page view loading of the contact page, definitely important. Um, but then submitting a lead form also, right, where that's them actually inquiring with you.

**[00:24:10] m4.t0254** Kate Walton - Hazelwood Weddings: Mmhm.

**[00:24:12] m4.t0255** Whitney Hodges: Then you're able to see here too.

**[00:24:15] m4.t0256** Whitney Hodges: Um, if they have booked a tour or not. Like, um, or I guess this wouldn't be if they've actually booked the tour, this is them looking at the book a tour page.

**[00:24:26] m4.t0257** Kate Walton - Hazelwood Weddings: Gotcha.

**[00:24:27] m4.t0258** Whitney Hodges: Oh.

**[00:24:28] m4.t0259** Whitney Hodges: So you can see all of those items for both of these campaigns. And so the conversions column right here, this is the number of times within the given date range that those things are happening. Okay, so this is all time, right? So you're probably not going to want to look at it like that. You're probably going to want to look at it.

**[00:24:47] m4.t0260** Kate Walton - Hazelwood Weddings: Okay.

**[00:24:48] m4.t0261** Whitney Hodges: Like, within the last 7 days.

**[00:24:50] m4.t0262** Kate Walton - Hazelwood Weddings: Okay.

**[00:24:50] m4.t0263** Whitney Hodges: If you're checking on it weekly. So, I mean, all of I think all of these numbers look great. Right? Like, you know, 4 leads from, the Google ads, 4 people submitting the lead form, 13 people looking at the book a tour page.

**[00:25:06] m4.t0264** Whitney Hodges: Um…

**[00:25:06] m4.t0265** Kate Walton - Hazelwood Weddings: Great, from the last 7 days, yeah.

**[00:25:08] m4.t0266** Whitney Hodges: Exactly. Mhmm. Yeah. Yeah. And you can see it, you know, kind of how it's it's different between the the two campaigns. So that's really what you're gonna wanna be looking at on the the Google ad side of things. Right? Are these conversions happening? Are people submitting the lead forms? Are they looking at the book a tour page? Like, those are gonna be your your highest level actions that could be happening.

### m5_accelerator_fit

Whitney matched a self-directed venue couple who wanted to learn campaign setup with the described Accelerator support, rather than defaulting to full-service management.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["audience_insight", "wia_expertise", "service_value"], "destination": "public_opportunity", "wia_contribution": "Whitney clarified the prospects' desired level of ownership, distinguished managed service from education and support, and explained the Accelerator option and optional setup assistance.", "attention_reason": "The exchange may help explain how support can fit capable owners who want guidance before deciding whether to delegate more.", "research_questions": []}

**Qualifications:** ["The booking and lead figures are the prospects' reported claims, not independently verified outcomes.", "Their positive response does not establish purchase or enrollment.", "The program scope described is specific to this call and is not verification of current offer details."]

**[00:05:17] m5.t0011** victoriamelvin-propert: We just had one call with her, too. We've had calls with a couple other people just trying to figure out… we feel like we're, like, 95% there, and we're just trying to close that last little gap, so that it just… things get easier, and calmer, and more manageable, and just kind of starting to roll on its own a little bit.

**[00:05:32] m5.t0012** Whitney Hodges: Okay, I hear you. Sounds good. So, um, I got a little bit of context from, you know, Tirza's introduction, just in terms of, like, you kind of dabbling with the meta ads, and, like, creating your own email and text funnel, which is awesome. So, I would really just kind of love to hear from you, like.

**[00:05:49] m5.t0013** Whitney Hodges: Where you feel like you're currently out with things, like, what you've tried but maybe hasn't worked, like, where you're kind of feeling like you need the most.

**[00:05:58] m5.t0014** Whitney Hodges: Help or guidance right now, so we…

**[00:05:59] m5.t0015** victoriamelvin-propert: Right now, we have more of a lead problem. Um, we did… we've been open for 4 years. We only did 3… sorry, Blair's going on his own computer. We only did 3 weddings the first 2 years we were open, because we just tested in the water, so last year we said, let's just jump in and do it.

**[00:06:02] m5.t0016** Whitney Hodges: Okay.

**[00:06:10] m5.t0017** Whitney Hodges: No, that's okay.

**[00:06:17] m5.t0018** Whitney Hodges: Okay.

**[00:06:17] m5.t0019** victoriamelvin-propert: We booked 25 weddings within the year for the year. Uh, just organically, a little bit of going viral, um, our iteration on our building went viral, but that's, you know, years ago at this point. Um, so this year, we just want to…

**[00:06:20] m5.t0020** Whitney Hodges: Right.

**[00:06:23] m5.t0021** Whitney Hodges: Yeah.

**[00:06:25] m5.t0022** Whitney Hodges: Nice.

**[00:06:32] m5.t0023** victoriamelvin-propert: we just want to get it right and in order and fixed, and we finally sat down. I made that funnel, like, 6 weeks ago, so it's still pretty new. We started messing with meta ads about 6 weeks ago, and they've been working pretty well, and we have gotten, like, I think we've gotten 16 good leads from that so far in 6 weeks.

**[00:06:39] m5.t0024** Whitney Hodges: Okay.

**[00:06:45] m5.t0025** Whitney Hodges: Mm-hmm.

**[00:06:47] m5.t0026** Blair Propert: Yep.

**[00:06:48] m5.t0027** Whitney Hodges: Nice.

**[00:06:48] m5.t0028** victoriamelvin-propert: Um, and then we started Google today, just playing around with it, trying to figure it out, because we want to understand it, um, but we know we don't know everything.

**[00:06:50] m5.t0029** Whitney Hodges: Thank you.

**[00:06:53] m5.t0030** Whitney Hodges: Right.

**[00:06:56] m5.t0031** Whitney Hodges: Uh-huh. Okay.

**[00:06:57] m5.t0032** victoriamelvin-propert: Um, but my background is in marketing, but, like, in… I'm on set, like, I build the sets, design the sets, like… but, like, on a global scale, so, like, I can create all the content that you need, and, like, know all the models, and can do all that, but, like, where to put it to be most proactive is where I think we struggle.

**[00:07:02] m5.t0033** Whitney Hodges: Oh, cool.

**[00:07:12] m5.t0034** Whitney Hodges: Okay, gotcha. Okay, sounds good. So I think kind of what I'm hearing, right, is that, you know, you know you need to be running Meta Ads and Google Ads, which you've started, right, in order to kind of see that lead volume to get you where you want to be. But maybe it kind of feels.

**[00:07:32] m5.t0035** Whitney Hodges: Like, right now that you're kind of shooting in the dark, like, shooting from the hip, like, it started, but you don't necessarily know if it's set up the right way, or optimized, or whatever.

**[00:07:39] m5.t0036** victoriamelvin-propert: Yep.

**[00:07:41] m5.t0037** victoriamelvin-propert: We're just trying everything. Like Meta, we found three people, we followed three different structures, one performed better, so then we went back to just started that guy over again. So, we know that's not 100% right, but we just want to learn, and we know that we don't know everything, so…

**[00:07:46] m5.t0038** Whitney Hodges: Mm-hmm.

**[00:07:51] m5.t0039** Whitney Hodges: Uh-huh.

**[00:07:56] m5.t0040** victoriamelvin-propert: You know, y'all do.

**[00:07:59] m5.t0041** Whitney Hodges: Gotcha, yeah. So, we typically work with clients in, like, one of two different capacities, right? So, for some venues, and this is typically for the venues that are a bit more established, right? Um, you know, typically, you know, um.

**[00:08:14] m5.t0042** Whitney Hodges: have already been running ads for a while, sort of thing, they'll usually have us kind of come in and, like, take over and manage everything for them, sort of thing. That's typically for the business owner who doesn't necessarily want to learn it, um, or kind of knows enough about it, but is.

**[00:08:31] m5.t0043** Whitney Hodges: so busy, like, being pulled in so many other directions that they're just like, I need somebody else to handle it. It doesn't sound like that's you guys, though. I think that you would be more of, um, our accelerator tracks, or our accelerator programs, or what they're called. And so what those are really meant to do is to help you think.

**[00:08:51] m5.t0044** Whitney Hodges: like an ad strategist, to help you really understand what's going on with the campaigns, the right ways that those should be set up, right? Like.

**[00:09:02] m5.t0045** Whitney Hodges: reading the data, understanding what decisions to make, kind of based on what the data is telling you, sort of thing, moving forward. And so, we do have our Google Search Accelerator program that's focused on the Google side, we have our Meta Ads Accelerator that's focused on the Meta Ads side, but then.

**[00:09:20] m5.t0046** Whitney Hodges: you know, obviously you could do both, right? Simultaneously, or one kind of after, um, the other. So, that would be probably the direction that I think that I would recommend for you, because it lets you kind of, you know, continue really kind of running and managing ads.

**[00:09:38] m5.t0047** Whitney Hodges: on your own, but really gives you the support to know what's working versus what's not working. You know the the support that is entailed right is going to be some learning elements of it. Right? A lot of just kind of curriculum about the foundations for success with ads in terms of what you should have in place as far as funnels or landing pages.

**[00:10:02] m5.t0048** Whitney Hodges: Which it sounds like, um, you know, you've… you've already done quite a bit, um, on your own. But could also just be good to kind of get our perspective on it, too, from just kind of more of that… that ads expert's, um, point of view.

**[00:10:16] m5.t0049** Whitney Hodges: Um, but then there's also going to be support through office hours calls that happen twice a week, um, with a Meta Ads call and a Google Ads call run by, you know, experts in those areas, basically, where you can have them really looking at your accounts in real time.

**[00:10:34] m5.t0050** Whitney Hodges: Telling you, kind of, what they are seeing, so helping you to really, kind of, understand the data that way. Making suggestions, or even making adjustments inside the accounts, um, in real time.

**[00:10:46] m5.t0051** Whitney Hodges: On the meta ad side of things, like you've probably kind of seen already, um, it's…

**[00:10:52] m5.t0052** Whitney Hodges: I guess the… what's the right way to word this? Not that it's, like, not as straightforward as Google, but there's so much more that goes into it, right? Like, you've got your headline, you've got your copy, you've got your creatives, um, and so many different objectives to choose from, right? And so…

**[00:10:58] m5.t0053** victoriamelvin-propert: Oh, it's awful. It's awful.

**[00:11:00] m5.t0054** Blair Propert: It's a nightmare.

**[00:11:02] m5.t0055** Blair Propert: It's a nightmare.

**[00:11:03] m5.t0056** victoriamelvin-propert: Yeah.

**[00:11:08] m5.t0057** victoriamelvin-propert: Yeah, that's stupid pixel.

**[00:11:09] m5.t0058** Whitney Hodges: Um…

**[00:11:11] m5.t0059** Whitney Hodges: Exactly, yeah, getting the tracking right and all of that. So, um, I would say that kind of the curriculum does go a little bit more in-depth on the meta ad side, with lots of examples of, like, what really works well for a top-of-funnel ad versus a bottom-of-funnel ad versus.

**[00:11:13] m5.t0060** victoriamelvin-propert: Yeah.

**[00:11:27] m5.t0061** Whitney Hodges: you know, running conversion campaigns to get more tours booked, um, sort of thing. Um, and then there are elements inside of the program that are kind of more, um, done for you, and I would say it's really kind of up to you whether or not you would want to leverage that.

**[00:11:43] m5.t0062** Whitney Hodges: piece of it, because for you, you know, you do already have campaigns running, right? But if you wanted us to go in and launch initial campaigns for you, launch meta ads for you, so that you can kind of see the way that we.

**[00:11:58] m5.t0063** Whitney Hodges: do it, right? And, like, have us kind of set up all the targeting, all the different things, that way you have that campaign there that's already really kind of structured based on our expertise, and then could always, like, copy it, duplicate it in the future, make changes in the future.

**[00:12:14] m5.t0064** Whitney Hodges: That is a piece of it that is included as well.

**[00:12:18] m5.t0065** victoriamelvin-propert: No, that's great. That's what we… we've just, like I said, we tried three different things, and they're like, okay, this one seems to work the best. Drop it in chat, let it read it. He's our data guy. Blair loves all the numbers. Um, so he… he started the Google stuff today. So, yeah, no, that sounds great.

### m5_campaign_attribution_diagnosis

A client clarification changed the attribution diagnosis: a separate ads-only form could identify paid leads, while UTMs and hidden fields were proposed for campaign-level detail.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["wia_expertise", "audience_insight", "broader_principle"], "destination": "public_opportunity", "wia_contribution": "Whitney asked about form and landing-page differences, revised her diagnosis after Victoria's clarification, and described UTM parameters and hidden fields as a possible campaign-level tracking layer.", "attention_reason": "This is a clear demonstration of client knowledge changing a technical recommendation, with the implementation outcome still open.", "research_questions": ["Were UTMs and hidden form fields later added, and did the resulting data distinguish the campaigns in HoneyBook?"]}

**Qualifications:** ["The UTM and hidden-field setup was proposed, not confirmed as implemented.", "No campaign-level results or subsequent attribution accuracy are reported.", "The lead counts and uncertainty are reported by the prospects."]

**[00:14:21] m5.t0096** Blair Propert: uh, I've talked to Vic about it, like, if there's a way for us to do a better job on our end, so we use HoneyBook as our capture and lead guide, um, and how we can track that better, of where theirs are actually coming from. So we ran a couple that overlapped.

**[00:14:30] m5.t0097** Whitney Hodges: Hmm?

**[00:14:37] m5.t0098** Blair Propert: Just to see, um, and we targeted them separately. Um, so one was just kind of open ended and the other one was, you know, um, with the pixel and a little bit more direct targeted. Um, and truthfully, we got leads, which was amazing. And they came in, but honestly, I don't know where they came from.

**[00:14:46] m5.t0099** Whitney Hodges: Mm-hmm.

**[00:14:50] m5.t0100** Whitney Hodges: Yeah.

**[00:14:53] m5.t0101** Blair Propert: like, if they came for… like, yes, they say, uh, um, some of the tracking on the meta was saying, you know, we're getting this many, you know, on the landing page and that, but I just thought that there might be something we could be doing as well, um, that maybe you could assist us with in the future of what that looks…

**[00:14:53] m5.t0102** Whitney Hodges: Mmhm.

**[00:15:02] m5.t0103** Whitney Hodges: Mm-hmm.

**[00:15:07] m5.t0104** Whitney Hodges: Mm-hmm.

**[00:15:09] m5.t0105** Blair Propert: to be able to utilize HoneyBook even more, which we are familiar with, too, on the investment… excuse me, the landing page and the guide, just because I feel like that will help shape what comes next.

**[00:15:13] m5.t0106** Whitney Hodges: Mm-hmm.

**[00:15:19] m5.t0107** Whitney Hodges: Mm-hmm.

**[00:15:23] m5.t0108** Whitney Hodges: Definitely, yes, yeah. So, okay, so I think what I'm hearing is that you have, like, a landing page that you've created for lead generation, but you're maybe using that in, like, a variety of different ways to where, like, organic traffic could hit it, or paid traffic could hit it, sort of thing, and you can't attribute.

**[00:15:31] m5.t0109** Blair Propert: Yep.

**[00:15:40] m5.t0110** Whitney Hodges: where the leads have actually come from? Is that kind of the issue?

**[00:15:46] m5.t0111** Blair Propert: Uh, yes, Vic, I'll let you go on that one, because you created it, so I can't…

**[00:15:47] m5.t0112** Whitney Hodges: Thanks.

**[00:15:49] m5.t0113** victoriamelvin-propert: No, it's not public. It's only… it's a landing page that's only for our ads. We've tried lead ads, we've tried conversion ads, just, like, the awareness ads seem to be doing the best for us right now, but, um, our building also was abandoned for 40 years, so I think that that's just a constant struggle of, like, oh, is it fixed.

**[00:15:53] m5.t0114** Whitney Hodges: Okay.

**[00:15:58] m5.t0115** Whitney Hodges: Mm-hmm.

**[00:16:04] m5.t0116** Whitney Hodges: Mm-hmm.

**[00:16:06] m5.t0117** Whitney Hodges: Yeah.

**[00:16:06] m5.t0118** victoriamelvin-propert: Uh…

**[00:16:07] m5.t0119** victoriamelvin-propert: So, and then, like, trying to… next step on our list was, like, trying to figure out how the retargeting thing worked, but it is far… the meta thing is very complicated, and we just haven't quite figured out.

**[00:16:18] m5.t0120** Whitney Hodges: Mm-hmm.

**[00:16:19] m5.t0121** victoriamelvin-propert: Like, the marketing part, I can get the targeting, I can get, like, the zip code, the searching, the what else are they looking for, I can get all that part, but, like, just actually getting the ad set up correctly, like, is it an awareness ad, is it leads, like, that part is what I think is most confusing for us.

**[00:16:33] m5.t0122** Blair Propert: Yep.

**[00:16:35] m5.t0123** victoriamelvin-propert: Right now.

**[00:16:36] m5.t0124** Whitney Hodges: Yeah, yeah, no, I think that that, that totally, um, makes sense. Um, you know, one thing in terms of, like, just attribution data, and depending on, like, how granular you want to get with it, right? So, um, I guess one question that I have. So, on the new, the landing page that you've created, that you know only adds traffic.

**[00:16:37] m5.t0125** Blair Propert: Okay.

**[00:16:55] m5.t0126** Whitney Hodges: is going to. Do you have a form on that landing page that's different than just, like, the form on the website, or are they the same form?

**[00:17:04] m5.t0127** victoriamelvin-propert: It's a different form.

**[00:17:05] m5.t0128** Whitney Hodges: Okay, perfect. Yeah, so then you should know, right, that any, like, lead that's coming through that form has come through an ad, but if you want to get more specific in terms of, okay, well, which ad did they come from, or which campaign did they come from.

**[00:17:19] m5.t0129** Whitney Hodges: Um, that's where UTM parameters could come into play, and so those can be set up in Meta, like, at the ad level, on the ad side of things, but the other layer of it that would have to be in there, and I'm pretty sure that you could do this with HoneyBook, is adding some hidden form fields to your forms.

**[00:17:23] m5.t0130** Blair Propert: Okay.

**[00:17:37] m5.t0131** Whitney Hodges: that are capturing those UTM parameters as well. Does that make sense, or am I kind of speaking a foreign language right now?

**[00:17:43] m5.t0132** victoriamelvin-propert: Yeah, that makes sense.

**[00:17:44] m5.t0133** Whitney Hodges: Yeah. So that would be something to where you're really seeing, okay, this lead saw my awareness ad and inquired through that, or they saw a conversion ad and inquired through that.

### m5_specialization_and_proposal_stage

The prospects directly identified venue specialization and a peer community as reasons WIA seemed more relevant than local alternatives, while the conversation remained at proposal stage.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["audience_insight", "service_value"], "destination": "internal_intelligence", "wia_contribution": "Whitney asked whether they were considering alternatives and explained the proposal, contract, and invoice steps; the prospects supplied the specialization and community rationale.", "attention_reason": "The exchange is useful buyer-value intelligence, but there is no confirmed purchase or permission for public use.", "research_questions": ["Did Victoria and Blair accept the proposal or proceed to contract and payment?"]}

**Qualifications:** ["This is a prospective buyer's stated perception, not an outcome or verified comparison of providers.", "A proposal was to be sent; acceptance and payment are not reported.", "No permission to use the prospect's statement publicly is supplied."]

**[00:30:25] m5.t0229** Whitney Hodges: Yes, yes, and we can definitely help you with that for sure. Are you guys kind of exploring still other options at this point as far as ad support, or do you feel like this is kind of the answer you've been looking for?

**[00:30:41] m5.t0230** victoriamelvin-propert: Um, I was just local people, but I think with you guys and being specialized in venues, it makes way more sense, um, just with the background and the community, too, if everybody's kind of in the same boat, for sure.

**[00:30:51] m5.t0231** Whitney Hodges: Okay, perfect. That sounds good. Well, yeah, so if you're ready to jump in, we would love to be able to, you know, start supporting you, like I said, as soon as you're ready. So next steps from here, I'll send you the proposal that kind of breaks all of this down.

**[00:31:07] m5.t0232** Whitney Hodges: Um, all you really have to do from there is accept the proposal, and then it's gonna, you know, open up a contract and invoice for you, and once those are taken care of, you'll be able to jump right in.

**[00:31:19] m5.t0233** victoriamelvin-propert: Sounds good.

### m6_brand_foundations_and_landing_pages

Whitney and Emily connected foundational brand and website work to the effort of building an ad landing page and to the consistency a couple may encounter across the broader site.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["wia_expertise", "service_value", "broader_principle"], "destination": "public_opportunity", "wia_contribution": "Whitney connected existing brand guidelines and website assets to WIA's landing-page work and added the couple's broader research journey; Emily reinforced the risk of a visual and messaging disconnect.", "attention_reason": "This makes otherwise invisible preparation for ad traffic tangible without claiming that faster page creation caused better results.", "research_questions": []}

**Qualifications:** ["The one-day and multi-month comparisons are Whitney's reported examples, not a controlled comparison or measured performance result.", "No conversion lift or causal effect is established.", "The past client is unnamed, and no publication permission is supplied."]

**[00:53:50] m6.t0337** Whitney Hodges: As opposed to, like, the full-blown website, right? But what is so interesting, or, I mean, maybe it's kind of obvious, right? The creation of those landing pages is so much faster and so much easier when.

**[00:54:05] m6.t0338** Whitney Hodges: the website is already… and the brand are already in amazing spots, right? So, like, to your point, Emily, when there are already brand guidelines that exist that are super clear, super thorough, really do, like, lay out who that ideal client is.

**[00:54:20] m6.t0339** Whitney Hodges: it's just a matter of, honestly, kind of, like, just cherry-picking and, like, copying a lot from the existing website into a long-form landing page that we know is going to convert well for ads. And I feel like one of the best ways for me to convey this, honestly, would be, like.

**[00:54:27] m6.t0340** Emily Foster: Mm-hmm.

**[00:54:37] m6.t0341** Whitney Hodges: In reflecting on some of our accelerator clients and kind of like where they've been at in their their process, right? Because usually one of the the very first things that we do when we welcome people into the accelerators is we give them all of our curriculum on how they can kind of like.

**[00:54:53] m6.t0342** Whitney Hodges: audit their social media, their website, kind of their assets that they have as a whole to make sure that they're ready for ads traffic, and it gives them kind of a breakdown on what's going to make a great landing page for their ads. And we'll see some clients who spend.

**[00:55:10] m6.t0343** Whitney Hodges: honestly, like, a couple of months needing to, like, go through that curriculum to, like, build the landing page. It can be more of, like, a painstaking process for them, versus… I'm thinking of, like, a past client of yours who needed to create an ads traffic landing page.

**[00:55:26] m6.t0344** Whitney Hodges: And she did it in a day, right? Because, like, all of that, like, already existed. So all of that foundational stuff, I mean, it's just so important because everything works together so holistically, right? Because even if an ad is directing people to a landing page and not.

**[00:55:42] m6.t0345** Whitney Hodges: the website, your business is getting more visibility in general. So many of today's couples are analytical buyers just like you are, Emily, that just because the ad didn't necessarily direct them to the full-blown website, they're still going to make their way over to the website through the research process, right? And it's so important that everything really is built for those conversions.

**[00:55:57] m6.t0346** Emily Foster: Okay.

**[00:56:04] m6.t0347** Emily Foster: Yeah, yeah, that's such a good point, because I feel like sometimes, like, if you are doing the heavy work for the landing page, but they haven't done the work for the rest of their website, there's that disconnect, too, where people will be like, well, why does this one page look so different from everything else?

### m6_multiple_audiences_site_structure

Emily distinguished between audiences that may need their own service pages and cultural or stylistic distinctions that may be better conveyed through relevant messaging and imagery; Whitney connected that distinction to ad landing pages and campaigns.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["audience_insight", "wia_expertise", "broader_principle"], "destination": "public_opportunity", "wia_contribution": "Whitney posed the attendee's multi-audience problem, connected distinct sectors to landing pages and campaign structure, and asked how blog strategy fits; Emily supplied the website and audience-journey reasoning.", "attention_reason": "The conversation avoids a one-size-fits-all rule and shows how buyer clarity can shape both site organization and advertising.", "research_questions": []}

**Qualifications:** ["The advice is a response to one attendee's scenario and does not establish a universal page structure.", "No implementation or resulting inquiry behavior is reported."]

**[00:56:21] m6.t0351** Whitney Hodges: So Mona had a really good question. She said, any suggestions on strategy when trying to attract different audiences? She says, we plan weddings as well as corporate, nonprofit, government, and other social events. And even within the wedding part of our business, we also plan Indian and South Asian, which would be different than like just a more.

**[00:56:30] m6.t0352** Emily Foster: Mm-hmm.

**[00:56:42] m6.t0353** Whitney Hodges: Traditional.

**[00:56:42] m6.t0354** Emily Foster: Yeah. Yeah, I think that's where it is really important to get clear about, like, your page strategy, which I didn't really talk a ton about, like, UX and, like, the overall, like, sitemap strategy for your website, but we have a lot of clients that do have, like, different focuses like that. Like, they might have different audiences within the wedding industry, or they do, like, like, social and corporate and nonprofit and weddings.

**[00:57:07] m6.t0355** Emily Foster: So I would say, like, having a dedicated page for most audiences is going to be preferable. But it is kind of knowing, like, I wouldn't necessarily say that you need, like, a separate page for, like, South Asian weddings. Like, in that case, like, you would want to just make sure that you're clear with your messaging and your images that you are capable of doing those larger weddings and, like, speaking to the pain points of those kinds of clients somewhere. But it's, like, not as literal as, like, in your navigation having, like.

**[00:57:35] m6.t0356** Emily Foster: Um, like a weddings tab and then it drops down and it's like South Asian weddings and like, like, I don't know, stereotypical weddings or something like that. Um, so you want to get kind of strategic about the messaging, but then also like in your site map that makes sure that you have like different services, um, indicated, especially when it is like those totally different worlds of like corporate versus weddings.

**[00:57:56] m6.t0357** Emily Foster: Um, and then in your SEO strategy, think about that as well, like, doing keyword research for each audience. Um, and then I would, like, this is kind of more of a basic kind of answer after all of that, like, all of that is a lot more complex than it sounds, like, it does take more time and thought of, like, thinking through, like, okay, should we have this page or this page, and, like.

**[00:58:15] m6.t0358** Emily Foster: having that kind of conversation about what's most important. But then, once you do that work of creating everything, like, looking at it through the lens of each of your ideal clients, and thinking about, like, okay, if I was a corporate client, and I landed on this website, how quickly can I find the information that I need? Or…

**[00:58:32] m6.t0359** Emily Foster: If I am an Indian couple and I'm like looking to find the right wedding planner, like how quickly do I see myself in the messaging and like what's my next call to action and kind of go through that client journey on your website to make sure that you're speaking to all of those clients.

**[00:58:48] m6.t0360** Emily Foster: Um, and the other thing, like, is you might need to create separate brands if it is distinct enough, like, um, that is a possibility sometimes. We don't always have clients do that, but I do have clients who have created, like, different websites for two different audiences, which is kind of, like.

**[00:59:05] m6.t0361** Emily Foster: the most extreme side. I think that gets the most heavy lifting.

**[00:59:09] m6.t0362** Whitney Hodges: Yeah, we oftentimes will see different landing pages for these, like, different kind of sectors, different types of events, and then that is where your ad strategy can get more layered as well, right? Like, Google ad campaigns specific for your corporate events, specific for your holiday parties, specific for your…

**[00:59:21] m6.t0363** Emily Foster: Hi.

**[00:59:27] m6.t0364** Whitney Hodges: your weddings.

**[00:59:28] m6.t0365** Emily Foster: Yeah.

**[00:59:30] m6.t0366** Whitney Hodges: Does a blogging strategy kind of play into that as well at all, Emily? Like, blog posts that are, like, dedicated to those different types of events?

**[00:59:37] m6.t0367** Emily Foster: Yeah, definitely, like, I even have a client who has two, like, it's one blog, like, they have a Showit website, and then a blog that runs through it, um, and we designed her blog pages, this is another reason I love, like, we didn't talk about platforms today, but I love Showit, because you can't really do this in platforms like Wix, or Squarespace, or WordPress as easily, but.

**[00:59:57] m6.t0368** Emily Foster: We have the blog page designed so that when she has couples and then she also has high school seniors as her ideal clients. So when a senior goes to the blog, they're going to only see content relevant to them. And then if a couple goes to the blog, they're only going to see wedding and engagement kind of content. So it does go with your SEO strategy with the keywords that you're finding. You would want to find keywords that are great for blog topics for each audience. And then you can lay out the blogs in a way.

**[01:00:26] m6.t0369** Emily Foster: that are really easy for each of those clients to digest.

### m6_brand_design_collaboration_process

Emily described a staged brand-design process in which client preference and strategic fit are both checked before visual work proceeds, with revisions treated as normal collaboration.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["service_value", "broader_principle", "wia_expertise"], "destination": "public_opportunity", "wia_contribution": "Whitney asked about the strategy-to-design bridge from the perspective of an ad strategist who receives existing guidelines; Emily explained her studio's process and client feedback checks.", "attention_reason": "This demonstrates how client input can be structured around both personal fit and audience strategy, without implying that revision is a process failure.", "research_questions": []}

**Qualifications:** ["The process is Emily's description of her studio's work, not a WIA-delivered branding service.", "The 25 to 30 percent revision estimate is Emily's reported figure; no underlying data is supplied.", "No client-specific outcome or publication permission is supplied."]

**[01:00:43] m6.t0372** Whitney Hodges: I think the one thing that I would be interested to hear more about from you, Emily, is just kind of the methodology of like the bridge of what happens between the strategy and then getting to the actual like.

**[01:01:00] m6.t0373** Whitney Hodges: design of the brand. Because for us as ad strategists, right, people are coming to us typically with, like, the brand guidelines are already done. We're just following the brand guidelines sort of thing, so we don't do quite that piece of it. Um, but I'm interested to hear, like, your process, right, of how, like, okay, if this is the strategy.

**[01:01:07] m6.t0374** Emily Foster: Mm-hmm.

**[01:01:18] m6.t0375** Whitney Hodges: How do we end up with this is what the brand looks like?

**[01:01:21] m6.t0376** Emily Foster: Yeah, yeah, so we do a call initially with clients, like, we'll go on a strategy call, and then, like, internally, our team takes the strategy notes and starts working on a mood board for clients, and our mood boards are, like, way more extensive than, like, I feel like, you know, you might see, like, a planner's mood board, and it's, like, one page kind of thing that shows the vibe, and some designers do it that way too, but usually ours are, like, anywhere from, like, three to seven plus pages.

**[01:01:46] m6.t0377** Emily Foster: So there's, like, a page that talks about the messaging, if we're writing their copy, and there's, like, a page that talks about, um, the overall design decisions that we want to make for the brand, and then the website style. Uh, so we pick, like, their color palette, um, based in the strategy, and that, like, goes, um, like, we factor in color psychology, and…

**[01:02:04] m6.t0378** Emily Foster: Like we do take a look at like the market and like how we can make people stand out compared to their competitors. So the mood board is like such a huge part of it. And then we send that over to the client for feedback. And I always tell people like to do a gut check of like, do you like this? But then also do you think it works for your ideal clients? And we have like feedback forms throughout each step of the process that like asks you those intentional questions to be like.

**[01:02:28] m6.t0379** Emily Foster: Um, like, do you like it? Do you approve it? But then also, do you think this works for your strategy and your ideal clients? And, like, kind of doing that check each time? Um, because even if it works for your strategy and your ideal client, I don't want people to end up with, like, a brand or website that they hate and that they can't stand. So there is kind of that happy medium.

**[01:02:45] m6.t0380** Emily Foster: So the mood board and kind of like stylistic selection process is such a huge part. And that's before we've even like opened Adobe to design logos. And then once we get on the same page about the mood board, from there we put together a brand presentation. So that includes like logo designs, patterns, typography selection.

**[01:03:03] m6.t0381** Emily Foster: Uh, and, like, icons, so that's, like, where we are taking the hours to, like, design everything and bring it together, and then we present that to the client and show them, like, their logos in every kind of different color that we could have, like, um, we'll show them, like, the patterns and the icons and lay it all out in a cohesive presentation, and then we go through the same kind of feedback.

**[01:03:23] m6.t0382** Emily Foster: process of, like, um, do you like this? Does this work for your strategy? Like, are there any edits that you want to see? And then we go through revisions. Um, revisions, I feel like, are a nice thing to talk about, too, because, um, people sometimes are weary to give revisions. Like, I think they're kind of like, oh, I don't want to hurt your feelings, or something like that, but.

**[01:03:42] m6.t0383** Emily Foster: Um, it's such a normal part of the process, and I would say we probably have about, like, 25 to 30% of our clients, like, give, like, semi-extensive revisions as well, and we do have, like, a lot of clients just approve things right away, but that revision and kind of collaboration process is such a…

**[01:03:59] m6.t0384** Emily Foster: important part of the process. Um, so we go through that, and then we export the logos, put together brand guidelines, and then from there, we start designing the website, and we'll design the homepage to start, and run that by with the same feedback process, and then go through the rest of the page designs, and.

**[01:04:16] m6.t0385** Emily Foster: Present the website as a whole, and make sure that we do, like, the final checks, like, tech checks and everything, make sure there's no broken links, and then we go into launch from there.

### m6_rebrand_lifespan_conditions

Emily's estimate of brand longevity was conditional on continuity in the business name, target clients, and market tier; a meaningful repositioning could justify a refresh.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["broader_principle", "audience_insight"], "destination": "public_opportunity", "wia_contribution": "Whitney raised the recurring-rebrand question and asked what conditions affect brand longevity; the estimate and repositioning distinctions are Emily's.", "attention_reason": "The exchange may help examine when a visual refresh responds to a real positioning change, while keeping the lifespan estimate attributed and bounded.", "research_questions": []}

**Qualifications:** ["The 10-to-20-plus-year figure is Emily's professional estimate, not a measured industry lifespan or guarantee.", "The exchange does not assess any particular business's brand or establish whether a refresh is needed."]

**[01:04:26] m6.t0386** Whitney Hodges: Love it. Okay, makes sense. So, one thing that came to mind for me is sometimes I feel like we'll see…

**[01:04:34] m6.t0387** Whitney Hodges: Certain wedding pros going through rebrands.

**[01:04:38] m6.t0388** Whitney Hodges: I don't know, like, every few years or so, almost, like, thinking that the branding is, like, the issue, and so, like, oh, I need to, like, rebrand sort of thing. But what would you say, like, when you're really doing the branding right, and, like, addressing the foundational pieces of it, like.

**[01:04:41] m6.t0389** Emily Foster: No.

**[01:04:47] m6.t0390** Emily Foster: Yeah.

**[01:04:54] m6.t0391** Whitney Hodges: I would think that that is going to serve you for a really long time, right? Like, do you know if… I mean, is there, like, a shelf life that you would say of, like, when your branding is really done right, like, it's going to work for you forever, sort of thing? Or is it, like, 10 years, or…

**[01:05:08] m6.t0392** Emily Foster: Uh, yeah. Yeah, I would think like at least 10 to 20 years and like the caveat being like a big brand strategy overhaul, like if you are starting to attract a different niche, um, like Mona's question earlier was a great example. Like if you are like a planner and you, maybe you used to work tons of like South Asian weddings and then.

**[01:05:10] m6.t0393** Whitney Hodges: What would you say?

**[01:05:32] m6.t0394** Emily Foster: you kind of get to a point in your business where you're like, I never want to take another wedding like that again, like, I only want to do elopements, and that would be, like, brand repositioning that probably does require some kind of… at least a brand refresh, and we can talk about, like, the difference, kind of, between a rebrand and brand refresh, but…

**[01:05:39] m6.t0395** Whitney Hodges: Great.

**[01:05:47] m6.t0396** Whitney Hodges: Mm-hmm.

**[01:05:47] m6.t0397** Emily Foster: Um, as long as, like, the name of your business is still working for you, and you're still, like, speaking to the same clients, and you're still kind of in, like, the same tier of market, your brand should work for you for, like, 10 to 20 plus years. Um, and that's, like, I always like talking about the big corporate brands, because you've seen, like, um, like, Coca-Cola or, like, Starbucks logos change a little bit over time, but, like.

**[01:06:03] m6.t0398** Whitney Hodges: Mm-hmm.

**[01:06:08] m6.t0399** Emily Foster: If you Google their brand from the 80s, it still looks pretty similar and still has a similar vibe. You can modernize things a little bit, but ideally, you're not having to modernize that much in that short of a time frame because you're not relying on trends.

### m6_adjacent_search_intent

The exchange distinguished truthful promotion of an existing service in the context of adjacent wedding interests from implying that the business sells services it does not offer.

**Individual parser check (diagnostic only):** failed

**Provisional discovery:** {"lenses": ["audience_insight", "wia_expertise", "broader_principle"], "destination": "public_opportunity", "wia_contribution": "Whitney connected the attendee's question to awareness-stage advertising and the need to nurture less-qualified prospects; Emily supplied the content and positioning recommendations and refined them after the attendee clarified the offer.", "attention_reason": "The exchange contains a meaningful truthfulness trade-off, a revision based on client knowledge, and a distinction between cold interest and inquiry-ready demand.", "research_questions": []}

**Qualifications:** ["The examples and recommendations respond to one attendee's ice-sculpture business and market; they are not validated as effective in other markets.", "Blogging, keyword research, partnerships, complementary imagery, and nurturing were suggestions, not reported implementations or results.", "The conversation distinguishes an ad that falsely claims an adjacent service is available from imagery that presents it as a complement to the offered service; it does not establish legal advice."]

**[01:06:42] m6.t0403** stlic: Yeah, we're kind of in a few different markets, like Austin, San Antonio are the primary market here, and then we just opened a shop in St. Louis, and we're, uh, expanding into Kansas City a little bit.

**[01:06:56] m6.t0404** stlic: But I struggle with like my ad spend because if people are searching for ice sculptures, I'm already at the top in most of the markets just naturally. But it's like, how do I branch out to end, you know, trends like last year was espresso martinis, this year is champagne towers.

**[01:07:04] m6.t0405** Emily Foster: You are.

**[01:07:17] m6.t0406** stlic: marquee lighting has become popular the last couple years. It's kind of adjacent, where, like, if people want marquee lights, that might be a client who might.

**[01:07:28] m6.t0407** stlic: one ice sculpture, two. And so, like, I don't want to spend on Google Ads for people who are already searching ice sculptures, because there's not a ton.

**[01:07:38] m6.t0408** stlic: of competition, and I'm already showing up. But how do we expand that reach to people who don't know what they don't know, or are like, oh, I want a champagne tower at my wedding, because that's in…

**[01:07:53] m6.t0409** stlic: And then it's like, oh, well, you know, the espresso martini was so in last year.

**[01:07:58] m6.t0410** Emily Foster: Yeah, I…

**[01:07:58] m6.t0411** stlic: where did all those brides just move to the Champagne Tower this year? And so, that's kind of where I'm struggling at, is like, am I really getting the bang for my buck on this Google AdWords?

**[01:08:02] m6.t0412** Emily Foster: Okay.

**[01:08:09] m6.t0413** stlic: Um, I don't really have an e-comm kind of product, so, like, the meta ads aren't really ideal either, because I just need so much information. So, how do I get to those clients, or what's the strategy about, hey, if you're searching for.

**[01:08:26] m6.t0414** stlic: Beer Borough Company, you might also be interested in there or like, you know, any kind of like niche kind of off.

**[01:08:36] m6.t0415** stlic: adjacent, you know, kind of companies.

**[01:08:39] m6.t0416** Emily Foster: Yeah, totally. And, um, just to be clear, like, you don't necessarily do marquee lights or, like, champagne…

**[01:08:44] m6.t0417** stlic: We don't do that at all, no. I just… it's like, the mentality of that customer is like, hey, we wanna spice up our wedding, or our event, and…

**[01:08:45] m6.t0418** Emily Foster: Yeah, it just pairs well.

**[01:08:49] m6.t0419** Emily Foster: Yeah, I…

**[01:08:55] m6.t0420** stlic: we're gonna get flowers for sure, but, like, do all the table centerpieces need to be flowers? How do we get the… some ice in there? Or… I'm not trying to, like, undercut anybody else's business, or downplay their stuff, but…

**[01:09:09] m6.t0421** Emily Foster: Yeah. Okay.

**[01:09:11] m6.t0422** stlic: I do want to try and compete a little bit on those things that are…

**[01:09:14] m6.t0423** Emily Foster: One.

**[01:09:16] m6.t0424** stlic: ancillary to, like, what do you need for a wedding, you know?

**[01:09:20] m6.t0425** Emily Foster: Yeah. Yeah, that makes sense. First, that's such a cool business. I love that you do ice sculptures. And also, I feel like that's such a great problem to have, Whitney, of you're already at the top for ice sculptures. So I think it's great to think about this expansion.

**[01:09:35] m6.t0426** Emily Foster: Um, there's, like, a lot of ways that you could go about it, so I think that the blogging strategy could be really useful here, or, like, frequently asked questions, so getting some organic content on your website that does mention keywords like marquee lights or champagne towers and things like that.

**[01:09:51] m6.t0427** Emily Foster: I say that with organic, because I feel like I'd want like Whitney or Daniela to say like I like. I am cautious about you running ads specifically to a page that is ranking for marquee lights, because I'm worried about that getting into like false advertising. But it is okay. If it's more like organic content, like, if you were to write a blog post that's like.

**[01:10:14] m6.t0428** Emily Foster: how to amplify your marquee lights experience or something. And then in the blog post, you're mentioning, like, 10 kinds of ice sculptures. That would be really cool to complement with that. So it's not like you're advertising and selling marquee lights, but you're, like, selling the experience that goes along with it.

**[01:10:29] m6.t0429** Emily Foster: Um, but, like, we wouldn't want you ranking to say, like, marquee lights available, and then people click on an ad and get there, and then they're not there, because I feel like that could just get into, like, mostly legal issues in the future, um, or if anything, like, frustrated clients.

**[01:10:45] m6.t0430** Emily Foster: Um, so I think adjacent content that can work well, like doing some keyword research about those kinds of topics, um, and seeing, like, if they even rank well in your area, kind of thing, like, if it's worth the squeeze, um, to kind of, like, have those blog posts.

**[01:11:01] m6.t0431** Emily Foster: And then having tons of call to actions in the blog post that links out to your services or your options for purchasing the ice sculpture experiences. And then you could run ads to those blogs. That could be a strategy if you're already kind of maxing out what you're doing with landing pages around ice sculptures. You could run ads to blog posts that have that kind of supplemental content.

**[01:11:24] m6.t0432** Emily Foster: Um, and, like, have examples of how you work together with that. And then, just, like, another tip, kind of outside the whole, like, digital advertising or, like, digital online space, like, I think that you could also start collaborating with those companies if they don't already offer ice sculptures, but, like.

**[01:11:42] m6.t0433** Emily Foster: Think about the kind of strategic partnerships you could create and you could bring that over to your website strategy of basically having relationships with them where maybe you write a blog post for their website and they write one for yours and you give back links to each other to feature each other's services.

**[01:11:59] m6.t0434** Emily Foster: Um, or consider, like, creating a referral program with them, like, maybe you have, like, a special offer that you give to a local marquee light company if one of their clients books an ice sculpture.

**[01:12:10] m6.t0435** Emily Foster: Um, and then this isn't always, like, I feel like the best answer for everyone, because it does depend on, like, your overhead and, like, your interest in it, but you could also consider, like, getting those adjacent services under your umbrella if you don't want to kind of invest the time in the strategic partnerships, but.

**[01:12:25] m6.t0436** Emily Foster: Start offering marquee lights or champagne towers, and then you could obviously do the keyword research and start ranking content for those.

**[01:12:34] m6.t0437** stlic: Yeah, I want to be cautious of, like you said, I'm not trying to sell marquee lights or add a different business to my business, but…

**[01:12:34] m6.t0438** Emily Foster: Does that help?

**[01:12:40] m6.t0439** Emily Foster: Why?

**[01:12:44] m6.t0440** stlic: just identifying the trends and staying current with, like you said, probably the blog post kind of situation is probably gonna be my best bet there. yeah, it's just like I know people are searching for things. If they're searching for my things, we do have a pretty good closing rate on our like. If someone fills out a form to your point earlier.

**[01:12:48] m6.t0441** Emily Foster: Yeah, right.

**[01:13:06] m6.t0442** stlic: we're getting more qualified leads is, you know, and that's the thing, like, oh, when we did Meta stuff, we'd get a ton of leads, but they were all ghosts. And how much time do you spend on tracking that down versus, like, no, you have to fill out this lengthy form.

**[01:13:16] m6.t0443** Emily Foster: Hmm.

**[01:13:23] m6.t0444** stlic: and now we know you have an event, and a day, and a location, and all that. But, like, if you're not already searching for that, how do we get into that, um, that mindset, or that mind…

**[01:13:35] m6.t0445** stlic: place for those people who aren't searching for.

**[01:13:39] m6.t0446** stlic: you know, and is it luxury weddings? Is it, you know, uh… I'm not sure what the… the key terms, or how to… how to navigate that, so…

**[01:13:50] m6.t0447** Emily Foster: Yeah, and it's not going to be the same for every market, um, but yeah, I would say, like, getting into the head of their pain points and finding keywords related to that in your area. So maybe it is, like, wedding decor in San Antonio, or, like, Austin, um, wedding reception ideas, and, like.

**[01:14:08] m6.t0448** Emily Foster: having blog content about those, um, will be really good, and then having clear call-to-actions throughout your website that link to frequently asked questions. And in your frequently asked questions, you could have mentions of, like… like, it could be, like, um…

**[01:14:23] m6.t0449** Emily Foster: if we purchase an ice sculpture, like, what other decor should we consider investing in? And then maybe mention, like, you may also want to consider marquee lights or champagne towers, like, inquire with us, and we're happy to give you referrals for these, or, like, something like that.

**[01:14:38] m6.t0450** Emily Foster: So it kind of organically gets those keywords on your site without you having like a dedicated page for a service that's not yours. But definitely thinking about like the pain points, like you basically just said that, but then doing the keyword research there and you could use tools like Moz or Ubersuggest.

**[01:14:55] m6.t0451** Emily Foster: Um, that's a good way to start SEO keyword research. And then also, I'm sure that there's tools in the vault, too, about, like, if you're going through the Meta Ads Accelerator, like, finding the right keywords for your ads campaigns related to those.

**[01:15:08] m6.t0452** stlic: Cool. Thank you.

**[01:15:10] m6.t0453** Emily Foster: Yeah, yeah, of course. Feel free to reach out with any other questions related to that. That's a great question. I love, like, when it's.

**[01:15:13] m6.t0454** Whitney Hodges: That's great.

**[01:15:16] m6.t0455** Whitney Hodges: Yeah, I think that was really good advice, Emily, and I'm not sure on your end, like, on the more organic side, how much you see Pinterest playing into the blogging strategy as well, like, if it makes sense that he's gonna, like, be kind of, like, creating blog posts that are dedicated to these, like, wedding decor trends.

**[01:15:25] m6.t0456** Emily Foster: Yeah, here.

**[01:15:32] m6.t0457** Whitney Hodges: To then create some pins that align with that as well, and maybe…

**[01:15:36] m6.t0458** Emily Foster: Yeah, I think put it everywhere. Yeah, Pinterest is a great way. And then like, that's another great place. I might have mentioned this when we were talking about blog strategy, but having tons of pictures of ice sculptures with these kind of adjacent services, like even if it is like you had a wedding and, you know, a marquee light company has their lights in the background, that's okay to use a picture like that.

**[01:15:37] m6.t0459** Whitney Hodges: just…

**[01:15:56] m6.t0460** Emily Foster: Um, but then having the pins do that, and then you can also continue sharing, like, on your stories, and create organic content, like, through Instagram and TikTok and Facebook, and, um, basically, like, promote it that way. And I also, I don't think that you're getting into dangerous territory of, like, false advertising if you have an ad.

**[01:16:13] m6.t0461** Emily Foster: like, where all of the messaging is focused on ice sculptures, but then you kind of… like, let's say you have, like, a reception table, and there's, like, an ice sculpture, and then a champagne tower next to it. Like, it's not like you're selling the champagne tower, but the overall image of that.

**[01:16:28] m6.t0462** Emily Foster: ad would give people the idea that, like, okay, this is going to go well with these other trends that I'm interested in.

**[01:16:31] m6.t0463** Whitney Hodges: Okay, just a minute.

**[01:16:34] m6.t0464** stlic: Yeah, or just like, oh, you're considering marquee lights, also maybe consider an ice sculpture to make the impact you're looking for, where it's like…

**[01:16:45] m6.t0465** Emily Foster: Yeah, I…

**[01:16:48] m6.t0466** stlic: If they're searching for a marquee light, you know.

**[01:16:52] m6.t0467** stlic: it's like, we don't do that, but you can consider this. I mean, I don't think it's, like, ethically wrong or unclear that I also sell marquee lights, but it's just, like, a way for… in my mind, if people are searching for… and I'm…

**[01:16:56] m6.t0468** Emily Foster: Yeah, I…

**[01:16:59] m6.t0469** Emily Foster: No.

**[01:17:08] m6.t0470** stlic: not trying to pick on marquee lighting, it's just something that I've noticed. So, anything like that, like, are you considering XYZ?

**[01:17:13] m6.t0471** Emily Foster: Yeah.

**[01:17:18] m6.t0472** stlic: you know, maybe consider ICE as well, or have you thought about this instead, or something?

**[01:17:21] m6.t0473** Emily Foster: Yeah, I…

**[01:17:24] m6.t0474** Emily Foster: Yeah, I feel like a great way to think about it, like, a good analogy for this is, like, the way that Oreos basically uses milk to sell their product, but it's, like, just thinking, like, in your ads creative about, like, how can you make, like, the marquee lights or the champagne tower, like, the milk in the background kind of experience of, like, oh, if you're going to have this thing anyway.

**[01:17:43] m6.t0475** Emily Foster: then you can also buy this other thing that pairs really well with it. So kind of, like, that complimentary advertising.

**[01:17:51] m6.t0476** Whitney Hodges: Yeah. Yeah. Kristi mentioned things that are IG-worthy, eye sculptures, lighting, eye-catching things. So, I mean, there definitely is an area of opportunity with the meta ads. It's just that, you know, that strategy does have to be a little bit more in-depth than, like.

**[01:17:54] m6.t0477** Emily Foster: Bye-bye.

**[01:17:58] m6.t0478** Emily Foster: Yeah.

**[01:18:02] m6.t0479** Emily Foster: Okay.

**[01:18:07] m6.t0480** Whitney Hodges: somebody who's coming in cold just thinking about an ice sculpture for the first time, they're not gonna be ready to send out fill out that form of your Sean that somebody who's, like, super qualified, like, ready to go would be. Right? So there would have to be those touch points in between of the email marketing or text message marketing, things that are really nurturing them and and kind of.

**[01:18:29] m6.t0481** Whitney Hodges: warming them up to take them from that awareness stage to actually becoming a lead.

**[01:18:35] m6.t0482** Emily Foster: Yeah, yeah, and that blog and Pinterest content is a great way to, like, warm up too, like, because you can always, like, have that kind of part of your, like, inquiry or sales funnel too.

### m6_followup_capacity_and_nurture

In response to concerns about low-readiness leads, labor, and spammy automation, Whitney recommended useful, sustained nurture rather than repeated generic check-ins, while making duration dependent on the event and buying timeline.

**Individual parser check (diagnostic only):** passed

**Provisional discovery:** {"lenses": ["audience_insight", "wia_expertise", "broader_principle"], "destination": "public_opportunity", "wia_contribution": "Whitney tied nurture duration to event timing and the likely buying window, and recommended useful marketing content rather than repeated generic check-ins.", "attention_reason": "This exchange could illuminate the tension between human follow-up capacity and keeping early-stage prospects engaged without presenting automation as a substitute for judgment.", "research_questions": ["What cadence and stopping criteria did Whitney have in mind for the proposed initial sequence and longer follow-up period?"]}

**Qualifications:** ["The approximately 30-day initial sequence and possible six-month follow-up were recommendations in a workshop, not a universal cadence or tested outcome.", "The attendee's lead volume, lead quality, and admin burden are his reported experience.", "The exact message frequency, stopping rule, and any resulting booking outcome are not provided."]

**[01:18:45] m6.t0485** stlic: Yeah, and Whitney, I know you guys are great about automating, uh, responses and stuff, but, like, that's part of my question, like, I kind of have a philosophy, like.

**[01:18:56] m6.t0486** stlic: either keep bugging them until they tell me no, or until the date passes that I can execute the event? Um… but also, like, how much time or dedication do you give to just these, like.

**[01:18:59] m6.t0487** Whitney Hodges: Mm-hmm.

**[01:19:02] m6.t0488** Whitney Hodges: Mm-hmm.

**[01:19:09] m6.t0489** stlic: Oh, yeah, that might be neat. I get married in 18 months, like, you know, you have to bring them along and kind of keep, uh, uh, nurturing the idea, but…

**[01:19:11] m6.t0490** Whitney Hodges: Mm-hmm.

**[01:19:16] m6.t0491** Whitney Hodges: Mm-hmm.

**[01:19:23] m6.t0492** stlic: you know, that was a problem that we faced was, like, the admins were spending so much time sending follow-up emails, and, like, uh…

**[01:19:33] m6.t0493** stlic: Automating felt kind of spammy, and was hard to track responses to, and so we felt like…

**[01:19:40] m6.t0494** stlic: Man, we're getting hundreds of leads, these warm leads of people that think, Oh, that looks cool, I'm interested. And now we got their name in their email. But now it's like they don't have an event, they don't have a date, they don't have nothing. And we're spending so much time and energy.

**[01:19:57] m6.t0495** stlic: Trying to keep, hey, you know, let us know. Let us know. Hey, how can we help? Did you know this? Did you know that? And it felt like Man, we're just throwing our resources away right now Because these folks don't have an event or date or.

**[01:20:13] m6.t0496** Emily Foster: Mm-hmm.

**[01:20:13] m6.t0497** stlic: any of this. So, what's… do you guys have, like, a…

**[01:20:17] m6.t0498** Emily Foster: you…

**[01:20:17] m6.t0499** stlic: Rule of thumb on that, like, yeah, you should send once a week, or once a month.

**[01:20:23] m6.t0500** stlic: just keep sending them your normal blog email from the MailChimp campaign, and uh… hope for the best, or what… or when do you draw the line at?

**[01:20:33] m6.t0501** stlic: No, just let that one go because it's taking up too much time.

**[01:20:40] m6.t0502** Whitney Hodges: Yeah, so from like an inquiry standpoint, when inquiries are coming in from ads, usually like the initial nurture sequence can be 30-ish days is kind of what we're seeing as a kind of best practice.

**[01:20:56] m6.t0503** Whitney Hodges: At this point, but then, I mean, continued follow-ups, like.

**[01:21:01] m6.t0504** Whitney Hodges: potentially for, like, the next 6 months or so, you know what I mean? Like, somebody who's planning a wedding, right? And depending on if the wedding is actually booked yet, and how far the date is in the future, and, like, just adding on an ice sculpture, that could be an impulse purchase that they could add, I would think.

**[01:21:17] m6.t0505** Whitney Hodges: pretty close up to the date of the wedding. Um, I do agree that it's way too heavy of a lift to, like, be having your admins manually just, like.

**[01:21:27] m6.t0506** Whitney Hodges: touching these people over and over again. And oftentimes, also, what we see is that, like, the just checking in, or how are you doing sort of emails don't necessarily, like, get you anywhere, as opposed to, like, a nurture marketing email that's providing more value, that's educating them, that's showing them beautiful pictures, that's maybe linking to blog posts that have been created.

**[01:21:46] m6.t0507** Whitney Hodges: Um, sort of thing. So, I, yeah, I definitely think the key in kind of mastering a meta ad strategy would be that the email marketing component of it is already kind of put together, that's being done pretty consistently, and in addition to those, like, sequences that, um, people are being pulled into.

**[01:22:05] m6.t0508** Whitney Hodges: Um, that from there, you know, there is probably at least just a general monthly email that's going out to your full email list, which it sounds like you're kind of already doing already.
