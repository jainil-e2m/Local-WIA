import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { PublishedCaptureForm, briefChannels, captureRequest, emptyCapture, type CaptureForm } from './PublishedCapture';
import type { BriefPublished, PublishedFinal, StoredBrief } from '../api/types';

const form = (change: Partial<CaptureForm> = {}): CaptureForm => ({ ...emptyCapture('email'), title: ' The question we ask ', text: ' Most of the sale happens in the first reply. ',
  published_on: '2026-10-18', ...change });
const body = (result: ReturnType<typeof captureRequest>) => (result as { body: PublishedFinal }).body;

test('L.B9: the capture request carries the channel, the final, the date, the link and one figure', () => {
  assert.deepEqual(captureRequest(form({ url: ' https://example.invalid/e/1 ', metric: 'replies', value: '14' }), '2026-10-19'), { body: {
    channel: 'email', piece: 1, title: 'The question we ask', text: 'Most of the sale happens in the first reply.', published_on: '2026-10-18',
    url: 'https://example.invalid/e/1', metrics: [{ metric: 'replies', value: '14' }] } });
  assert.equal(body(captureRequest(form({ channel: 'reel', piece: 2 }), '2026-10-19')).piece, 2);
  assert.equal(body(captureRequest(form({ piece: 2 }), '2026-10-19')).piece, 1, 'only reels are numbered');
  assert.deepEqual([body(captureRequest(form(), '2026-10-19')).url, body(captureRequest(form(), '2026-10-19')).metrics], [null, []]);
  assert.match((captureRequest(form({ channel: '' })) as { error: string }).error, /channel/);
  assert.match((captureRequest(form({ text: '  ' })) as { error: string }).error, /published text/);
  assert.match((captureRequest(form({ published_on: '' })) as { error: string }).error, /day it was published/);
  assert.match((captureRequest(form({ published_on: '2026-10-20' }), '2026-10-19') as { error: string }).error, /future/);
  assert.match((captureRequest(form({ url: 'javascript:alert(1)' }), '2026-10-19') as { error: string }).error, /http/);
  assert.match((captureRequest(form({ metric: 'replies' }), '2026-10-19') as { error: string }).error, /both/);
});

test('L.B9: the form offers the brief\'s own channels', () => {
  const v2 = { content_body: { document: { header: { channels: ['reel', 'email', 'threads'] } } } } as unknown as StoredBrief;
  assert.deepEqual(briefChannels(v2), ['reel', 'email']);
  assert.deepEqual(briefChannels({ content_body: { document: { title: 'A v1 brief' } } } as unknown as StoredBrief), ['email', 'reel', 'carousel', 'caption', 'stories']);
});

test('L.B9: a saved piece shows what was published, its figure and what changed from the brief', () => {
  const saved = { content_id: 'published_1', published_on: '2026-10-18', channel: 'email', title: 'The question we ask', status: 'confirmed', source_kind: 'approved_brief',
    angle_id: 'a', brief_id: 'b', created_by: 'giselle@example.invalid', performance: [{ date: '2026-10-18', metric: 'replies', value: '14' }],
    details: { capture: { url: 'https://example.invalid/e/1' }, edit: { before: 'Follow-up shapes which inquiries become tours.', after: 'Most of the sale happens in the first reply.' } } } as BriefPublished;
  const html = renderToStaticMarkup(<PublishedCaptureForm channels={['email', 'reel']} saved={[saved]} busy={false} error="" onSubmit={async () => true} />);
  for (const text of ['What was published from this brief', '2026-10-18 · email: The question we ask', 'recorded by giselle@example.invalid', 'replies: 14',
    'Open the published piece', 'The brief said:', 'Follow-up shapes which inquiries become tours.', 'Most of the sale happens in the first reply.', 'Record the published piece'])
    assert.ok(html.includes(text), text);
  assert.ok(!html.includes('Which reel'), 'the reel number appears only for a reel');
  const unsafe = { ...saved, details: { capture: { url: 'javascript:alert(1)' }, edit: null } } as BriefPublished;
  const plain = renderToStaticMarkup(<PublishedCaptureForm channels={['email']} saved={[unsafe]} busy={false} error="Refused" onSubmit={async () => true} />);
  assert.ok(!plain.includes('javascript:') && plain.includes('No change from the brief') && plain.includes('Refused'));
});
