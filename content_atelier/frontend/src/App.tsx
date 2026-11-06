/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { AppRoutes } from './app/AppRoutes';
import MockApp from './mock/MockApp';

/** The real, API-backed app unless the build explicitly asks for the saved demo (`VITE_ATELIER_MODE=mock`, 6.F3). The mode is
    replaced at build time, so the real app's bundle carries none of the demo (its flow, its sample screens, its examples)
    and the demo's carries none of the real app. A plain `npm run build` and the Dockerfile's default both give the real
    app (7.F2). Authentication wraps both. */
export default function App() {
  return import.meta.env.VITE_ATELIER_MODE === 'mock' ? <MockApp /> : <AppRoutes />;
}
