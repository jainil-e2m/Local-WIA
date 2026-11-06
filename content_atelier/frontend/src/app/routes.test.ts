import { test } from 'node:test';
import assert from 'node:assert/strict';
import { legacyHashTarget, navViewOf, parseStudioLink, paths } from './routes';

test('1.F1: each entity has a path, and the path round-trips', () => {
  assert.equal(paths.week('week_2026-10-05'), '/studio/angles/week_2026-10-05');
  assert.equal(paths.angle('week_1', 'angle_a'), '/studio/angles/week_1/angle_a');
  assert.equal(paths.brief('brief_1'), '/studio/briefs/brief_1');
  assert.equal(paths.studioPack('pack_1'), '/studio/packs/pack_1');
  assert.equal(paths.pack('pack_1'), '/packs/pack_1');
  assert.equal(paths.document('t_1'), '/sources/documents/t_1');
  assert.equal(paths.moments, '/moments');
  assert.equal(paths.moment('m_reply'), '/moments/m_reply');
  assert.equal(paths.intakeSource('s1'), '/sources/intake/sources/s1');
  assert.equal(paths.knownItem('item_1'), '/knowledge/known/items/item_1');
  assert.equal(paths.version('wia-kb-2026-10-20.c-1a2b3c4d'), '/knowledge/versions/wia-kb-2026-10-20.c-1a2b3c4d');
  assert.deepEqual(parseStudioLink(paths.angle('week_1', 'angle_a')), { tab: 'angles', week: 'week_1', angle: 'angle_a' });
  assert.deepEqual(parseStudioLink(paths.brief('brief_1')), { tab: 'briefs', brief: 'brief_1' });
});

test('1.F1: an identifier that is not a plain token is encoded, never read as another path', () => {
  assert.equal(paths.document('a/b?c#d'), '/sources/documents/a%2Fb%3Fc%23d');
  assert.equal(paths.moment('a/b?c#d'), '/moments/a%2Fb%3Fc%23d');
  assert.equal(parseStudioLink('/studio/briefs/a%2Fb'), null);
});

test('1.F1: links saved before the app had paths (#studio/...) still lead to the same screen', () => {
  assert.equal(legacyHashTarget('#studio/briefs/brief_1'), '/studio/briefs/brief_1');
  assert.equal(legacyHashTarget('#studio/angles/week_1/angle_a'), '/studio/angles/week_1/angle_a');
  for (const other of ['', '#', '#elsewhere', '#studio/', '#studio/briefs/a/b']) assert.equal(legacyHashTarget(other), null, other);
});

test('1.F1: a path belongs to one sidebar area', () => {
  assert.equal(navViewOf('/'), 'home');
  assert.equal(navViewOf('/home'), 'home');
  assert.equal(navViewOf('/studio/briefs/b'), 'editorial');
  assert.equal(navViewOf('/packs/p'), 'packs');
  assert.equal(navViewOf('/previous'), 'previous');
  assert.equal(navViewOf('/sources/documents/t'), 'sources');
  assert.equal(navViewOf('/knowledge/versions/v'), 'knowledge');
  assert.equal(navViewOf('/moments'), 'moments');
  assert.equal(navViewOf('/moments/m_reply'), 'moments');
  assert.equal(navViewOf('/momentsx'), null, 'only the ledger and its moments belong to it');
  assert.equal(navViewOf('/sample/moments'), null, 'the sample screens are not in this app (6.F3)');
  assert.equal(navViewOf('/elsewhere'), null);
});
