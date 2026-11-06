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
  assert.equal(commandCenterLoginUrl('/', 'command-center'), '/api/auth/sso/start');
});

test('6.F8: a deep link survives sign-in in one hop when the server signs in through Command Center', () => {
  const deep = '/studio/briefs/brief_1?status=pending';
  assert.equal(commandCenterLoginUrl(deep, 'command-center'), `/api/auth/sso/start?returnTo=${encodeURIComponent(deep)}`);
  // Without a public Command Center origin the server has only its form, which follows the same returnTo (login.js).
  assert.equal(commandCenterLoginUrl(deep, 'form'), `/login?returnTo=${encodeURIComponent(deep)}`);
  assert.equal(commandCenterLoginUrl(deep), `/login?returnTo=${encodeURIComponent(deep)}`, 'the form is the fallback');
  const auth: AuthState = { status: 'unauthenticated', user: null, error: '', signIn: 'command-center', refresh: async () => {}, logout: async () => {} };
  const html = renderToStaticMarkup(<AuthContext.Provider value={auth}><AuthGate><p>Private</p></AuthGate></AuthContext.Provider>);
  assert.ok(html.includes('href="/api/auth/sso/start"'), 'the gate\'s link goes straight to the hand-off');
});

test('a client session sees no studio content, only a team-only notice (S.F3)', () => {
  const auth: AuthState = { status: 'authenticated', user: { name: 'Client', email: 'client@example.invalid', role: 'client' }, error: '', refresh: async () => {}, logout: async () => {} };
  const html = renderToStaticMarkup(<AuthContext.Provider value={auth}><AuthGate><p>Private meeting-derived content</p></AuthGate></AuthContext.Provider>);
  assert.equal(html.includes('Private meeting-derived content'), false);
  assert.ok(html.includes('WIA team only'));
  assert.ok(html.includes('Sign out'));
});
