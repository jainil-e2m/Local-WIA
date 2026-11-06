import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { Rubric } from '../api/types';
import { briefDecisionRequest } from './BriefReaderV2';

/* E.X9: WIA rates briefs as well as cards. The Gate 2 decision carries the ratings on review rubric 2.3a with the version the
   form showed: optional, but every point or none (as Gate 1's card form, E.X7). */

const RUBRIC = {
  version: 'rubric-2.3a.v1', instruction: 'Rate each point.', scale: [1, 2, 3, 4, 5],
  criteria: [{ key: 'subject', name: 'WIA is the subject', text: '' }, { key: 'purpose', name: 'Strategic purpose', text: '' }],
} as unknown as Rubric;

test('E.X9: a brief decision sends no ratings unless rated, all of them with the rubric version, and refuses a partial set', () => {
  assert.deepEqual(briefDecisionRequest('h', 'approved', '', 'Ready.', '', RUBRIC, {}),
    { body: { expected_hash: 'h', decision: 'approved', reason_code: null, note: 'Ready.', author: null } });
  assert.deepEqual(briefDecisionRequest('h', 'approved', '', '', '', RUBRIC, { subject: 4 }), { error: 'Rate the brief on every rubric point, or on none.' });
  const body = briefDecisionRequest('h', 'approved', 'strong', '', '', RUBRIC, { subject: 4, purpose: 5 });
  assert.ok('body' in body);
  assert.deepEqual(body.body.rubric_ratings, { subject: 4, purpose: 5 });
  assert.equal(body.body.rubric_version, 'rubric-2.3a.v1');
  assert.deepEqual(briefDecisionRequest('h', 'rejected', '', '', ''), { error: 'Choose a reason and say why in the note.' });
});
