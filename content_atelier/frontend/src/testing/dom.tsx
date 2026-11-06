import { installDom } from './setupDom';
import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthContext, type AuthState } from '../auth/AuthProvider';
import { createQueryClient } from '../api/query';
import { TEAM } from './render';

/* A browser for the view tests that need effects, clicks and a real client render (an error boundary, a refused write, a
   screen that must not fetch). Each test file runs in its own process, so installing the globals here affects only it. */

export interface Mounted {
  container: HTMLElement;
  client: QueryClient;
  text(): string;
  click(element: Element | null): Promise<void>;
  type(element: HTMLInputElement | HTMLTextAreaElement, value: string): Promise<void>;
  choose(element: HTMLSelectElement, value: string): Promise<void>;
  tick(element: HTMLInputElement): Promise<void>;
  settle(): Promise<void>;
  unmount(): Promise<void>;
}

/** Mounts the screen the way the app does: router, server-state cache and sign-in. Effects run and requests are made. */
export async function mount(ui: React.ReactElement, { url = '/', pattern, auth = TEAM, client = createQueryClient() }: { url?: string; pattern?: string; auth?: AuthState; client?: QueryClient } = {}): Promise<Mounted> {
  installDom();
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);
  await act(async () => {
    root.render(
      <QueryClientProvider client={client}>
        <AuthContext.Provider value={auth}>
          <MemoryRouter initialEntries={[url]}>{pattern ? <Routes><Route path={pattern} element={ui} /></Routes> : ui}</MemoryRouter>
        </AuthContext.Provider>
      </QueryClientProvider>,
    );
  });
  const settle = async () => { await act(async () => { await new Promise(resolve => setTimeout(resolve, 20)); }); };
  return {
    container, client,
    text: () => container.textContent ?? '',
    click: async element => { await act(async () => { element?.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true })); }); },
    type: async (element, value) => {
      await act(async () => {
        const prototype = Object.getPrototypeOf(element);
        Object.getOwnPropertyDescriptor(prototype, 'value')!.set!.call(element, value);
        element.dispatchEvent(new window.Event('input', { bubbles: true }));
      });
    },
    choose: async (element, value) => {
      await act(async () => { element.value = value; element.dispatchEvent(new window.Event('change', { bubbles: true })); });
    },
    tick: async element => { await act(async () => { element.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true })); }); },
    settle,
    // Clearing the cache also cancels its garbage-collection timers, which would keep the test process alive.
    unmount: async () => { await act(async () => root.unmount()); client.clear(); container.remove(); },
  };
}

/** Replaces fetch for a test; returns the calls made. The answer function gets the URL and options. */
export function stubFetch(answer: (url: string, options?: RequestInit) => Response | Promise<Response>) {
  const calls: { url: string; options?: RequestInit }[] = [];
  const original = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL, options?: RequestInit) => {
    const url = String(input);
    calls.push({ url, options });
    return answer(url, options);
  }) as typeof fetch;
  return { calls, restore: () => { globalThis.fetch = original; } };
}

export const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
