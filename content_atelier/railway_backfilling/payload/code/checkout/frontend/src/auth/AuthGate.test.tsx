import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { AuthContext, AuthState } from './AuthProvider';
import { AuthGate } from './AuthGate';
import { commandCenterLoginUrl } from './session';

test('studio content is hidden while signed out, loading or unable to verify a session', () => {
  for (const status of ['unauthenticated', 'loading', 'error', 'authenticated'] as const) {
    const auth: AuthState = { status, user: status === 'authenticated' ? { name: 'Fixture', email: 'fixture@example.invalid', role: 'team' } : null, error: 'Session unavailable', refresh: async () => {}, logout: async () => {} };
    const html = renderToStaticMarkup(<AuthContext.Provider value={auth}><AuthGate><p>Private meeting-derived content</p></AuthGate></AuthContext.Provider>);
    assert.equal(html.includes('Private meeting-derived content'), status === 'authenticated');
    if (status === 'error') assert.ok(html.includes('Retry connection'));
    if (status === 'unauthenticated') assert.ok(html.includes('href="/login"'));
  }
});

test('production sign-in stays on the Atelier host', () => {
  assert.equal(commandCenterLoginUrl(), '/login');
});
