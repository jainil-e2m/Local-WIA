export type SourceType = 'fathom' | 'zoom' | 'slack' | 'manual';

export type ClearanceStatus = 'cleared' | 'needs_consent' | 'anonymised';

export type GateStatus = 'gate1_angle' | 'gate2_brief' | 'gate3_pack' | 'approved_for_giselle';
export type MockStudioStage = 'angles' | 'briefs' | 'packs' | 'scheduling' | 'scheduled';

export interface Moment {
  id: string;
  source: SourceType;
  sourceName: string;
  speaker: string;
  clientName: string;
  date: string;
  timestamp: string;
  quote: string;
  type: 'Result' | 'Soundbite' | 'Teaching Point' | 'Question / Struggle' | 'Story / Objection';
  clearance: ClearanceStatus;
  channelOrMeeting: string;
  audioDuration?: string;
  speakerVerified: boolean;
}

export interface SerpApiData {
  origin?: 'editorial';
  note?: string;
  searchQuery: string;
  googleTrendsScore: number | null; // null means no measured demand data.
  trendDirection: 'rising' | 'stable' | 'surging' | null;
  peopleAlsoAsk: string[];
  autocomplete: string[];
  forumDiscussions: { source: string; snippet: string; date: string }[];
}

export interface CarouselSlide {
  slideNumber: number;
  phase: 'Hook' | 'Problem' | 'Solution' | 'Transformation' | 'How We Help' | 'CTA';
  headline: string;
  body: string;
  designNote?: string;
}

export interface ReelScript {
  id: string;
  angleTitle: string;
  duration: string;
  hook: string;
  visualCue: string;
  talkingPoints: string[];
  ctaText: string;
  spokenScript?: string;
  spokenScriptVersion?: number;
  visualSequence?: { beat: string; direction: string }[];
}

export interface ContentPack {
  /** Supplied copy, including metadata and captions absent from generated templates. */
  suppliedCopy?: { email: string; carousel: string; reels: [string, string, string] };
  email: {
    subjectLines: string[];
    previewText: string;
    body: string;
    ctaButton: string;
    ctaUrl: string;
  };
  carousel: {
    title: string;
    slides: CarouselSlide[];
    caption: string;
  };
  reels: ReelScript[];
  captions: {
    longFormInstagram: string;
    linkedIn: string;
  };
  ruleChecks: {
    slideCountValid: boolean;
    frameworkBeatsPresent: boolean;
    ctaMatchesTrack: boolean;
    voiceCriticPassed: boolean;
    overlapScore: number | null; // null means no measured archive review.
  };
}

export type BriefBeat = 'Hook' | 'Problem' | 'Main point' | 'Transformation' | 'CTA';

/** Direction for the five-piece pack; this is not finished copy or publication clearance. */
export interface ProductionBrief {
  version: 1;
  preparedAt: string;
  preparationBasis: string;
  briefType: string;
  readerPromise: string;
  distinctiveness: string;
  narrative: { beat: BriefBeat; direction: string }[];
  evidencePolicy: { established: string[]; hypotheses: string[]; excludedClaims: string[] };
  voice: { perspective: string; tone: string; writingRules: string[]; avoid: string[] };
  email: {
    summary: string;
    readerJob: string;
    lengthGuidance: string;
    subjectDirections: [string, string, string];
    openingDirection: string;
    outline: string[];
    cta: string;
  };
  carousel: {
    summary: string;
    readerJob: string;
    slides: { number: number; beat: BriefBeat; headlineDirection: string; detail: string; visualDirection: string }[];
    captionDirection: string;
  };
  reels: [{ title: string; role: string; summary: string; durationGuidance: string; hookDirection: string; beats: string[]; visualDirection: string; cta: string },
    { title: string; role: string; summary: string; durationGuidance: string; hookDirection: string; beats: string[]; visualDirection: string; cta: string },
    { title: string; role: string; summary: string; durationGuidance: string; hookDirection: string; beats: string[]; visualDirection: string; cta: string }];
  cta: { primaryAction: string; wordingDirection: string; offerBridge: string; destination: string; avoid: string };
  creativeDirection: { treatment: string; assets: string[]; accessibility: string[] };
  distribution: { channels: string[]; sequence: string; adaptation: string };
  success: { primarySignal: string; secondarySignals: string[]; measurementNote: string };
  reviewChecklist: string[];
}

export interface ContentIdea {
  suppliedCopy?: { angle: string; brief: string };
  id: string;
  title: string;
  subtitle: string;
  angleRationale?: {
    topic: string;
    points: { label: string; text: string }[];
    source: 'llm' | 'editorial' | 'mock';
  }; // Concise decision rationale, not internal model reasoning.
  badge: 'Client Call' | 'Industry Trend' | 'Client Story' | 'Workshop Vault' | 'Slack Win' | 'Team Strategy';
  scoreBasis?: 'editorial';
  editorialContext?: {
    audience: string;
    objective: string;
    funnelStage: string;
    pillar: string;
    beliefShift: string;
    suggestedInvitation: string;
    sources: {
      recordingId: string;
      meeting: string;
      recordedAt: string;
      timestamp: string;
      speaker: string;
      quote: string;
      url: string;
      role: 'Primary passage' | 'Supporting passage' | 'Counterpoint';
      interpretation: string;
      speakerVerified: boolean;
    }[];
    brandReferences: { title: string; section: string }[];
    externalContext: { title: string; url: string; summary: string }[];
  };
  daysAgo: string;
  createdAt?: string;
  editorialWeek?: string; // Monday date (YYYY-MM-DD), inherited by brief and pack.
  originalEditorialWeek?: string; // Original source week retained when revived into Weekly Studio.
  revivedAt?: string;
  isMock?: boolean;
  mockLayoutVersion?: number;
  mockDeploymentId?: string; // The four sourced mocks restart once per deployment.
  mockContentPack?: ContentPack; // Saved source-specific template, available after brief approval.
  mockSimulation?: { version: 1; stage: MockStudioStage; changedAt: string };
  timestamp: string;
  primaryQuote: string;
  client: string;
  sourceType: SourceType;
  sourceDetails: string;
  score: number; // composite rank
  scoresBreakdown: {
    proof: number;
    audiencePain: number;
    offerFit: number;
    recurrence: number;
    novelty: number;
    demand: number;
  };
  suggestedCta: 'Elevate' | 'Accelerators' | 'LeadLock';
  gate: GateStatus;
  angleApprovedAt?: string;
  briefApprovedAt?: string;
  publishingApprovedAt?: string;
  scheduledAt?: string; // Publishing instant, persisted as UTC ISO; displayed in IST.
  contentSchedules?: Partial<Record<number, string>>; // Deliverable order 1–5 → UTC publishing instant.
  brief: {
    productionBrief?: ProductionBrief;
    contentPlan?: {
      email: string;
      carousel: string;
      reels: [string, string, string];
    };
    similarityReview?: {
      checkedAt: string;
      periodStart: string;
      periodEnd: string;
      publishedHistoryComplete: boolean;
      matches: { title: string; publishedAt: string; similarity: string; modifications: string[] }[];
    };
    coreInsight: string;
    messageSpine: string[];
    audiencePain: string;
    formatSplit: {
      emailFocus: string;
      carouselFocus: string;
      reelsFocus: string;
    };
    claimsRequiringConsent: string[];
    openQuestionsForWhitney: string[];
  };
  research: SerpApiData;
  pack?: ContentPack;
  paletteTheme?: string;
}

export type PostChannel = 'email' | 'carousel' | 'reel' | 'linkedin';
export type PostStatus = 'posted' | 'scheduled' | 'draft';

export interface CalendarPostItem {
  id: string;
  ideaId: string;
  day: 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';
  dateStr: string;
  time: string;
  channel: PostChannel;
  channelName: string;
  title: string;
  summary: string;
  status: PostStatus;
  metrics?: {
    primaryStat: string;
    secondaryStat?: string;
  };
}
