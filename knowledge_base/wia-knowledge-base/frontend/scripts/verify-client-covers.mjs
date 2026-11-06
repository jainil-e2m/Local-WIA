import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { CLIENT_COVERS, DEFAULT_COVER_ID, coverById, savedCoverId, saveCoverId } from '../src/clientCovers.ts';

assert.equal(CLIENT_COVERS.length, 12);
assert.equal(new Set(CLIENT_COVERS.map(cover => cover.id)).size, CLIENT_COVERS.length);
const html = await readFile(new URL('../exports/client-portfolio.html', import.meta.url), 'utf8');
for (const cover of CLIENT_COVERS) {
  const bytes = await readFile(new URL(`../public${cover.image}`, import.meta.url));
  assert.ok(bytes.length > 1000, `${cover.id}: asset exists`);
  assert.ok(html.includes(bytes.toString('base64')), `${cover.id}: full asset embedded in offline export`);
  assert.ok(!html.includes(`"${cover.image}"`), `${cover.id}: no unresolved image URL`);
}

const preferences = new Map();
Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: {
  getItem: key => preferences.get(key) ?? null,
  setItem: (key, value) => preferences.set(key, value),
} });
assert.equal(savedCoverId('new-live-client'), DEFAULT_COVER_ID);
assert.equal(savedCoverId('new-live-client', 'quiet-arches'), 'quiet-arches');
assert.equal(saveCoverId('bloom', 'sheer-light'), true);
assert.equal(savedCoverId('bloom'), 'sheer-light');
assert.equal(savedCoverId('another-live-client'), DEFAULT_COVER_ID);
assert.equal(saveCoverId('another-live-client', 'white-roses'), true);
assert.equal(savedCoverId('bloom'), 'sheer-light');
assert.equal(savedCoverId('another-live-client'), 'white-roses');
assert.equal(coverById('retired-or-unknown-cover').id, DEFAULT_COVER_ID);
preferences.set('wia-client-cover-v1:stale-client', 'retired-cover');
assert.equal(savedCoverId('stale-client'), DEFAULT_COVER_ID);
Object.defineProperty(globalThis, 'localStorage', { configurable: true, get() { throw new Error('Storage disabled'); } });
assert.equal(savedCoverId('new-live-client', 'quiet-arches'), 'quiet-arches');
assert.equal(saveCoverId('new-live-client', 'white-roses'), false);
delete globalThis.localStorage;
console.log('PASS: 12 distinct assets embedded; per-client isolation, live defaults, unknown IDs, and unavailable storage.');
