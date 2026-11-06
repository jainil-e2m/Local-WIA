import { ContentIdea, Moment } from '../types/atelier';

export const INITIAL_MOMENTS: Moment[] = [
  {
    id: 'm-1',
    source: 'fathom',
    sourceName: 'Client Advisory Call #42',
    speaker: 'Sarah Jenkins (Planner, Napa)',
    clientName: 'Sarah Jenkins Events',
    date: '28 Sep 2026',
    timestamp: '19:42',
    quote: "I haven't posted anything organically on Instagram in like 10 weeks… and leads literally didn't stop coming through the door.",
    type: 'Soundbite',
    clearance: 'cleared',
    channelOrMeeting: 'Fathom · 1-on-1 Strategy',
    audioDuration: '43 min',
    speakerVerified: true,
  },
  {
    id: 'm-2',
    source: 'slack',
    sourceName: '#social-proof-and-results',
    speaker: 'Carmen (WIA Strategist)',
    clientName: 'Aethel Floral Design',
    date: '27 Sep 2026',
    timestamp: '14:15',
    quote: "Their business has doubled… their best month ever in Q3 after revamping the Meta retargeting funnel. $84k in booked contracts.",
    type: 'Result',
    clearance: 'needs_consent',
    channelOrMeeting: 'Slack · Social Proof',
    speakerVerified: true,
  },
  {
    id: 'm-3',
    source: 'zoom',
    sourceName: 'Vault Monthly Workshop: UVP & Offers',
    speaker: 'Whitney (WIA Founder)',
    clientName: 'All Accelerator Cohorts',
    date: '24 Sep 2026',
    timestamp: '09:12',
    quote: "If you sell 'day-of coordination', you are competing on price with college students. Sell 'flawless emotional peace of mind' and price is secondary.",
    type: 'Teaching Point',
    clearance: 'cleared',
    channelOrMeeting: 'Zoom Cloud · Vault Session',
    audioDuration: '62 min',
    speakerVerified: true,
  },
  {
    id: 'm-4',
    source: 'fathom',
    sourceName: 'Office Hours Q&A',
    speaker: 'Elena Rostova (Bridal Photographer)',
    clientName: 'Elena Rostova Studios',
    date: '25 Sep 2026',
    timestamp: '32:05',
    quote: "Brides ghost me after I send my pricing guide PDF. I feel like my PDF is a wall instead of an invitation.",
    type: 'Question / Struggle',
    clearance: 'anonymised',
    channelOrMeeting: 'Fathom · Group Office Hours',
    audioDuration: '55 min',
    speakerVerified: true,
  },
  {
    id: 'm-5',
    source: 'slack',
    sourceName: '#meta-ads-accelerator',
    speaker: 'Giselle (Content Lead)',
    clientName: 'Bella Vista Venues',
    date: '26 Sep 2026',
    timestamp: '11:30',
    quote: "Bella Vista got 19 high-ticket tour bookings in 14 days using the single video creative Whitney scripted.",
    type: 'Result',
    clearance: 'cleared',
    channelOrMeeting: 'Slack · Meta Ads',
    speakerVerified: true,
  },
  {
    id: 'm-6',
    source: 'zoom',
    sourceName: 'Q3 Backfill Sync #12',
    speaker: 'Asha (Ad Manager)',
    clientName: 'Couture Floral Co',
    date: '18 Sep 2026',
    timestamp: '22:18',
    quote: "Search volume for 'intimate micro-weddings' dropped 30%, but inquiries for 150+ guest luxury destination weekends spiked 45%.",
    type: 'Story / Objection',
    clearance: 'cleared',
    channelOrMeeting: 'Zoom Cloud Backfill',
    audioDuration: '38 min',
    speakerVerified: true,
  }
];

export const INITIAL_IDEAS: ContentIdea[] = [
  {
    id: 'idea-1',
    title: 'The Planner Who Stopped Posting...',
    subtitle: '10 weeks without an Instagram post, yet qualified inquiries hit an all-time record.',
    badge: 'Client Call',
    daysAgo: '2 days ago',
    timestamp: '28 Sep 2026',
    primaryQuote: "I haven't posted anything organically on Instagram in like 10 weeks… and leads didn't stop.",
    client: 'Sarah Jenkins Events',
    sourceType: 'fathom',
    sourceDetails: 'Fathom Advisory Call #42 · Timestamp 19:42',
    score: 96,
    scoresBreakdown: {
      proof: 98,
      audiencePain: 95,
      offerFit: 94,
      recurrence: 92,
      novelty: 96,
      demand: 88,
    },
    suggestedCta: 'Elevate',
    gate: 'gate3_pack',
    paletteTheme: 'from-[#8C4A38] to-[#542B21]',
    brief: {
      coreInsight: 'Wedding pros burn 15+ hours a week trying to outsmart the Instagram algorithm when high-net-worth couples book through paid search and curated retargeting, not endless carousel carousels.',
      messageSpine: [
        'The organic treadmill gives you vanity likes from other wedding vendors, not booking deposits from engaged couples.',
        'Sarah paused organic posting for 70 days. Her calendar remained booked through year-end because her paid pipeline was doing the lifting.',
        'High-converting ads give wedding business owners their weekends and creative sanity back.',
        'If you want a booked season without feeling chained to your phone, install an automated client acquisition engine.'
      ],
      audiencePain: 'Exhaustion with social media creation, fear of "disappearing" if they stop posting, guilt over unmade reels.',
      formatSplit: {
        emailFocus: 'Intimate founder confession from Whitney on giving yourself permission to stop dancing for the algorithm.',
        carouselFocus: 'Tactical breakdown: The 5 systems Sarah had running behind the scenes while her IG was dormant.',
        reelsFocus: 'Reel 1: Provocative hot take / Reel 2: Sarah’s before-and-after numbers / Reel 3: The 3 paid ads that replace 30 reels.'
      },
      claimsRequiringConsent: ['Sarah Jenkins’ exact monthly booking numbers (Anonymised to "luxury Napa planner" for public draft).'],
      openQuestionsForWhitney: ['Should we mention Sarah is in Napa, or keep the geography general?']
    },
    research: {
      searchQuery: 'wedding planner instagram fatigue',
      googleTrendsScore: 84,
      trendDirection: 'rising',
      peopleAlsoAsk: [
        'Do wedding planners need to post daily on Instagram?',
        'How many leads come from Instagram for wedding vendors?',
        'How to get wedding clients without social media?',
        'Is paid advertising worth it for boutique wedding planners?'
      ],
      autocomplete: [
        'wedding planner marketing without instagram',
        'wedding vendor social media burnout',
        'meta ads for luxury wedding planners'
      ],
      forumDiscussions: [
        {
          source: 'r/WeddingPhotography',
          snippet: 'Honestly feeling so depressed spending 4 hours editing a reel for 120 views while my brides find me on Google.',
          date: 'Sep 2026'
        },
        {
          source: 'r/EventPlanning',
          snippet: 'Has anyone completely stopped organic posting and just ran $20/day IG ads? Did your bookings survive?',
          date: 'Sep 2026'
        }
      ]
    },
    pack: {
      email: {
        subjectLines: [
          'She didn’t post for 10 weeks (and made $65k)',
          'Confession: You don’t need to post on IG today',
          'What happened when a luxury planner stopped posting'
        ],
        previewText: 'A client told me this on Tuesday and I had to share the transcript...',
        body: `A luxury wedding planner told me something on our Tuesday call that made me smile so wide:

"Whitney, I have a confession. I haven’t posted anything organically on Instagram in like 10 weeks... and leads literally didn't stop."

For the past 4 years, the wedding industry told you:
• Post 5x a week
• Dance for reels
• Document every single tablescape setup
• Keep up with every trending audio

And if you take a weekend off? You’re told your business will fade into obscurity.

Here is the truth: High-end couples don't hire a $15,000 planner because they used a trending pop audio. They hire them because of authority, immediate responsiveness, and clear positioning.

While her organic grid sat quietly:
1. Her Meta Ads ran silently in the background targeting engaged couples within 75 miles.
2. Her LeadLock workflow answered every incoming inquiry within 4 minutes.
3. Her portfolio lookbook landed in their inbox before they could contact another competitor.

She had her best booking quarter in 3 years. And she actually enjoyed her summer weekends.

If you’re ready to step off the content hamster wheel and build a business that runs on systems instead of stamina:

Hit reply with the word ELEVATE, or explore our private consulting below.`,
        ctaButton: 'Discover Elevate Consulting',
        ctaUrl: 'https://weddingindustryads.com/elevate'
      },
      carousel: {
        title: 'The 70-Day Experiment: What Happens When a Luxury Planner Stops Posting?',
        caption: 'Save this for the next time you feel guilty about not posting a reel today. 🥂\n\nOne of our private advisory clients didn’t post a single photo on Instagram for 10 weeks. Her inquiries? At an all-time record.\n\nHere’s what she built behind the scenes so her calendar didn’t depend on the algorithm.\n\nDrop a comment with “ATELIER” and I’ll send you the exact breakdown.\n\n#WeddingPlannerTips #WeddingIndustryAds #WeddingProMarketing',
        slides: [
          {
            slideNumber: 1,
            phase: 'Hook',
            headline: 'She didn’t post on Instagram for 10 weeks.\nHer bookings didn’t stop.',
            body: 'Here is what actually happened when a luxury planner stopped dancing for the algorithm.'
          },
          {
            slideNumber: 2,
            phase: 'Problem',
            headline: 'The Wedding Pro Content Trap',
            body: 'You spend 12 hours a week filming setups, hunting audio, and writing captions.\n\nResult? 34 likes from other vendors, 0 booked contracts, and profound creative burnout.'
          },
          {
            slideNumber: 3,
            phase: 'Problem',
            headline: 'The Myth You Were Sold',
            body: '“If you don’t post every day, high-budget brides will forget you exist.”\n\nExcept luxury couples aren’t scrolling Reels at 2 AM to find their planner—they search when they get engaged, and make decisions based on trust.'
          },
          {
            slideNumber: 4,
            phase: 'Solution',
            headline: 'System 1: Intent-Driven Paid Reach',
            body: 'Instead of hoping the algorithm smiles on your post, she ran 2 targeted Meta creatives to engaged couples within 60 miles for less than the price of a floral arrangement.'
          },
          {
            slideNumber: 5,
            phase: 'Solution',
            headline: 'System 2: The 4-Minute Auto-Responder',
            body: '80% of couples book the first 2 vendors who reply. Her automated system delivered a personalized lookbook while competitors took 48 hours to check their DMs.'
          },
          {
            slideNumber: 6,
            phase: 'Transformation',
            headline: 'The 70-Day Result',
            body: '• 0 organic posts created\n• 24 qualified high-budget inquiries\n• $78,000 in signed event contracts\n• 40+ hours saved for client work and family'
          },
          {
            slideNumber: 7,
            phase: 'How We Help',
            headline: 'Stop Trading Your Life For Likes',
            body: 'In our Elevate advisory, we engineer client-acquisition infrastructure that prints qualified bookings on autopilot—no viral dances required.'
          },
          {
            slideNumber: 8,
            phase: 'CTA',
            headline: 'Ready to build your evergreen booking engine?',
            body: 'DM or comment “ELEVATE” and we’ll share the exact roadmap.'
          }
        ]
      },
      reels: [
        {
          id: 'reel-1',
          angleTitle: 'Angle 1: The Provocative Contrarian Take',
          duration: '35 sec',
          hook: '“I haven’t posted on Instagram in 10 weeks.” That was the opening line from my client Sarah yesterday.',
          visualCue: 'Whitney seated in natural light, speaking candidly to camera, sipping coffee, raw editorial framing.',
          talkingPoints: [
            'Most wedding pros think stopping organic content means business suicide.',
            'Sarah had her biggest revenue quarter in 4 years.',
            'Because paid media brings the buyers, while organic reels bring the lurkers.',
            'If your business dies when you take two weeks off social media, you don’t have a business—you have a social media job.'
          ],
          ctaText: 'Comment ELEVATE if you want the breakdown of her paid setup.'
        },
        {
          id: 'reel-2',
          angleTitle: 'Angle 2: The 3 Ads That Replace 30 Reels',
          duration: '45 sec',
          hook: 'If you could run 3 ads and never worry about what to post on Instagram this week, would you?',
          visualCue: 'Whitney holding phone, pointing to onscreen text overlays highlighting the 3 ad angles.',
          talkingPoints: [
            'Ad 1: The "Real Bride Budget" reality check video.',
            'Ad 2: The Behind-the-Curtain crisis resolution story.',
            'Ad 3: The 30-second Aesthetic Venue Walkthrough.',
            'Set them live with $15/day budget and let them run all wedding season.'
          ],
          ctaText: 'Link in bio for our Accelerator walkthrough.'
        },
        {
          id: 'reel-3',
          angleTitle: 'Angle 3: The Time-Audit Reality Check',
          duration: '30 sec',
          hook: 'How many hours did you spend creating content this week? Be honest.',
          visualCue: 'Text on screen: "15 hrs of reels vs 15 min of review". Direct eye contact, calm authority.',
          talkingPoints: [
            'Average planner spends 12–18 hours a week editing clips.',
            'That’s time you could spend pitching venues or resting.',
            'Sarah redirected that energy into client experience and let ads do the prospecting.',
            'The result? Higher rates, happier clients, and zero Instagram guilt.'
          ],
          ctaText: 'Save this video to remind yourself next time you panic about algorithms.'
        }
      ],
      captions: {
        longFormInstagram: `“Whitney, I have a confession. I haven’t posted anything organically on Instagram in like 10 weeks… and leads didn’t stop.”\n\nWhen Sarah told me this on our client advisory call, I cheered out loud.\n\nBecause for years, wedding vendors have been sold a lie: that your booking calendar is directly tied to how many trending audios you lip-sync to on a Tuesday afternoon.\n\nIt’s not.\n\nHere’s what was actually happening while Sarah’s feed was silent for 70 days:\n\n1. Her Meta Ads were laser-targeted to couples newly engaged in Napa & Sonoma, spending just $20/day.\n2. When an inquiry arrived, her LeadLock workflow fired within 4 minutes with a bespoke portfolio lookbook.\n3. By the time other planners replied 2 days later, Sarah already had the discovery call scheduled.\n\nResult? Her highest grossing quarter in 4 years of business.\n\nIf you are feeling completely exhausted by the social media hamster wheel, take a breath. There is a much quieter, more lucrative way to run your wedding brand.\n\nDrop a comment with ELEVATE and I’ll send you the blueprint.`,
        linkedIn: `A client admitted on our sync this week: "I haven't posted organically on LinkedIn or Instagram in 10 weeks. And we had our best month on record."\n\nB2C wedding service founders often mistake social media visibility for revenue pipeline. In reality, predictable customer acquisition comes from paid distribution and rapid inquiry response systems.\n\nThree lessons from Sarah's 70-day hiatus:\n1. Paid campaigns deliver consistent reach regardless of algorithm shifts.\n2. 80% of couples contract with the vendor who responds first with clear authority.\n3. Freeing 15 hours/week from video editing allows premium high-ticket client delivery.`
      },
      ruleChecks: {
        slideCountValid: true,
        frameworkBeatsPresent: true,
        ctaMatchesTrack: true,
        voiceCriticPassed: true,
        overlapScore: 18,
      }
    }
  },
  {
    id: 'idea-2',
    title: 'Wedding Season Trends 2026',
    subtitle: 'Search queries for high-budget weekend celebrations surge, while single-day elopements level off.',
    badge: 'Industry Trend',
    daysAgo: '3 days ago',
    timestamp: '27 Sep 2026',
    primaryQuote: "Inquiries for 150+ guest luxury destination weekends spiked 45% across our floral and planning roster.",
    client: 'Market Research & Cohort Data',
    sourceType: 'zoom',
    sourceDetails: 'Zoom Vault Workshop #18 · SerpAPI Google Trends',
    score: 91,
    scoresBreakdown: {
      proof: 88,
      audiencePain: 90,
      offerFit: 95,
      recurrence: 94,
      novelty: 92,
      demand: 96,
    },
    suggestedCta: 'Accelerators',
    gate: 'gate2_brief',
    paletteTheme: 'from-[#4D6A53] to-[#2E4334]',
    brief: {
      coreInsight: 'High-end 2026 couples are prioritizing multi-day guest experiences over single-night blowout parties, yet most wedding pros still sell standard "8-hour packages".',
      messageSpine: [
        'Couples are spending more on welcome parties and farewell brunches than ever before.',
        'If your packages only price Saturday, you are leaving 40% of contract value on the table.',
        'Position yourself as a multi-day experience director, not a Saturday vendor.'
      ],
      audiencePain: 'Planners feeling squeezed by single-day margins while coordinating 3 days of logistics.',
      formatSplit: {
        emailFocus: 'The 2026 Shift: Why our top planners are moving to multi-day retainers.',
        carouselFocus: '5 packaging adjustments for luxury planners heading into 2026 booking season.',
        reelsFocus: 'Reel 1: Stop selling 8-hour days / Reel 2: The $35k welcome party trend / Reel 3: How to quote 3-day weekends.'
      },
      claimsRequiringConsent: [],
      openQuestionsForWhitney: ['Should we launch the new Accelerator bundle alongside this?']
    },
    research: {
      searchQuery: 'wedding trends 2026 luxury multi-day',
      googleTrendsScore: 92,
      trendDirection: 'surging',
      peopleAlsoAsk: [
        'What are the luxury wedding trends for 2026?',
        'How much does a 3-day wedding celebration cost?',
        'How do planners charge for wedding weekend events?'
      ],
      autocomplete: [
        'wedding trends 2026 decor',
        '2026 wedding industry predictions',
        'multi-day wedding planning pricing'
      ],
      forumDiscussions: [
        {
          source: 'r/BigBudgetBrides',
          snippet: 'Our planner charged 20% on the whole weekend including the rehearsal dinner and Sunday pool brunch. Worth every penny.',
          date: 'Sep 2026'
        }
      ]
    }
  },
  {
    id: 'idea-3',
    title: 'Turning Inquiries Into Bookings',
    subtitle: 'Why the first 120 minutes decide 78% of your wedding contracts, and how LeadLock automates it.',
    badge: 'Client Story',
    daysAgo: '4 days ago',
    timestamp: '26 Sep 2026',
    primaryQuote: "Their business has doubled… their best month ever in Q3 after installing the rapid responder.",
    client: 'Aethel Floral Design',
    sourceType: 'slack',
    sourceDetails: 'Slack #social-proof-and-results · Carmen',
    score: 89,
    scoresBreakdown: {
      proof: 94,
      audiencePain: 96,
      offerFit: 92,
      recurrence: 86,
      novelty: 82,
      demand: 85,
    },
    suggestedCta: 'Elevate',
    gate: 'gate1_angle',
    paletteTheme: 'from-[#5C5577] to-[#39344D]',
    brief: {
      coreInsight: 'Brides are in an emotional peak when submitting an inquiry form. If they wait 48 hours for a reply, that peak vanishes into buyer skepticism.',
      messageSpine: [
        'The inquiry speed window has shrunk to under two hours.',
        'Speed does not mean sounding like a cold automated robot.',
        'A warm, highly personalized video auto-responder closes 3x more consultations than an email PDF.'
      ],
      audiencePain: 'Losing high-value leads to competitors simply because of busy weekend event schedules.',
      formatSplit: {
        emailFocus: 'The Anatomy of the 4-Minute Wedding Inquiry Response.',
        carouselFocus: 'Before vs After: What brides receive from standard vendors vs elite booking engines.',
        reelsFocus: 'Reel 1: Stop sending pricing PDFs / Reel 2: The Sunday night inquiry test / Reel 3: How to automate without feeling robotic.'
      },
      claimsRequiringConsent: ['Need permission to cite Aethel Floral $84k figure or keep anonymized.'],
      openQuestionsForWhitney: ['Confirm whether this CTA directs to LeadLock standalone or full Elevate.']
    },
    research: {
      searchQuery: 'wedding vendor inquiry response time',
      googleTrendsScore: 76,
      trendDirection: 'rising',
      peopleAlsoAsk: [
        'How fast should a wedding vendor respond to inquiries?',
        'Why do brides ghost wedding planners after inquiry?',
        'How to follow up on wedding inquiries without being annoying?'
      ],
      autocomplete: [
        'wedding inquiry email templates',
        'convert wedding inquiries to phone calls',
        'automated booking CRM for wedding florists'
      ],
      forumDiscussions: [
        {
          source: 'r/weddingplanning',
          snippet: 'If a venue takes 4 days to email me back, I automatically cross them off my list. It feels like they dont care.',
          date: 'Sep 2026'
        }
      ]
    }
  },
  {
    id: 'idea-4',
    title: 'The High-Ticket Pricing Guide Myth',
    subtitle: 'Why sending a 16-page pricing PDF kills luxury consultations before they start.',
    badge: 'Workshop Vault',
    daysAgo: '5 days ago',
    timestamp: '25 Sep 2026',
    primaryQuote: "Brides ghost me after I send my pricing guide PDF. I feel like my PDF is a wall instead of an invitation.",
    client: 'Elena Rostova Studios',
    sourceType: 'fathom',
    sourceDetails: 'Fathom Group Office Hours · Timestamp 32:05',
    score: 87,
    scoresBreakdown: {
      proof: 85,
      audiencePain: 94,
      offerFit: 90,
      recurrence: 91,
      novelty: 84,
      demand: 80,
    },
    suggestedCta: 'Accelerators',
    gate: 'gate1_angle',
    paletteTheme: 'from-[#735A42] to-[#453322]',
    brief: {
      coreInsight: 'When you email a full pricing menu upfront, couples compare numbers on a spreadsheet instead of connecting with your creative vision.',
      messageSpine: [
        'Pricing without context creates price shoppers.',
        'Replace the pricing PDF with an invitation to an investment consultation.',
        'Frame your pricing around their vision, not your package list.'
      ],
      audiencePain: 'Being ghosted immediately after sending pricing guides.',
      formatSplit: {
        emailFocus: 'Why we banned pricing PDFs across our client roster in 2026.',
        carouselFocus: 'The 3 questions to ask before you ever share your pricing.',
        reelsFocus: 'Reel 1: The ghosting culprit / Reel 2: How to respond to "Can you just send pricing?" / Reel 3: The investment conversation script.'
      },
      claimsRequiringConsent: [],
      openQuestionsForWhitney: ['Confirm if this is an Accelerator topic or Vault replay snippet.']
    },
    research: {
      searchQuery: 'wedding planner pricing guide ghosting',
      googleTrendsScore: 78,
      trendDirection: 'stable',
      peopleAlsoAsk: [
        'Should wedding vendors put pricing on their website?',
        'How to stop brides from ghosting after pricing guide?',
        'How to discuss high-end pricing with engaged couples?'
      ],
      autocomplete: [
        'wedding photographer pricing sheet template',
        'wedding pricing guide design tips',
        'handling price objections in wedding industry'
      ],
      forumDiscussions: []
    }
  }
];

export const BRAND_KIT_REFERENCE = {
  founderVoice: {
    name: 'Whitney (WIA Founder)',
    tone: 'Candid, warm, authoritative, zero-fluff, conversational luxury.',
    personGuidelines: 'Use first person ("I") when telling Whitney’s direct experiences and advisory stories; use collective "we" when explaining WIA frameworks, testing results, and ad benchmarks.',
    antiAiCritic: 'Reject phrases like "In the dynamic tapestry of modern nuptials", "Unlock your potential", "Game-changer", or robotic checklist filler. Keep natural cadence, contractions, and authentic wedding trade terminology (BEOs, walkthroughs, full-production, retainer, editorial).'
  },
  strategyPillars: [
    {
      pillar: 'Pillar 1: Systematized Authority',
      description: 'Moving wedding professionals from exhaustion-driven hustle to calm, predictable client acquisition.'
    },
    {
      pillar: 'Pillar 2: Paid Client Pipelines',
      description: 'Meta Ads & Google Search Ads configured specifically for high-net-worth couples and seasonal booking spikes.'
    },
    {
      pillar: 'Pillar 3: Conversion Architecture (LeadLock)',
      description: 'Rapid, bespoke response engines that turn inquiries into signed contracts in under 48 hours.'
    },
    {
      pillar: 'Pillar 4: Premium Positioning & Packaging',
      description: 'Transitioning from commodity day-rate pricing to multi-day, high-ticket retainers.'
    }
  ],
  goldenExemplar: {
    title: 'The 10-Week Organic Hiatus (The "10 Weeks" Suite)',
    sourceCall: 'Fathom Call #42 with Napa Planner',
    deliverablesProduced: '1 Email, 1 8-Slide Carousel, 3 Video Scripts, Captions',
    performance: 'Generated 38 qualified Elevate applications and 14 cohort seats in 7 days.'
  }
};
