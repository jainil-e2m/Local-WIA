import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { getSession, logoutSession, readSessionUser, userInitials, userGreeting, AuthUser } from './session';
import { AuthContext, AuthState } from './AuthProvider';
import { TopHeader } from '../components/TopHeader';

const user: AuthUser = { name: 'Gisselle Morgan', email: 'fixture@example.invalid', role: 'team' };
const fetchResult = (response: Response) => (async () => response) as typeof fetch;

test('session requests use the shared cookie-backed endpoint and bypass cached identities', async () => {
  let request: [unknown, RequestInit | undefined] | undefined;
  const fetcher = (async (url, options) => { request = [url, options]; return Response.json({ user }); }) as typeof fetch;
  assert.deepEqual(await getSession(undefined, fetcher), user);
  assert.equal(request![0], '/api/auth/session');
  assert.equal(request![1]?.credentials, 'include');
  assert.equal(request![1]?.cache, 'no-store');
});

test('an expired session is signed out; network/server failures are not fake guest sessions', async () => {
  assert.equal(await getSession(undefined, fetchResult(new Response(null, { status: 401 }))), null);
  await assert.rejects(getSession(undefined, fetchResult(new Response(null, { status: 503 }))), /unavailable/);
  await assert.rejects(getSession(undefined, fetchResult(Response.json({ user: { ...user, role: 'admin' } }))), /Invalid/);
  await assert.rejects(getSession(undefined, (async () => { throw new Error('network'); }) as typeof fetch), /network/);
  assert.throws(() => readSessionUser({ name: 'Blake', role: 'team' }), /Invalid/);
});

test('logout invalidates the same Command Center cookie through its existing endpoint', async () => {
  let request: [unknown, RequestInit | undefined] | undefined;
  await logoutSession((async (url, options) => { request = [url, options]; return Response.json({ ok: true }); }) as typeof fetch);
  assert.equal(request![0], '/api/auth/logout');
  assert.equal(request![1]?.method, 'POST');
  assert.equal(request![1]?.credentials, 'include');
  await assert.rejects(logoutSession(fetchResult(new Response(null, { status: 500 }))), /Could not sign out/);
});

test('names and initials match Command Center, and greetings use India time', () => {
  assert.equal(userInitials(user.name), 'GM');
  assert.equal(userInitials('Blake'), 'BL');
  assert.equal(userInitials('Wedding Industry Ads'), 'WI');
  assert.equal(readSessionUser({ ...user, name: '  ' }).name, user.email);
  assert.equal(userGreeting(user, new Date('2026-10-06T02:00:00Z')), 'Good morning, Gisselle Morgan');
  assert.equal(userGreeting(user, new Date('2026-10-06T08:00:00Z')), 'Good afternoon, Gisselle Morgan');
  assert.equal(userGreeting(user, new Date('2026-10-06T14:00:00Z')), 'Good evening, Gisselle Morgan');
  assert.equal(userGreeting(null), 'Welcome to Content Atelier');
});

function renderAccount(session: Pick<AuthState, 'user' | 'status'>) {
  const value: AuthState = { ...session, error: '', refresh: async () => {}, logout: async () => {} };
  return renderToStaticMarkup(<AuthContext.Provider value={value}><TopHeader onOpenInbox={() => {}} onOpenBrandKit={() => {}} pendingCount={0} /></AuthContext.Provider>);
}
test('the header renders the authenticated identity, never the old hardcoded account', () => {
  const html = renderAccount({ user, status: 'authenticated' });
  assert.ok(html.includes('Gisselle Morgan'));
  assert.ok(html.includes('GM'));
  assert.ok(!html.includes('Blake'));
  assert.ok(!html.includes('Founder · WIA'));
  const client = renderAccount({ user: { ...user, name: 'Taylor Chen', role: 'client' }, status: 'authenticated' });
  assert.ok(client.includes('Taylor Chen'));
});

test('loading, signed-out and backend-error states do not impersonate a user', () => {
  for (const [status, label] of [['loading', 'Checking session…'], ['unauthenticated', 'Not signed in'], ['error', 'Session unavailable']] as const) {
    const html = renderAccount({ user: null, status });
    assert.ok(html.includes(label));
    assert.ok(!html.includes('Blake'));
    assert.ok(!html.includes('Founder · WIA'));
  }
});
