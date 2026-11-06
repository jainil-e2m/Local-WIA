import { paths } from './routes';

/* Every view of the app (plan 1.F1, 1.F4). Each reads the stored data through the API and has a path of its own. The
   screens that render the built-in examples are not here: they exist in the demo build only (src/mock/sampleViews.ts,
   6.F3), and viewRegistry.test.ts fails when anything this app imports reaches them or the examples. */

export interface ViewEntry {
  id: string;
  path: string;
  title: string;
}

export const VIEWS: ViewEntry[] = [
  { id: 'home', path: paths.home, title: 'Home' },
  { id: 'studio-angles', path: paths.angles, title: 'Weekly Studio: content angles' },
  { id: 'studio-briefs', path: paths.briefs, title: 'Weekly Studio: content briefs' },
  { id: 'studio-packs', path: paths.studioPacks, title: 'Weekly Studio: content packs' },
  { id: 'studio-scheduled', path: paths.scheduled, title: 'Weekly Studio: scheduled content' },
  { id: 'previous', path: paths.previous, title: 'Previous Concepts' },
  { id: 'packs', path: paths.packs, title: 'Content Packs' },
  { id: 'sources-documents', path: paths.documents, title: 'Sources: documents' },
  { id: 'sources-intake', path: paths.intake, title: 'Sources: intake' },
  { id: 'moments-ledger', path: paths.moments, title: 'Moments: the ledger' },
  { id: 'knowledge-review', path: paths.review, title: 'Knowledge: review queue' },
  { id: 'knowledge-known', path: paths.known, title: 'Knowledge: what the system knows' },
  { id: 'knowledge-versions', path: paths.versions, title: 'Knowledge: versions' },
  { id: 'settings', path: paths.settings, title: 'Settings' },
];
