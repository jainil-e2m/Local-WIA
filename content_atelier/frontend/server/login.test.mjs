import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

/* The sign-in page's script (login.js) follows ?returnTo= after a successful sign-in. It must only ever go to a page on
   this host: an address the browser would read as another host is an open redirect after sign-in (a phishing aid). */

const ORIGIN = 'https://atelier.example.test';
const source = readFileSync(new URL('./login.js', import.meta.url), 'utf8');

/** Runs login.js the way the browser does, submits the form, and returns where the page sent the person. */
async function signInWith(search) {
  let submit;
  let destination = null;
  const element = () => ({ hidden: true, textContent: '', disabled: false, value: '' });
  const button = element();
  const form = {
    email: { value: 'team@example.test' }, password: { value: 'secret' },
    querySelector: () => button,
    addEventListener: (type, handler) => { if (type === 'submit') submit = handler; },
  };
  const context = {
    document: { getElementById: id => (id === 'login' ? form : element()) },
    window: { location: { search, origin: ORIGIN, href: `${ORIGIN}/login${search}`, replace: url => { destination = url; } } },
    URL, URLSearchParams, AbortSignal,
    fetch: async () => ({ ok: true, json: async () => ({ user: { email: 'team@example.test' } }) }),
  };
  vm.runInNewContext(source, context);
  await submit({ preventDefault() {} });
  assert.notEqual(destination, null, 'a successful sign-in navigates');
  return destination;
}

/** Where a browser actually goes for that address: it drops tabs and newlines and reads a backslash as a slash. */
const resolved = destination => new URL(destination, `${ORIGIN}/login`);

test('1.F1: after sign-in the page returns to the path the person asked for', async () => {
  assert.equal(await signInWith(`?returnTo=${encodeURIComponent('/studio/briefs/brief_1?status=pending')}`), '/studio/briefs/brief_1?status=pending');
  assert.equal(await signInWith(''), '/');
  assert.equal(await signInWith('?returnTo=%2Flogin'), '/');
  assert.equal(await signInWith('?returnTo=%2Fapi%2Fatelier%2Fweeks'), '/');
});

test('1.F1: a returnTo the browser would read as another host never leaves this host', async () => {
  const hostile = ['https://evil.example', '//evil.example', '/\\evil.example', '/\t/evil.example', '/\n/evil.example', '/\r/evil.example',
    '/\t\\evil.example', '\t//evil.example', '/%09/evil.example', '/./\t/evil.example'];
  for (const value of hostile) {
    const destination = await signInWith(`?returnTo=${encodeURIComponent(value)}`);
    assert.equal(resolved(destination).origin, ORIGIN, `${JSON.stringify(value)} sent the browser to ${destination}`);
  }
});
