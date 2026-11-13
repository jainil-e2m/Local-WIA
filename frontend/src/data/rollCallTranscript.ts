/* ────────────────────────────────────────────────────────────────
   The demo office-hours transcript, in its own module so it is code-split and
   the ~30KB never reaches the main bundle.

   WHAT THIS IS. The genuine Google Ads office hours of 12 February 2026,
   hosted by Carmen Cruickshank, pulled from the Fathom share link Gisselle
   provided. Unlike the internal-meeting card's fixture this is a REAL client
   session with REAL members in it, which is what makes the attendance
   derivation checkable rather than illustrative.

   WHY THIS SESSION MATTERS TO THE DESIGN. Three members turn up across
   48 minutes, one after another rather than together — Jillian leaves at 9:19,
   Carmen says "Hey, Erin." at 9:22, and Michael & Diana arrive at 35:00. At
   that volume, everyone who attends speaks, so speaker-derived attendance
   holds. It would NOT hold at six attendees, because Whitney described the
   format as an open drop-in (26 Aug @12:00) where a member can join, listen
   and leave without saying a word — and that member is exactly the one the
   2-week flag exists to catch. The card therefore treats every derived absence
   as a flag for a human, never as an action.

   THREE THINGS IN HERE THE CARD HAS TO HANDLE HONESTLY:
     · "Jillian" has no surname, and two members join under that name.
     · "Michael & Diana" is one label covering two humans on one membership.
     · Michael & Diana are enrolled in the META channel, not Google — so their
       presence here is a cross-track signal, not a plain attendance mark.
   ──────────────────────────────────────────────────────────────── */

export const DEMO_SESSION_META = {
  title: "Google Ads Office Hours  - 2.12.26",
  host: "Carmen Cruickshank",
  date: "2026-02-12",
  sourceLabel: "Google Ads office hours, 12 Feb 2026 (Fathom)",
} as const;

export const DEMO_TRANSCRIPT = `Google Ads Office Hours  - 2.12.26 - February 12
VIEW RECORDING - 48 mins (No highlights):

---

0:00 - Carmen Cruickshank (weddingindustryads.com)
  Hi, Jillian. This meeting is being recorded. Can you hear me?

0:33 - Jillian
  I can. Can you hear me?

0:38 - Carmen Cruickshank (weddingindustryads.com)
  I can hear you. It's like echoing.

0:41 - Jillian
  I just noticed.

0:43 - Carmen Cruickshank (weddingindustryads.com)
  Maybe because I think there's two of you in here. This sounds good. Okay, perfect.

2:01 - Jillian
  I have Square, and I just called them yesterday, and they do not have the option to, like, integrate the thank you page.  So, like, there's not an option to, like, redirect them back to my website for a thank you page, so now what do I do?

2:21 - Carmen Cruickshank (weddingindustryads.com)
  Okay. There are several options. Now, I can't guarantee the conversion tracking. So, basically, I always try to say thank you page, because that's easiest if Google can see that, but a lot of times I can use code.  So, for example, if when someone submits, it says thank you, we'll get back to you soon. Normally, they're not attached to that, so I'll just take the code there, put it into Google Tag Manager, all the complex stuff, and I'd say 75% of the time that works.  Okay. Yeah, so that should work, and then if on the VIP day I tell you, like, I tried all different angles, then we'll just do a second best option, which is...  It's contact page view. So just people that view the contact page or people that click, we could try to do button clicks too on people submitting the form.  So there's different options, but of course, accurate ways to thank you page, but we can probably get that figured out.

3:14 - Jillian
  Okay. Okay. I guess we'll have to try that then. Because like I said, I called them yesterday and they said that that was not an option.  Is it? So like for myself, sorry, my dogs are in the background.

3:33 - Carmen Cruickshank (weddingindustryads.com)
  Okay.

3:34 - Jillian
  She's good. For myself, like I'm a licensed esthetician. So I have Square. I use Square. Is it common? Like, so on my website, if you go to book, it'll take you to the Square website, I guess you could say for booking.  like, do people have their own? Like, I don't know. I know that Glass Genius is also really popular in this industry, but I mean.  I'm finding that where maybe isn't because maybe not what I need but I also don't know what like what other options are.

4:16 - Carmen Cruickshank (weddingindustryads.com)
  Like booking systems you mean for appointments?

4:19 - Jillian
  Sorry say that again.

4:21 - Carmen Cruickshank (weddingindustryads.com)
  You're okay you mean like booking systems for appointments?

4:23 - Jillian
  Yes.

4:24 - Carmen Cruickshank (weddingindustryads.com)
  Okay have you uh I think you're friends with Diana correct with I think she uses Mangomint have you tried that or no?

4:32 - Jillian
  I've never even heard of that.

4:34 - Carmen Cruickshank (weddingindustryads.com)
  Okay yeah definitely ask her about it because she switched from one to another um and so yeah she uses Mangomint now and then she actually when people submit they're redirected to a thank you page so that could work out too.  Oh okay. did it yeah.

4:49 - Jillian
  Did you guys suggest Mangomint?

4:51 - Carmen Cruickshank (weddingindustryads.com)
  No we didn't uh there's probably some options that Whitney might suggest but from her like Mangomint it's also very pretty very clear  Clean. And then you can redirect to the thank you page.

5:02 - Jillian
  So yeah, I like clean.

5:06 - Jillian
  Okay. Okay. So it sounds like your landing page is similar to your homepage, but it's not your homepage.

5:18 - Carmen Cruickshank (weddingindustryads.com)
  Exactly. Cause a homepage, for example, like, like your home, you know, it has the menu like, oh, check out this room, this room, this room.  And then landing page is like, you don't want people to have another option, but submit a lead form to you.

5:30 - Jillian
  If that makes sense. Yes.

5:31 - Carmen Cruickshank (weddingindustryads.com)
  You know, so you want to have it, have all the elements that really like subconsciously pushes people to contact you.  Yeah. So I definitely recommend having both. I think that's kind of nice. Cause then some people, they don't want to contact at that moment and they just want to know more about you.  So they'll research you organically and then they see your website. They learn more about you, but like a landing page, it's for them to learn about you, but not as much as a homepage.  I know that was a lot of words, but does that make sense?

5:57 - Jillian
  Yeah. And then. Videos and learn more in the process. I just want this to be done correctly.

7:06 - Carmen Cruickshank (weddingindustryads.com)
  No, that makes sense. Yeah, you're definitely doing it correctly. And I'm glad you asked those questions. Yeah. And to the person doing the landing page, she probably knows already what she's doing.  Do you want to just take some notes, things to keep in mind. So that way, when you're like making sure it's a good landing page, you're like, OK, I understand why this works.  Yeah. So I think that would be helpful.

7:25 - Jillian
  OK.

7:25 - Carmen Cruickshank (weddingindustryads.com)
  Do you know where to find the do you see audit and adapt in the courses?

7:30 - Jillian
  Yes.

7:31 - Carmen Cruickshank (weddingindustryads.com)
  OK, perfect.

7:32 - Jillian
  Yes. I think I've started. I started it or either finished that one.

7:39 - Carmen Cruickshank (weddingindustryads.com)
  OK.

7:40 - Jillian
  Yeah. Yeah.

7:41 - Carmen Cruickshank (weddingindustryads.com)
  Do you have any other questions?

7:43 - Jillian
  I don't think so. I think that's it for now. Yeah, I think that's it for now. So the VIP day basically will go over the landing page.
  ACTION ITEM: DM Jillian new VIP day link - WATCH: https://fathom.video/calls/566502955?timestamp=534.9999

7:55 - Carmen Cruickshank (weddingindustryads.com)
  Yes. Yeah, no, definitely go over the landing page and I'll let you know if any changes need to. Mm-hmm.

9:00 - Jillian
  Okay.

9:02 - Carmen Cruickshank (weddingindustryads.com)
  Perfect. Thank you so much. Nice to meet you, Jillian.

9:04 - Jillian
  Thank you. You too. So if you, I can't go and reschedule right now, like I need the other link.

9:11 - Carmen Cruickshank (weddingindustryads.com)
  Yeah. I'm going to contact someone and I'll let you know and I'll send you the link in DMs.

9:16 - Jillian
  Perfect. Okay. Great. Thank you so much.

9:18 - Carmen Cruickshank (weddingindustryads.com)
  I appreciate it. Of course.

9:19 - Jillian
  Thank you. Bye. Bye.

9:22 - Carmen Cruickshank (weddingindustryads.com)
  Hey, Erin.

9:23 - Erin Smith
  How are you? Hi, Carmen. Thanks for the shout out. I just saw it on the board.

9:28 - Carmen Cruickshank (weddingindustryads.com)
  Yeah. No, that, that definitely deserves to be shouted out. Cause that's like, you're, it's a high ticket venue thing.  So that's amazing.

9:35 - Erin Smith
  You know, it's also the, so one was a wedding and one I think was an engagement and it's our biggest wedding ever booked.  So I was like, and I, I just like the fact that I could tie it directly to the ad because we used a certain landing page.  used a certain form. I was like over the moon. Yeah. Yeah. was really great. We've done so well, like at least getting people to submit the form.  We've gotten like 50 submissions on the form, which is great. And so my question, and I had met with Christina in December, and then I just kind of, it fell off my radar, but we were thinking of doing like an A-B testing of the ad, either with a new landing page or new assets or both.  And I just wanted to kind of talk through it to see like what you think is best practice. So one thing, our CRM now will let us customize our forms.  And this was like a big thing when we were putting together my landing page is that our forms are very long, but now they can be short.  Because it will, um, Triple Seat is doing like what they call. Dynamic forms. So I was thinking like, if we try a new landing page with a shorter form, like just capturing name, phone number, email, and like wedding date or something like that, is it better to, I'm just looking at my notes from, you know, I think, so she said we could do a campaign level experiment or do an ad level experiment.  And I'm wondering if it's like best practice, like we don't want our ads to compete against each other because the first one is doing so well.  So I'm just wondering, like, what do you think we should do for, if we wanted to do a second wedding ad?  Is it a competition, like against itself? Like we don't want that to happen.

11:50 - Carmen Cruickshank (weddingindustryads.com)
  Oh yeah, definitely not. My first question is like, are you just thinking of making changes to scale? Or do you think you're just not getting as many leads?  As you want to get from Google Ads, like, why do you think of making a change?

12:06 - Erin Smith
  Honestly, so one thing would be to see if more people submit the form, if it's a shorter form. So, because we had set up click, like there's an inquire now, which is a jump down to the form.  So, overall, we've had 86 people click the inquire now, but we've had 45 people submit the form. So, it's kind of like, let's say 50%.  So, we want more people to submit the form because then we get their information. So, I didn't know if...

12:43 - Carmen Cruickshank (weddingindustryads.com)
  Yeah.

12:44 - Erin Smith
  Yeah. So, that's kind of where, that was my thinking, was that.

12:50 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, because it's like, if that many people are so interested and it's, I mean, you're still getting a good amount of leads, but of course, there's always room for improvement.  I'm just going to see the... The form. Okay. Yeah, no, it's definitely not too long. Do you notice, though, like, when people come as leads, like, most of the time they're quality leads?  Or do you feel like if you took out some fields, like, it wouldn't be as well filtered? You know, I'm trying to avoid that issue, if that makes sense.

13:20 - Erin Smith
  Yeah, um, hold on one second. I'm just sorry, my boss is just texting me. What happens? Okay. So I do, I mean, I think they're quality leads, they're converting, right?  But the, let's see. I do think they're quality leads, and it's probably because we asked for so much on the form, you know?  We asked, you know, one. One of the things that we have in the new form, which isn't quite up and running yet, but we have the ability to say like, do you have an alternate date?  What is your budget? Stuff like that. So the questions could be very much catered to a wedding rather than just like a general event.  And it's like drop downs where we didn't have that ability before. I don't know. I just thought maybe another ad would give us like a little bit more visibility.  But if you think not, then maybe if there's any tweaks, I don't know. mean, was originally when I talked to her, but talk to Christina, we didn't have the ability to edit the form.  This is just like a new feature that rolled out like two weeks ago. So what I had talked to her about was, well, it says changing the goal, but I think our goal is, our goal is like conversion.  So I'm just, I I don't know. She's doing like an experiment.

15:04 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, no, definitely. I agree. I'm trying to get an idea of just the numbers here. What was it? Okay, so 13 leads, 446.  One second. Okay. Yeah, I'm just looking. Let me see. Maybe I should share my screen. My screen is pretty.  I'm messy right now, but let me.

15:31 - Erin Smith
  Okay. My screen is pretty messy right now.

15:34 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, everything's a little cluttered, but.
  SCREEN SHARING: Carmen started screen sharing - WATCH: https://fathom.video/calls/566502955?timestamp=936.01491

15:36 - Erin Smith
  I get it.

15:38 - Carmen Cruickshank (weddingindustryads.com)
  Okay, so I'm going do full screen. And is it? Okay.

15:47 - Erin Smith
  So the ad that is the one that's successful is like search leads WIA.

15:52 - Carmen Cruickshank (weddingindustryads.com)
  All those other ones are, yeah, that one. Mm-hmm. Let's see. Okay. Yeah, so like for example. Yeah. I wish I could honestly filter it.  Where is the clicks? Okay, yeah, so we have 468 clicks, and then we have 13 leads in the past 30 days.  Now, when I did the numbers, I think it was 2.7%, so it definitely could increase, because this is about, like, a third of that.  Yeah, yeah. Yeah, and here's the thing is, I have had clients who have genuine long lead forms, and then I'm like, okay, definitely people are not submitting because of this.  We could, I don't think that's an issue, like, we could definitely try to just do a quick thing. Maybe some people just don't want to think, oh, like, what if I want it at till 8 p.m., and then people, and they don't have availability or something, I don't know.  So we could definitely try a shorter form. I don't feel like that'd be bad, and we could just do it 50-50 split with the budget.  So I think your budget per day is 6, oh, 28.

16:57 - Erin Smith
  Okay, that's good. We bumped it up because... We paused the competitor ad. We weren't getting any conversions from the competitor, like looking at the competitors.  We were getting some eyes, but we took, I think it was like a $15, $5 kind of thing. So we put the $5 over to here.  So yeah, but actually that's another question. So we have $20 a day, I think. Yeah. I think of all time.  So we started working with you in November year to date, we've spent $1,700. So that actually doesn't, well, maybe, I don't know.  I'd have to look to the exact start date, but it was actually a lower spend than I expected. I kind of budgeted a little bit higher, but maybe I was just not doing my math right.

17:55 - Carmen Cruickshank (weddingindustryads.com)
  So. Oh, you're okay. Like, so you're saying there's higher budget?

17:59 - Erin Smith
  Well. there could be. I mean, we could bump it up. And that's, I guess that's my question. If we have a, if we have a compete, not a competing ad, if we had like a testing, you know, like an A-B testing ad, or if we should bump up our per day budget, like which, which would be best practice to get like maybe either more leads or more people who are clicking inquiries.  Or now to like actually fill out the form.

18:32 - Carmen Cruickshank (weddingindustryads.com)
  So no, that's a good question. I feel like, let me see. I'm going to see the past. Wait, let's see.  Like I'll just do a seven day period in February, basically to answer your question. Okay. So you're on average getting 11, five.  Okay. You're getting a good amount. Yeah. As long as, cause the reason sometimes I'll be like, maybe bump up, but bump up the budget is if someone So,  Everyone's getting 10 clicks or less per day, but you guys are getting a pretty good amount. Of course, it's less maybe on the weekend, but 22 clicks, 14 clicks.  I feel like keeping it as it is right now and then just testing, okay, like let's try a shorter lead form and then see if that brings in more people.  And maybe it brings in more people, but you have to, you know, filter out more leads than you decide, okay, what do we prefer?  You know, less quality leads or more general leads? I think that I would do that first. And we could even set it up on a, if you just come with your other landing page, so maybe it's this one, and then it's like 26 wedding and then short form or something.

19:44 - Erin Smith
  Yeah, yeah.

19:45 - Carmen Cruickshank (weddingindustryads.com)
  You know, we, I could just set that up for you to do the experiments here.

19:50 - Erin Smith
  Oh, okay.

19:51 - Carmen Cruickshank (weddingindustryads.com)
  I could set that up for you on an office hours. We're going to start having those weekly. So, what else was it?  I feel like that would be a good start. And And then once you start getting like 30 leads per month, so maybe like one, two leads per day, then what we could do is a performance max campaign.  And so that will just show your ads more to people in their Gmail, people pop up still on search, and then you're getting cheaper cost per leads.  But that definitely is a gradual thing, but definitely the next step, the short lead form. So if you just create that, I can help set that up for you.  And then I do, of course, like if you have more budgets to spend, that's helpful. I wouldn't recommend increasing budget more than like 20% or 40% at a time, because I can just send Google into learning mode.
  ACTION ITEM: Build short-form LP (name/email/phone/date); swap treehouse hero; prep for 50/50 A/B w/ Carmen - WATCH: https://fathom.video/calls/566502955?timestamp=1242.9999  So it's like one change at a time. So yeah, there's so many, there's like a whole variety of things we could do.  And in an ideal world, maybe in the future, we'll increase the budget, but right now it's not essential, if that makes sense.

20:51 - Erin Smith
  Okay. So then, so then step one would be setting up the new landing page with the shorter form.  Step two would be this experiments thing.

21:03 - Carmen Cruickshank (weddingindustryads.com)
  And so that would be basically an experiment using the new landing page form, correct? Exactly. Exactly. And we'll just do a split test.  So I'll do 50% of the budget here, the shorter one, and then 50% of the regular one. And then we just see in a 45-day period which one performs better and, you know, decide from there.

21:24 - Erin Smith
  Okay.

21:25 - Carmen Cruickshank (weddingindustryads.com)
  Okay.

21:26 - Erin Smith
  And do you think, should we change anything else on the landing page or just the form? Like, should we change photos, like, just to see?

21:34 - Carmen Cruickshank (weddingindustryads.com)
  Or is that kind of, like, skewing your results then? Like, maybe, I don't know, if there was anything you would change.  I feel like this is just me visually. This is the, uh, bride thing, right?

21:51 - Erin Smith
  Like, the... That's our treehouse.

21:53 - Carmen Cruickshank (weddingindustryads.com)
  Treehouse? Oh, okay. To be honest, at first I was, like, kind of confused what it was.

21:58 - Erin Smith
  Yeah, I should say, I could... Yeah, it says our magical treehouse. People probably don't realize what that is, but.

22:05 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, like immediately. Yeah, I mean, if it, if there's another angle, maybe. Overall, though, like, and I'm not trying to be critical, like, the pictures do look really, really good.  I want you to be critical.

22:17 - Erin Smith
  Actually, I have a picture there that I can put, that has a bride and groom in it, like, in the treehouse.

22:23 - Carmen Cruickshank (weddingindustryads.com)
  Yes, I think that would be nice, too. Like, because then it really brings it together. But no, I love the, like, flowers appear, the garden here.  It definitely gives off garden venue. No, this is pretty. And it doesn't give off this, like, oh, we're some big venue look at us.  Like, it shows it's micro, but it's, like, intimate. Like, that's what I'm feeling from this. And again, like, I don't think it's essential right now because you guys are getting a good amount of leads.  If you guys have, like, a design specialist or, like, a brand specialist, you could get, like, audits, free audits, and just kind of see.

22:56 - Erin Smith
  Yeah.

22:57 - Carmen Cruickshank (weddingindustryads.com)
  But I think if I was to say, like, a next step, I don't I know if you've heard. Am I frozen?

23:02 - Erin Smith
  I can hear you.

23:03 - Carmen Cruickshank (weddingindustryads.com)
  I just can't see you. I'll just let me see if I can pull it up one second. Okay, you can see me again.  What was it? If you have you heard of Microsoft Clarity?

23:16 - Erin Smith
  You know, I saw you messaged something in the chat.

23:23 - Carmen Cruickshank (weddingindustryads.com)
  I was going to watch that, that Zoom. Yeah, I definitely would recommend it. I don't think, I more recommend Microsoft Clarity when people are not getting leads, because I set up their ads.  I mean, I would say it's correct. And then we have the conversion tracking, they're not getting it. You're getting it.  So if you just want to see data of like, okay, this is what people are engaging with, people are clicking on this picture, people are not, you know, you can just kind of see what people are doing.  I feel like that would actually give you more helpful insights. It's, it's free. It's really not that hard to set up.  I could even help you set it up on an office hours. But honestly, it doesn't really take a deep mark.  Marketing mind to just look at it and say, oh, okay, like, let's switch this, let's switch this. Yeah, okay.  check it together. So, but honestly, I feel like your ads are doing really good. Like you're getting 3% conversion rate.  That'll definitely optimize over time. We can check out that short form AB split test. But overall, I feel like just kind of letting it settle over the next two months, I feel like it'll have a gradual increase.  If it's not, then we're like, okay, like, let's figure out what to do, if that makes sense.

24:26 - Erin Smith
  Okay. And are there any other, because like at the beginning, I did a lot of housekeeping, like cleaning up the words, like negative keywords.  And then I kind of just have been letting it run because it feels like it's working. Are there any other kind of like ongoing, like housekeeping things to like make sure, you know, we're not spending money somewhere we shouldn't in the ad?  Like any of those kind of things?

24:51 - Carmen Cruickshank (weddingindustryads.com)
  No, that's a really good question. Yeah, I think I'd say the biggest thing. Can you see my screen?

24:58 - Erin Smith
  I see my, yeah, I see. Our landing page.

25:01 - Carmen Cruickshank (weddingindustryads.com)
  Okay. Okay. Yeah, I think the biggest thing I do, I don't know if you guys have. Okay. Sometimes it'll show you auction insights, which is just competitors.  I'll just check that for fun. But overall, what I do on a daily thing, just to make sure we're not burning budget, you're right with the search terms.  I think that's number one, biggest thing I do.

25:23 - Erin Smith
  Okay.

25:23 - Carmen Cruickshank (weddingindustryads.com)
  I just check metrics on like a month to month basis. So I'll do, what is it? Like if I had to check an account five minutes a day and make sure it's going well, the metrics I check are click-through rate, which is amazing.  This is normally at 5%, maybe. So 11% is really good. I check conversions, of course. You know, you want to see how much is, you know, happening.  Cost per conversion. And then conversion rate. Of course, this isn't accurate. So we can, we can also do, make a change today.  I'll get to that in a second. little can a I do cost per conversion because you want that ideally at $50 or less and then conversion rate.  So that's pretty much it. These, do you know what these are?

26:10 - Erin Smith
  No, I actually changed my layout to not see those because I didn't know.

26:17 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, I know what you mean. So basically this is impression share. So impression share is how often you show up in your market when people search for wedding venues in New York.  Like that's your market. So it shows you the opportunity that's lost. So if, so the budget, I'm trying to like recalibrate my mind.  If you have really low budget, this is going to have a higher percentage saying that you're not showing up because of budget.  But if it's because of rank, then this is going to be higher. But honestly, I wouldn't pay attention to this of like, oh, I'm not ranking high enough because, you know, your market's really big.

26:56 - Erin Smith
  Like it's New York City.

26:58 - Carmen Cruickshank (weddingindustryads.com)
  It's very competitive. So. I don't know. Just kind of wanted to explain that. But yeah, it's just mainly conversions, clicks.  Everything's really healthy. And just honestly, search terms. Now, if there's an issue, then of course, we'll go deeper into stuff.  Yeah, I have been looking at it weekly.

27:13 - Erin Smith
  I've been using that spreadsheet you guys created and just kind of tracking that. And it seems like we're okay.  So I really haven't spent as much time since the beginning, where I spent a lot of time looking at it every day.

27:27 - Carmen Cruickshank (weddingindustryads.com)
  So yeah, no, that makes sense. I think what I'm going to do, because I know if we have this as a primary action, so you know how we're tracking the clicks and the leads.  So I think I'm going to switch this to secondary.

27:42 - Erin Smith
  Okay.

27:42 - Carmen Cruickshank (weddingindustryads.com)
  that way people can make the leads primary and really go for that. Because I think they're kind of getting comfortable like, oh yeah, we're getting clicks, we're getting conversions.  I see. I don't that. So yeah, it's a small change. And then yeah, you can come back to me next time with that shorter lead form and we can get that.

28:01 - Erin Smith
  Okay. So that you changed the outbound clicks to secondary. Yeah. I remember we talked about that. We took it off, I think, for a while and then we put it back.  So, okay. So that's good.

28:14 - Carmen Cruickshank (weddingindustryads.com)
  That's done.

28:15 - Erin Smith
  Okay. So then I'll work on, I'm just waiting to hear back from Triple C, the CRM to, because we were having a bug with the new form and I want to make sure it's like perfect.  So I'll, I'll work on the form to get it into the new landing page. And then, and then, yeah, like we can set up the experiment.  I'm also going to swap out that treehouse picture.

28:39 - Carmen Cruickshank (weddingindustryads.com)
  So yeah. Yeah.

28:41 - Erin Smith
  No, you know, to people that know us, they know we have a treehouse, but maybe even if I just like bold the word treehouse, maybe people will understand that's what it is.  So the number of people who have asked us, like, do I have to climb up there? We're like, no, not at all.  Like, it's not even a treehouse. Like, it's basically a shed, right?

29:00 - Carmen Cruickshank (weddingindustryads.com)
  Yeah.

29:00 - Erin Smith
  Yeah. But we have some really cool, like newer photos of people in the treehouse.

29:05 - Carmen Cruickshank (weddingindustryads.com)
  So.

29:06 - Erin Smith
  That's cute. Okay. Okay. All right. And then just one quick question about the search terms. Is there anything I should look at?
  SCREEN SHARING: Carmen started screen sharing - WATCH: https://fathom.video/calls/566502955?timestamp=1757.08265

29:13 - Carmen Cruickshank (weddingindustryads.com)
  You said you would look at those. You suggest those or. Let's see. Search terms here. Okay. Honestly, there's no right or wrong.  It's like even me when I'm searching for a client I do full service for. I'll ask them their opinion.  So just anything you guys don't want to be known for. So like the Arches Brooklyn, is that another wedding venue?

29:39 - Erin Smith
  Yeah. Yeah.

29:41 - Carmen Cruickshank (weddingindustryads.com)
  Honestly, like I leave competitors in there, even if it's not for the competitor campaign, because it's like, you want to show your venue to people searching for something else.  Bacchus wedding. I honestly don't know what that is.

29:53 - Erin Smith
  another venue too.

29:55 - Carmen Cruickshank (weddingindustryads.com)
  Okay. Yeah. Honestly, like I just leave competitors in. Okay. Yeah. No. wing virtual all all-inclusive. So wedding packages under 5k in NYC, like that's such a specific one, but I think your guys' minimum price is $5,500, correct?  Yeah, and that's like a winter weekday, so I'm not all-inclusive. Yeah, so I think what I'll just do is, I don't know if I'll take out all-inclusive, because maybe sometimes people, they have a different definition of all-inclusive, where you might look like that to them, if that makes sense, or are you guys really like not all-inclusive?

30:30 - Erin Smith
  Well, we don't have catering on site, we, I mean, we have furniture, and we can provide a bar, but yeah, we have no catering, we don't have a kitchen, so.

30:39 - Carmen Cruickshank (weddingindustryads.com)
  Oh, okay. Yeah, I'll just do all-inclusive, I'll do it in the brackets, and then I'll put it for a campaign, and then I'll also put under 5,000, because just, you're not under 5,000.

30:54 - Erin Smith
  Yeah, yeah. Okay.

31:01 - Carmen Cruickshank (weddingindustryads.com)
  Oh, let's see. I'm going to change this to be 100. Bring your own food when you do wedding venues.  Botanic Garden wedding venue, barn wedding venue. Are there a lot of barn wedding venues?

31:15 - Erin Smith
  No, and I thought I took barn out because we had seen that before.

31:22 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, there's not a barn anywhere. New York City.

31:27 - Erin Smith
  Yeah, I'll do barn.

31:30 - Carmen Cruickshank (weddingindustryads.com)
  Now, if, for example, let's say you didn't want barn at all, like, hard no, then I would do barn in the quotes.  But just because, like, sometimes Google can really mix, like, barn with wedding venue because I just see that's a big thing in the industry.  Like, I don't want Google to be excluding a lot. So I'm just going to do an exact one. Okay.  Let's see. I think it really is kind of objective, like, your opinion. Like, if, let's say, you guys were so high-end, you don't want anything cheap, affordable.  Thank you. Free. I would put the parentheses, you know. Let's see. Cheap, like, yeah, cheapest. Like, this one, I'm going to put quote, or, yeah, quote.  Yeah, we're definitely not the cheapest. You're not the cheapest, and you don't want to be. Diker Heights wedding venue, is that a competitor?

32:23 - Erin Smith
  No, but Diker Heights is a part of Brooklyn, so I would leave that in, just in case. It's just, it's a neighborhood.

32:30 - Carmen Cruickshank (weddingindustryads.com)
  Okay. Overall, though, these look pretty good. Yeah, I think it really is just knowing, and you already know what Carole Hall is.

32:39 - Erin Smith
  Yeah.

32:40 - Carmen Cruickshank (weddingindustryads.com)
  Checking things like that.

32:42 - Erin Smith
  Yeah, and that was something, I don't know if it was with you or with Christina, we took out our own name, like, we, because, I guess we made it a negative keyword, so we weren't bidding against ourselves or something.  I forget what the rationale was, but.

32:59 - Carmen Cruickshank (weddingindustryads.com)
  Mm-hmm.-hmm. Mm
  SCREEN SHARING: Carmen started screen sharing - WATCH: https://fathom.video/calls/566502955?timestamp=2065.548509

35:00 - Michael & Diana
  I added to the homepage. And then that was, once I did that, the booking started to pick up again.

35:11 - Carmen Cruickshank (weddingindustryads.com)
  That's good. And that was like, I think two weeks ago.

35:14 - Michael & Diana
  Yeah.

35:15 - Carmen Cruickshank (weddingindustryads.com)
  Yeah. Wow. No, that's good. And like before, cause I'm just kind of curious, like, cause it says so far for this month, only one appointment booked, but that there could be direct and indirect causes.  Uh, before Google Ads, did you, like, how often would you book per month, if that makes sense?

35:33 - Michael & Diana
  Gosh, that's a good question. Cause a lot of our bookings were coming from Google already. Um, I want to say probably half of the amount.

35:45 - Carmen Cruickshank (weddingindustryads.com)
  Okay. So maybe like 15.

35:48 - Michael & Diana
  Yeah. Maybe even less than that.

35:51 - Carmen Cruickshank (weddingindustryads.com)
  Maybe like, maybe like 10, five to 10. Oh, okay. And so now it's like 30.

35:57 - Michael & Diana
  I think, I mean, that's what we're tracking at.

36:00 - Carmen Cruickshank (weddingindustryads.com)
  Okay. Wow. No, that's good. Yeah. Definitely. me know at the end of February.

36:05 - Michael & Diana
  Cause what are you seeing? Cause you said only one conversion. And then when I go into my Google, like, what's it called?  The, like the, this part of my phone, it says for this month, 12 conversions.

36:25 - Carmen Cruickshank (weddingindustryads.com)
  Yeah. It says 12 conversions. Uh, but that's because 11 was people that clicked the, anything that said book. And then one was an appointment.  Yeah.

36:35 - Michael & Diana
  Okay. Now I'm getting confused. Okay. I literally thought there were 12 appointments, but people have been booking and the bookings have been, I think maybe they're just coming from Google then, not the ad.

36:47 - Carmen Cruickshank (weddingindustryads.com)
  Oh, okay.

36:47 - Michael & Diana
  Yeah. Yeah.

36:48 - Carmen Cruickshank (weddingindustryads.com)
  I mean, I'm like, oh, this person booked and then the numbers are like tracking. Mm-hmm. Mm-hmm. Like, okay.

36:54 - Michael & Diana
  That makes sense. Yeah.

36:56 - Carmen Cruickshank (weddingindustryads.com)
  No, but what's good is like the optimizations will make today. I will probably increase that too. I'll do the same thing I did with Erin, where both of the lead and the button click was set to primary, but I'm just going to put the button click as a secondary.  Just so that Google doesn't think like, oh yeah, we're doing what we're supposed to do. We're getting button clicks, you know.  Yeah, and I think I'll just switch it to maximize conversions. You're not getting as many phone calls, correct?

37:36 - Michael & Diana
  Oh gosh, no.

37:37 - Carmen Cruickshank (weddingindustryads.com)
  That's good.

37:38 - Michael & Diana
  I don't even think I've had one yesterday for a gift card. I walked in through how to like do the gift card online.  And then I've had like two calls in the last two weeks.

37:50 - Carmen Cruickshank (weddingindustryads.com)
  That's awesome.

37:51 - Michael & Diana
  I'm glorious.

37:52 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, I can imagine. I'm just trying to see if there was anything. And normally I don't track recommendations here.  But, I'm just trying to make sure. No. Okay. Yeah, I just kind of like to see, like, if Google recommends anything, because you just never know.  I'm going to check last 30 days just to see.

38:22 - Michael & Diana
  And I do have a client at 10, so I have to get off, like, at 9.55. Just wanted to let you know.

38:28 - Carmen Cruickshank (weddingindustryads.com)
  That makes sense. Let's see. So, click-through rate's good. Okay. Yeah, it's interesting. said in the past 30 days, like, three appointments booked.  But I think it's because this is also set at primary, so I can't really tell too much difference. But once that's off, then it'll be good.  What's three? I'm just going to calculate real quick. Three out of 166.

38:52 - Michael & Diana
  Not great.

38:53 - Carmen Cruickshank (weddingindustryads.com)
  Let me see. Oh, yeah.

38:55 - Michael & Diana
  I'm like, oh my gosh, my, like, people are booking at a 20%. yeah. what I'm I'm don't even know.  I'm

40:00 - Carmen Cruickshank (weddingindustryads.com)
  So Google, like let's say if you wanted $30 cost per lead, then Google will be burning through your budget a lot faster because it wants to get you one or two leads per day.  So it's expecting like 60 bucks per day or something. That makes sense. No, that's not it. Not right now.  Yeah. That's pretty much it. Honestly, just for some best practices, I'll check.

40:21 - Michael & Diana
  Yeah.

40:22 - Carmen Cruickshank (weddingindustryads.com)
  Search terms. I feel like even the how much does it cost? I don't mind keeping it there because like they're curious.
  ACTION ITEM: Review search terms; add negatives (CVS, Opalescence Go, baking soda, homemade, cheapest); keep Core Whitening; remove if wasteful - WATCH: https://fathom.video/calls/566502955?timestamp=2428.9999

40:32 - Michael & Diana
  Right. Oh, the purple whitening strips can come off.

40:43 - Carmen Cruickshank (weddingindustryads.com)
  Yeah. Yeah. Because I almost wonder like I feel like someone wouldn't want to book if they can just get strips.

40:52 - Michael & Diana
  Yeah. I mean, maybe they like see and it triggers, but the, yeah, if you're looking for at-home stuff, typically you're not going to spend.  Yeah. And we're upping our prices in March, so I'm like.

41:03 - Carmen Cruickshank (weddingindustryads.com)
  Okay, that makes sense. At-home teas, think I'll take home, take out at home. Yeah. I think I have heard of that.

41:14 - Michael & Diana
  Oh, I'm like, that sounds great.

41:15 - Carmen Cruickshank (weddingindustryads.com)
  I know. They say, like, take the peel or something, like.

41:20 - Michael & Diana
  Oh, I've literally never heard of that.

41:23 - Carmen Cruickshank (weddingindustryads.com)
  That's funny. Okay, I think I'll just take out banana. Banana. Yeah, I try to, like, not take out the whitened teeth part, because if I just take it out altogether, it just confuses Google.

41:35 - Michael & Diana
  Yeah.

41:35 - Carmen Cruickshank (weddingindustryads.com)
  I'll just take out homemade. Yeah, I remember I was younger, and I would just be watching YouTube and, like, random life hacks or something, and I would see, like, the weirdest things, so.

41:44 - Michael & Diana
  Well, now it's TikTok. There's so many DIY stuff for whitening on. Like, people are painting their teeth with, like, not nail polish, but that's what it looks like.

41:51 - Carmen Cruickshank (weddingindustryads.com)
  I'm like, if I see one more ad for this, I'm going lose it. I know, yeah, literally.

41:55 - Michael & Diana
  That's disgusting. You like polish.

41:57 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, that's horrible. Cool. Core Teeth Whitening. Is that a brand?

42:02 - Michael & Diana
  I literally never heard of it. But if it's a professional, like, dental grade.

42:12 - Carmen Cruickshank (weddingindustryads.com)
  Core Teeth Whitening.

42:14 - Michael & Diana
  whitening with results.

42:17 - Carmen Cruickshank (weddingindustryads.com)
  Oh, okay. But they have at-home stuff, too. Oh, okay.

42:23 - Michael & Diana
  Highly effective professional system designed to remove deep virus terrain. Um, I'm not quite sure about that.

42:32 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, I feel like- Well, it says it costs $800 to $1,200, and ours is not that high. So I think it is a perfect- kind of like Zoom.  Mm-hmm.

42:42 - Michael & Diana
  Similar to that. So I would probably leave that on there for now.

42:45 - Carmen Cruickshank (weddingindustryads.com)
  Mm-hmm. Yeah, I mean, if it's, like, taking all these clicks and wasting budget, then we'll take it out, but it's not too harmful.  Okay. Laser Teeth Whitening, same-day Teeth Whitening, ProSensitive Teeth. Mm-hmm. And we took out- At home already, so that's good.  Took out strips, Philips, Zoom, is that?

43:05 - Michael & Diana
  That is, we'll keep that on there just because that's like what the dental offices use.

43:10 - Carmen Cruickshank (weddingindustryads.com)
  Oh, okay, okay.

43:11 - Michael & Diana
  If they're looking for dental, they're going to, like, we are the same, if that makes sense.

43:15 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, that makes sense. Let's see, best whitener for your teeth, we're going to get my teeth whitened. And this is, as I'm just going through this, have you ever, because I know you guys are not dental, oh what?

43:27 - Michael & Diana
  Opalescence Go, that can be taken off. That's like an at-home.

43:31 - Carmen Cruickshank (weddingindustryads.com)
  Oh, at-home thing?

43:33 - Michael & Diana
  Yep.

43:34 - Carmen Cruickshank (weddingindustryads.com)
  Okay.

43:35 - Michael & Diana
  The whole thing is, yeah.

43:36 - Carmen Cruickshank (weddingindustryads.com)
  Yeah. Because you guys are in dental hygienists, correct?

43:41 - Michael & Diana
  So we are. Yeah, I've been a hygienist for 15 years. I just don't work in the dental office anymore, thankfully.

43:50 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, no, it's nice having your own thing. Let's see. Oh. Where was it? Oh, I thought I saw. Oh, like, looks.  Oh, yeah. Reviews. That's really good. Right there. In-office whitening, teeth bleaching.

44:12 - Michael & Diana
  Aura Glow. That one. Yeah, that one's at home.

44:35 - Carmen Cruickshank (weddingindustryads.com)
  Do we take out baking soda? think I saw baking soda somewhere.

44:38 - Michael & Diana
  just saw it, too.

44:39 - Carmen Cruickshank (weddingindustryads.com)
  I was like, let's not.

44:41 - Michael & Diana
  Where did it go? Right there. Above you by, like, three.

44:47 - Carmen Cruickshank (weddingindustryads.com)
  Okay, baking soda, teeth bleaching, yeah.

44:50 - Michael & Diana
  It's crazy, stinky.

44:53 - Carmen Cruickshank (weddingindustryads.com)
  Yeah, I definitely believe that the changes we made already will get you more bookings from Google Ads. And then we can just see where things are in two weeks.  And then if anything needs to change at all.

45:05 - Michael & Diana
  Okay.

45:06 - Carmen Cruickshank (weddingindustryads.com)
  Okay. Oh. Your coffee stains. I feel like overall this looks pretty good. Oh, cheapest? I'll take cheapest out.

45:20 - Michael & Diana
  We're not.

45:22 - Carmen Cruickshank (weddingindustryads.com)
  Like you're affordable, but not like too affordable.

45:27 - Michael & Diana
  Right. Like it's between home, at home, cheap stuff. There's other whitening techs that are like charging $2.49 and we're raising our price to $3.99 in March.  Like we're doing from $2.99 to $3.99. So we're kind of doing a big jump. Just because we're a luxury brand, I'm like, my friend is like, you built a luxury brand.  Why doesn't your price reflect it? I was like, oh, snap. I don't know why.

45:53 - Carmen Cruickshank (weddingindustryads.com)
  No, that's true though.

45:54 - Michael & Diana
  And what's nice is on the website. it had CVS teeth whitening strips.

45:58 - Carmen Cruickshank (weddingindustryads.com)
  Do you see it? Yeah.

46:00 - Michael & Diana
  I definitely do not want that. That's so weird. I can go through these later, too.

46:05 - Carmen Cruickshank (weddingindustryads.com)
  No, you're good. Yeah. What is it? I'll just do CVS because we took out strips. Yeah. What was it?  No, but I completely agree. Also, what's great is your website justifies the price because, like, for me, when I see it, don't just think it's teeth whitening.  Like, you do the whole wax on the hand thing. It's the experience.

46:25 - Michael & Diana
  So, you know, showing that. Yeah, I finally got that. My videographer to come in and do that. That has been, like, a game changer, I think, for people converting, even if it's just whether it's my website or my landing page, I think that's been really helpful.  And people have mentioned it. They're like, oh, like, I went on your website and then I could see exactly what you do.  And I was, like, super comfortable and I wasn't anxious anymore because I, like, saw the whole process. And I'm like, that's the key.

46:51 - Carmen Cruickshank (weddingindustryads.com)
  No, exactly. And it's insane how some small change like that really just fixes people's minds so much.

46:57 - Michael & Diana
  I know.

46:58 - Carmen Cruickshank (weddingindustryads.com)
  Yeah.

46:58 - Michael & Diana
  Which Which is great.
`;
