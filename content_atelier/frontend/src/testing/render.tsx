import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { AuthContext, type AuthState } from '../auth/AuthProvider';
import { createQueryClient, queryKey } from '../api/query';
import type { Route as ApiRoute } from '../api/routes';

/* Server-side rendering of a screen the way the app mounts it: inside a router, the server-state cache and a sign-in.
   The cache is seeded with the answers the screen would have read, so the markup shows the screen with its data. */

export type Seeded = readonly [route: ApiRoute | string, args: unknown, data: unknown];

export const TEAM: AuthState = { status: 'authenticated', user: { name: 'Fixture', email: 'fixture@example.invalid', role: 'team' }, error: '', refresh: async () => {}, logout: async () => {} };
export const CLIENT: AuthState = { ...TEAM, user: { name: 'Client', email: 'client@example.invalid', role: 'client' } };

export interface RenderOptions {
  /** The URL the screen is opened at (with its query string). */
  url?: string;
  /** The route pattern that mounts it, for a screen that reads path parameters (`/studio/briefs/:briefId`). */
  pattern?: string;
  seed?: Seeded[];
  auth?: AuthState;
}

export function renderScreen(ui: React.ReactElement, { url = '/', pattern, seed = [], auth = TEAM }: RenderOptions = {}): string {
  const client = createQueryClient();
  for (const [route, args, data] of seed) client.setQueryData(queryKey(route as ApiRoute, args), data);
  const html = renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={[url]}>
          {pattern ? <Routes><Route path={pattern} element={ui} /></Routes> : ui}
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
  // Clearing the cache cancels its garbage-collection timers, which would keep a test process with a DOM alive.
  client.clear();
  return html;
}
