/* The sample screens (plan 1.F4, 6.F3): the views that render from the built-in examples in src/data. They exist in the demo
   build only (VITE_ATELIER_MODE=mock), each at /sample/<view>, and each carries the "Sample data" marker; the real app has
   no /sample/* path and its bundle carries none of them. sampleViews.test.tsx fails when a sample screen has no marker, when a
   component that imports the examples is not listed below, or when anything the real app imports reaches the examples. */

export type SampleView = 'ideas' | 'previous' | 'moments' | 'research' | 'inbox' | 'packs';

export interface SampleViewEntry {
  id: string;
  path: string;
  title: string;
  sample: SampleView;
}

const sample = (view: SampleView, title: string): SampleViewEntry => ({ id: `sample-${view}`, path: `/sample/${view}`, title, sample: view });

export const SAMPLE_VIEWS: SampleViewEntry[] = [
  sample('ideas', 'Sample: ideas'),
  sample('previous', 'Sample: previous concepts'),
  sample('moments', 'Sample: moments ledger'),
  sample('research', 'Sample: research'),
  sample('inbox', 'Sample: inbox and approvals'),
  sample('packs', 'Sample: content packs'),
];

/** The component files that render the built-in examples. A file in src/components that imports the examples (`../data/...`
    or the example-only types in `../types/atelier`) and is not listed here fails the test. */
export const FIXTURE_COMPONENT_FILES = [
  'AngleEvidence.tsx', 'AngleRationale.tsx', 'BrandKitModal.tsx', 'BriefingOverview.tsx', 'ContentPacksView.tsx', 'EditorialHub.tsx',
  'FlagIdeaModal.tsx', 'IdeaCard.tsx', 'IdeaDetailModal.tsx', 'InboxApprovalsView.tsx', 'MomentsLedgerView.tsx', 'PackSchedulePopover.tsx',
  'ResearchView.tsx', 'ScheduledContent.tsx',
] as const;
