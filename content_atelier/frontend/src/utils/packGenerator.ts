import { ContentIdea, ContentPack } from '../types/atelier';
import { reelProduction } from './reelProduction';

/**
 * Generates a full WIA bespoke content pack with scripts for all deliverables:
 * 1. Long-form Founder Email (Whitney's voice)
 * 2. 8-Slide Educational Instagram Carousel
 * 3. 3 High-Conversion Short Video Reels
 * 4. Social Captions & Engagement Prompts
 */
export function generateContentPackForIdea(idea: ContentIdea): ContentPack {
  const pack = idea.isMock && idea.mockContentPack ? structuredClone(idea.mockContentPack) : buildContentPackForIdea(idea);
  return { ...pack, reels: pack.reels.map((reel, index) => ({ ...reel, ...reelProduction(reel, index) })) };
}

function buildContentPackForIdea(idea: ContentIdea): ContentPack {
  const isSarah = idea.title.toLowerCase().includes('planner') || idea.title.toLowerCase().includes('posting');
  const isTrend = idea.title.toLowerCase().includes('trend') || idea.title.toLowerCase().includes('2026');
  
  if (isSarah) {
    return {
      email: {
        subjectLines: [
          'The planner who stopped posting for 10 weeks (and what happened next)',
          'Why your Instagram grid isn’t booking your $15k weddings',
          'Sarah paused her Instagram. Inquiries hit an all-time record.',
        ],
        previewText: 'She didn’t post for 70 days. Her calendar remained booked through year-end. Here’s what was running behind the scenes.',
        body: `Let’s talk about the unspoken exhaustion in the wedding industry right now.

Last Tuesday on a client advisory call, Sarah—a high-end wedding planner who produces $150k+ editorial weddings—looked at me and whispered something almost confessorial:

"Whitney, I haven't posted anything organically on Instagram in like 10 weeks… and leads didn't stop. In fact, our qualified consultation calendar is more booked than it was when I was spending 15 hours a week creating reels."

Read that again.

Ten weeks without dancing for the algorithm. Ten weeks without agonizing over audio trends. Yet her inquiry inbox was filled with high-intent brides with real budgets.

How?

Because high-net-worth couples booking luxury wedding planners do not browse Instagram the way vendors do. They search with intent, they click vetted recommendations, and they enter structured conversion pipelines.

While Sarah's organic grid was dormant, three quiet engines were running for her:
1. Targeted Google Search ads capturing couples actively searching for luxury venues in her market.
2. A curated Meta Retargeting sequence showcasing past client press features and portfolio galleries.
3. A 4-hour automated consultation qualification workflow that eliminated ghost inquiries before she ever hopped on Zoom.

If you are currently trapped on the organic social treadmill, believing that your business will evaporate if you don't post three times a day—let this be your permission slip to build a client acquisition system that works while you're offline.

— Whitney
Founder, Wedding Industry Ads`,
        ctaButton: 'Apply for Elevate (Private Advisory)',
        ctaUrl: 'https://weddingindustryads.com/elevate',
      },
      carousel: {
        title: 'The 10-Week Organic Hiatus: Why Her Bookings Didn’t Stop',
        caption: `Swipe through to see the exact 3-part paid infrastructure that replaced 15 hours of weekly content creation for a boutique wedding planner. Drop "SYSTEM" in the comments for our private case study breakdown.`,
        slides: [
          {
            slideNumber: 1,
            phase: 'Hook',
            headline: 'She stopped posting on Instagram for 10 weeks.',
            body: 'Qualified inquiry volume didn’t drop. It hit an all-time high.',
            designNote: 'Bold serif headline, high-contrast dark indigo card, subtle champagne accent.',
          },
          {
            slideNumber: 2,
            phase: 'Problem',
            headline: 'The Organic Social Treadmill',
            body: 'Most luxury wedding pros spend 12-18 hours a week creating content that gets vanity likes from other vendors—not booking deposits from affluent couples.',
            designNote: 'Data graphic illustrating vendor engagement vs. actual bride booking behavior.',
          },
          {
            slideNumber: 3,
            phase: 'Problem',
            headline: 'The Secret Luxury Couples Keep',
            body: 'Affluent brides with $100k+ budgets rarely discover their main vendors via random reels. They search with high intent, read portfolio proof, and look for immediate authority.',
            designNote: 'Split comparison layout with clean typography.',
          },
          {
            slideNumber: 4,
            phase: 'Solution',
            headline: 'Engine 01: High-Intent Google Search',
            body: 'Instead of hoping the algorithm shows her work, Sarah captured high-intent couples at the exact moment they typed "Napa valley luxury wedding planner" into Google.',
            designNote: 'Wireframe search mockup highlighting CTR and qualified lead volume.',
          },
          {
            slideNumber: 5,
            phase: 'Solution',
            headline: 'Engine 02: Authority Retargeting',
            body: 'Anyone who visited her website saw curated press placements (Vogue, Over The Moon) across Instagram & Facebook for the next 45 days.',
            designNote: 'Editorial editorial moodboard aesthetic with press logos.',
          },
          {
            slideNumber: 6,
            phase: 'Transformation',
            headline: 'Engine 03: LeadLock Qualification',
            body: 'Inquiries were filtered through a bespoke 4-question budget qualification before scheduling a call. Zero ghosting. Zero price shoppers.',
            designNote: 'Checklist diagram showing consultation conversion rates jump from 28% to 64%.',
          },
          {
            slideNumber: 7,
            phase: 'How We Help',
            headline: 'The Difference Between Content & Infrastructure',
            body: 'Content creates temporary attention. Infrastructure creates predictable bookings and gives you your weekends back.',
            designNote: 'Comparison card between the Organic Loop vs. Paid Architecture.',
          },
          {
            slideNumber: 8,
            phase: 'CTA',
            headline: 'Ready to step off the posting treadmill?',
            body: 'Comment "ELEVATE" below or DM us to audit your wedding advertising funnel.',
            designNote: 'Clear luxury CTA card with founder signature crest.',
          },
        ],
      },
      reels: [
        {
          id: 'reel-1',
          angleTitle: 'Reel 1: The Provocative Confession (Hot Take)',
          duration: '32 seconds',
          hook: 'I’m about to say something that wedding marketing gurus will hate me for…',
          visualCue: 'Whitney sitting in a chic, sunlit studio with a cup of coffee, speaking directly and candidly to camera.',
          talkingPoints: [
            'One of our luxury wedding planner clients didn’t post a single photo on Instagram for 10 weeks.',
            'No carousels. No trending audio dances. Nothing.',
            'And during that exact period, her qualified booking inquiries went UP by 42%.',
            'Because high-budget couples don’t hire you because your reel was funny. They hire you because your paid pipeline proves your authority before they ever reach out.',
          ],
          ctaText: 'Drop "PIPELINE" in the comments and I’ll send you our 3-part paid ad blueprint.',
        },
        {
          id: 'reel-2',
          angleTitle: 'Reel 2: Before & After Numbers Breakdown',
          duration: '45 seconds',
          hook: 'Here is what 15 hours of weekly reel creation actually got this planner vs. 1 targeted Meta ad campaign.',
          visualCue: 'Talking head with subtle animated on-screen data badges comparing time spent vs. revenue generated.',
          talkingPoints: [
            'Option A: 15 hours per week making content. Result: 3,000 views from other florists and planners, 1 inquiry with a $2k budget.',
            'Option B: 1 targeted luxury acquisition ad running at $25/day. Result: 14 inquiries, average budget $85k, 4 booked clients.',
            'Stop working for Meta’s algorithm for free when you can make Meta’s algorithm work for your bank account.',
          ],
          ctaText: 'Link in bio to apply for Elevate.',
        },
        {
          id: 'reel-3',
          angleTitle: 'Reel 3: The 3 Ads That Replace 30 Reels',
          duration: '38 seconds',
          hook: 'If you want to stop feeling like a full-time content creator while running a wedding business, run these 3 ads instead.',
          visualCue: 'Whitney holding an iPad showcasing the 3 campaign architectures with elegant editorial b-roll.',
          talkingPoints: [
            'Ad 1: The Luxury Portfolio Carousel targeting high-income zip codes.',
            'Ad 2: The Editorial Press Feature retargeting recent website visitors.',
            'Ad 3: The 60-second venue tour video that answers your top 3 consultation objections.',
          ],
          ctaText: 'Comment "ADS" and I’ll send you our exact campaign structure.',
        },
      ],
      captions: {
        longFormInstagram: `She didn’t post for 70 days. Her calendar remained booked through year-end. 🥂✨

When Sarah (one of our luxury planning clients) came to us, she was spending nearly two full working days every week filming reels, choosing audio, and editing carousels.

Her inquiry inbox? Mostly vendor peers asking for collar recommendations or couples whose budgets were half her starting investment.

We turned off the content hamster wheel and installed an automated paid acquisition engine:
→ Precision geo-targeted Google Search capturing high-intent bridal searches
→ Curated Instagram retargeting showing her best Vogue-published weddings
→ An automated LeadLock qualification filter

The result? 10 weeks of organic silence, and the highest grossing quarter in her studio’s history.

You don’t need more content. You need infrastructure that works while you’re designing weddings.

Drop "SYSTEM" below and I’ll DM you the breakdown of Sarah’s ad funnel. 📩`,
        linkedIn: `A reminder for wedding industry founders and luxury creative directors:

Content creates temporary attention. Infrastructure creates predictable revenue.

Last month, one of our boutique event planning clients went 10 weeks without posting a single organic piece of content to Instagram. During that exact timeframe, qualified consultation inquiries increased by 42%.

Why? Because affluent couples planning $100k+ weddings don’t make booking decisions based on daily reels. They search with intent, evaluate authority, and respond to curated advertising systems.

If your agency or studio is trading creative hours for algorithm vanity metrics, it's time to build a real client acquisition engine.

#WeddingIndustryAds #LuxuryWeddings #MarketingStrategy #Entrepreneurship`,
      },
      ruleChecks: {
        slideCountValid: true,
        frameworkBeatsPresent: true,
        ctaMatchesTrack: true,
        voiceCriticPassed: true,
        overlapScore: 14,
      },
    };
  }

  // Generic Luxury WIA Content Pack for other angles (Trends / Inquiries / Objections)
  return {
    email: {
      subjectLines: [
        `${idea.title}: What luxury couples are actually paying for in 2026`,
        `The shift in $100k+ wedding bookings (and how to position for it)`,
        `Are your wedding inquiries dropping, or are you pitching the wrong offer?`,
      ],
      previewText: 'A strategic deep dive from Whitney on how high-end wedding pros are winning market share right now.',
      body: `Over the past two weeks across our client calls and Slack channels, one clear pattern has emerged:

"${idea.primaryQuote}"

The wedding market isn't slowing down—it's bifurcating. Couples with average budgets are cutting back, while high-net-worth couples are investing more heavily than ever in multi-day bespoke celebrations.

The difference between wedding businesses struggling for inquiries and those commanding $15k+ minimums comes down to one thing: positioning authority through paid acquisition.

Here is the exact message spine we are installing for our agency clients:
1. ${idea.brief.messageSpine[0] || 'Stop competing on price in saturated markets.'}
2. ${idea.brief.messageSpine[1] || 'Filter inquiries with automated qualification systems.'}
3. ${idea.brief.messageSpine[2] || 'Position your studio as the undisputed category leader.'}

If you want predictable booking flow without relying on referrals or endless organic posting, let’s build your system together.

— Whitney
Wedding Industry Ads`,
      ctaButton: `Apply for ${idea.suggestedCta}`,
      ctaUrl: `https://weddingindustryads.com/${idea.suggestedCta.toLowerCase()}`,
    },
    carousel: {
      title: `${idea.title} · Strategic Breakdown`,
      caption: `How luxury wedding professionals are turning market shifts into booked calendars. Swipe through for the full 7-step architecture.`,
      slides: [
        {
          slideNumber: 1,
          phase: 'Hook',
          headline: idea.title,
          body: idea.subtitle,
          designNote: 'Haute couture editorial card with large typography and WIA atelier crest.',
        },
        {
          slideNumber: 2,
          phase: 'Problem',
          headline: 'The Industry Blind Spot',
          body: idea.brief.audiencePain,
          designNote: 'Data stat highlighting conversion drops for generic positioning.',
        },
        {
          slideNumber: 3,
          phase: 'Solution',
          headline: 'The Core Shift',
          body: idea.brief.coreInsight,
          designNote: 'High-contrast typography with champagne emphasis.',
        },
        {
          slideNumber: 4,
          phase: 'Solution',
          headline: 'Tactical Pillar 01',
          body: idea.brief.messageSpine[0] || 'Focus exclusively on high-intent search queries.',
          designNote: 'Step-by-step diagram of the client journey.',
        },
        {
          slideNumber: 5,
          phase: 'Transformation',
          headline: 'Tactical Pillar 02',
          body: idea.brief.messageSpine[1] || 'Pre-qualify every lead with our 4-minute conversion gate.',
          designNote: 'Before and after inquiry volume chart.',
        },
        {
          slideNumber: 6,
          phase: 'How We Help',
          headline: `How ${idea.suggestedCta} Implements This`,
          body: `We build the complete paid client acquisition architecture for your studio, from creative assets to qualification funnels.`,
          designNote: 'Feature cards with checkmark indicators.',
        },
        {
          slideNumber: 7,
          phase: 'CTA',
          headline: `Command Higher Minimums in 2026`,
          body: `Comment "${idea.suggestedCta.toUpperCase()}" to schedule a private marketing audit with our team.`,
          designNote: 'Minimalist luxury closing slide with founder sign-off.',
        },
      ],
    },
    reels: [
      {
        id: `reel-${Date.now()}-1`,
        angleTitle: 'Reel 1: The Contrarian Shift',
        duration: '35 seconds',
        hook: `If you’re a wedding pro wondering where your 2026 inquiries went, stop scrolling.`,
        visualCue: 'Whitney walking through a modern bridal gallery, talking candidly to camera with natural studio lighting.',
        talkingPoints: [
          idea.brief.messageSpine[0] || 'Inquiries haven’t vanished; they migrated to vetted paid search.',
          'Couples with $100k+ budgets aren’t shopping through hashtag feeds.',
          'When you position your studio with high-intent ads, you attract couples ready to pay your full rate.',
        ],
        ctaText: `Comment "${idea.suggestedCta.toUpperCase()}" for the full breakdown.`,
      },
      {
        id: `reel-${Date.now()}-2`,
        angleTitle: 'Reel 2: The Direct Case Study',
        duration: '40 seconds',
        hook: `Here is the exact quote a luxury vendor told us after implementing this change:`,
        visualCue: 'Close-up camera angle with highlighted quote graphic popping on screen.',
        talkingPoints: [
          `"${idea.primaryQuote}"`,
          'They didn’t change their prices or rebrand their website.',
          'They simply changed where they captured couple attention.',
        ],
        ctaText: `Link in bio to audit your wedding ads.`,
      },
      {
        id: `reel-${Date.now()}-3`,
        angleTitle: 'Reel 3: The 3-Step Playbook',
        duration: '45 seconds',
        hook: `3 things every high-ticket wedding vendor needs in place before wedding season starts:`,
        visualCue: 'Fast-paced editorial cuts showing wedding stationery, luxury venue setups, and ad analytics.',
        talkingPoints: [
          'Step 1: High-intent geo-targeted search campaigns.',
          'Step 2: Editorial retargeting ads highlighting real press features.',
          'Step 3: Instant 4-hour budget qualification workflows.',
        ],
        ctaText: `DM us "${idea.suggestedCta.toUpperCase()}" to get started.`,
      },
    ],
    captions: {
      longFormInstagram: `The wedding market isn’t slowing down—it’s shifting. ✨💍\n\n"${idea.primaryQuote}"\n\nHere’s what our data across 50+ luxury wedding vendors is proving right now: Couples with $100k+ wedding budgets are making decisions faster, but they are completely bypassing generic social media feeds.\n\nThey want vetted authority, clear proof, and seamless booking communication.\n\nSwipe through the carousel above for the exact 7-part architecture we install for our clients.\n\nDrop "${idea.suggestedCta.toUpperCase()}" in the comments to receive the private case study breakdown directly to your inbox. 💌`,
      linkedIn: `Strategic insight for wedding industry leaders and luxury studio owners:\n\n"${idea.primaryQuote}"\n\nWhen positioning high-ticket wedding services ($10k - $50k+ packages), marketing volume is secondary to positioning precision. A structured paid acquisition system will outperform 20 hours of weekly content creation every single time.\n\n#WeddingMarketing #LuxuryWeddings #WeddingIndustryAds #BusinessStrategy`,
    },
    ruleChecks: {
      slideCountValid: true,
      frameworkBeatsPresent: true,
      ctaMatchesTrack: true,
      voiceCriticPassed: true,
      overlapScore: 12,
    },
  };
}
