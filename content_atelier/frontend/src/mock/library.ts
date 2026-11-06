import { ContentIdea } from '../types/atelier';
import { INITIAL_IDEAS } from '../data/mockData';
import { mergeEditorialMocks } from '../data/editorialMockData';
import { resetStudioForDeployment } from '../utils/studioDeployment';
import { stampEditorialItem } from '../utils/editorialWeeks';

/* The demo build's library of example concepts, kept in this browser's localStorage (VITE_ATELIER_MODE=mock only; the real
   app's bundle carries none of it, 6.F3). The saved flow (App.tsx) and the sample screens (SampleDataWorkspace.tsx) share it. */

// Vite writes the build's id here (vite.config.ts `define`); a test run has none.
declare const __ATELIER_BUILD_ID__: string | undefined;

/** Which build this is: each build restarts the four sourced example concepts once, and reloads of the same build keep
    their progress (6.F4; this replaced an id the server handed out at /api/studio/deployment). */
export function demoDeploymentId(): string {
  if (import.meta.env?.DEV) return 'local-development';
  return (typeof __ATELIER_BUILD_ID__ === 'string' && __ATELIER_BUILD_ID__) || 'local-development';
}

export const EDITORIAL_STORAGE_KEY = 'wia-editorial-library-v1';

/** The saved library, merged with the supplied examples and restarted for this build. */
export function loadEditorialLibrary(deploymentId = demoDeploymentId()): ContentIdea[] {
  let ideas = INITIAL_IDEAS;
  try {
    const saved = JSON.parse(localStorage.getItem(EDITORIAL_STORAGE_KEY) || 'null');
    if (Array.isArray(saved) && saved.length && saved.every(item => item.id && item.title && item.brief && item.research && ['gate1_angle', 'gate2_brief', 'gate3_pack', 'approved_for_giselle'].includes(item.gate))) {
      ideas = [...saved, ...INITIAL_IDEAS.filter(idea => !saved.some(item => item.id === idea.id))];
    }
  } catch { /* Use the supplied library when browser storage is unavailable. */ }
  return resetStudioForDeployment(mergeEditorialMocks(ideas), deploymentId).map(idea => stampEditorialItem(idea));
}

export function saveEditorialLibrary(ideas: ContentIdea[]) {
  try { localStorage.setItem(EDITORIAL_STORAGE_KEY, JSON.stringify(ideas)); }
  catch { /* Keep the in-memory workflow usable when storage is blocked. */ }
}
