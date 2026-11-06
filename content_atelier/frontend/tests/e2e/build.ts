/// <reference types="node" />
import { build } from 'vite';

/* Builds the real app, the one the Node server serves in production (VITE_ATELIER_MODE=backend), into dist/ before the browser
   test. ATELIER_E2E_SKIP_BUILD=1 reuses a build already there (CI builds it in the step before). */
export default async function buildApp() {
  if (process.env.ATELIER_E2E_SKIP_BUILD === '1') return;
  process.env.VITE_ATELIER_MODE = 'backend';
  await build({ logLevel: 'warn' });
}
