import { test } from 'node:test';
import assert from 'node:assert/strict';
import { groupPacksByMonth } from './packMonths';
import { INITIAL_IDEAS } from '../data/mockData';
import { generateContentPackForIdea } from './packGenerator';

test('pack months use generation dates in IST and retain original records', () => {
  const source = INITIAL_IDEAS[0];
  const pack = generateContentPackForIdea(source);
  const boundary = { ...source, id: 'boundary', pack, briefApprovedAt: '2026-09-30T20:00:00Z', createdAt: '2026-08-01T00:00:00Z' };
  const older = { ...source, id: 'older', pack, briefApprovedAt: '2026-09-01T00:00:00Z' };
  const undated = { ...source, id: 'undated', pack, briefApprovedAt: undefined, createdAt: undefined, editorialWeek: undefined };
  const ideas = [older, boundary, undated, { ...source, pack: undefined }];
  const snapshot = JSON.stringify(ideas);
  const groups = groupPacksByMonth(ideas);
  assert.deepEqual(groups.map(group => group.key), ['2026-10', '2026-09', 'undated']);
  assert.equal(groups[0].ideas[0], boundary);
  assert.equal(groups.reduce((count, group) => count + group.ideas.length, 0), 3);
  assert.equal(JSON.stringify(ideas), snapshot);
});
