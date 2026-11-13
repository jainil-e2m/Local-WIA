// Checks the client editor's storage rule: only fields that differ from the KB record are kept.
// Run: node scripts/verify-client-details.mjs (Node 22.6+ reads the .ts module directly).
import assert from 'node:assert/strict';
import { NOT_EXTRACTED, blank, overrideFrom } from '../src/clientOverride.ts';

const kb = {
  name: 'Dos Palomas Ranch', aliases: ['Dos Palomas'], category: NOT_EXTRACTED, location: 'Boerne, Texas', owner: '', lifecycle: 'Active',
  engagements: [{ type: 'ELEVATE Clients', start: null }], hasLogo: true, tint: '#f6f7f4',
};
// What the editor opens with when nothing was edited: "Not extracted yet" shows as an empty field.
const untouched = () => ({
  name: kb.name, aliases: [...kb.aliases], category: blank(kb.category), location: blank(kb.location), owner: kb.owner, lifecycle: kb.lifecycle,
  engagements: kb.engagements.map(e => ({ ...e })), logo: { kind: 'extracted' }, logoScale: 1, logoTint: kb.tint,
});
const edit = patch => overrideFrom(kb, { ...untouched(), ...patch });

assert.deepEqual(edit({}), {}, 'nothing edited, nothing stored');
assert.equal(blank(NOT_EXTRACTED), '', 'the placeholder text is not a value');
assert.deepEqual(edit({ category: '  ' }), {}, 'leaving "Not extracted yet" empty stores nothing');
assert.deepEqual(edit({ category: ' Wedding venue ' }), { category: 'Wedding venue' }, 'a typed category is stored, trimmed');
assert.deepEqual(edit({ location: '' }), { location: '' }, 'clearing a real value is an edit');
assert.deepEqual(edit({ name: 'Dos Palomas Ranch ' }), {}, 'whitespace-only change is not an edit');
assert.deepEqual(edit({ name: 'Dos Palomas Events' }), { name: 'Dos Palomas Events' });
assert.deepEqual(edit({ aliases: ['Dos Palomas', 'DPR', 'DPR', 'dos palomas ranch'] }), { aliases: ['Dos Palomas', 'DPR'] }, 'aliases deduped, the name itself dropped');
assert.deepEqual(edit({ owner: 'Carmen', lifecycle: 'Onboarding' }), { owner: 'Carmen', lifecycle: 'Onboarding' });
const dated = [{ type: 'Elevate', start: '2026-01-06' }];
assert.deepEqual(edit({ engagements: dated }), { engagements: dated });
assert.deepEqual(edit({ engagements: [...dated, { type: ' ', start: '' }] }), { engagements: dated }, 'blank engagement rows are dropped');
assert.deepEqual(edit({ logo: { kind: 'none' } }), { logoRemoved: true }, 'hiding an extracted logo is stored');
assert.deepEqual(overrideFrom({ ...kb, hasLogo: false }, { ...untouched(), logo: { kind: 'none' } }), {}, 'no logo to hide, nothing stored');
assert.deepEqual(edit({ logo: { kind: 'none' }, logoScale: 1.4, logoTint: '#26303f' }), { logoRemoved: true }, 'display settings ignored without a logo');
assert.deepEqual(edit({ logoScale: 1.25, logoTint: '#f6ecea' }), { logoScale: 1.25, logoTint: '#f6ecea' });
// Edit, then put every field back: the override must be empty again (that is what removes it from storage).
assert.deepEqual(edit({ ...untouched() }), {}, 'reverting every field leaves nothing stored');

console.log('Client details storage rule: all checks passed.');
