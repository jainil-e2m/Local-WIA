import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { reelProduction } from './reelProduction';
import { generateContentPackForIdea } from './packGenerator';
import { INITIAL_IDEAS } from '../data/mockData';
import { EDITORIAL_MOCK_IDEAS } from '../data/editorialMockData';
import { draftPackToText, selectDraftContents } from '../stages/ideaStages';
import { IdeaDetailModal } from '../components/IdeaDetailModal';

test('generated packs persist spoken scripts and shot plans for all three reels', () => {
  for (const idea of INITIAL_IDEAS) {
    const pack = generateContentPackForIdea(idea);
    for (const reel of pack.reels) {
      assert.ok(reel.spokenScript?.includes(reel.hook));
      assert.ok(reel.spokenScript?.includes(reel.ctaText));
      assert.equal(reel.visualSequence?.length, 4);
    }
  }
});

test('mock scripts are distinct, read-aloud sentences without production instructions', () => {
  for (const idea of EDITORIAL_MOCK_IDEAS.filter(idea => idea.pack)) {
    const reels = idea.pack!.reels;
    assert.equal(new Set(reels.map(reel => reel.spokenScript)).size, 3);
    for (const reel of reels) {
      assert.ok(!reel.spokenScript!.includes('Use a fictional example'));
      assert.ok(reel.spokenScript!.split(/\s+/).length > 50);
    }
  }
});

test('legacy reels get recording copy without mutating or overwriting saved production content', () => {
  const reel = INITIAL_IDEAS.find(idea => idea.pack)!.pack!.reels[0];
  const snapshot = JSON.stringify(reel);
  assert.ok(reelProduction(reel, 0).spokenScript.includes(reel.hook));
  assert.equal(JSON.stringify(reel), snapshot);
  const saved = { ...reel, spokenScript: 'My exact recording script.', spokenScriptVersion: 2, visualSequence: [{ beat: 'Single take', direction: 'A continuous studio shot.' }] };
  assert.equal(reelProduction(saved, 0).spokenScript, saved.spokenScript);
  assert.equal(reelProduction(saved, 0).visualSequence, saved.visualSequence);
});

test('short saved scripts expand at least twofold, once, with CTA last and realistic timing', () => {
  for (const idea of [...INITIAL_IDEAS, ...EDITORIAL_MOCK_IDEAS].filter(idea => idea.pack)) {
    for (const [index, reel] of idea.pack!.reels.entries()) {
      const oldText = [reel.hook, ...reel.talkingPoints.filter(point => !point.startsWith('Use a fictional example')), reel.ctaText].join('\n\n');
      const legacy = { ...reel, spokenScript: oldText, spokenScriptVersion: undefined };
      const expanded = reelProduction(legacy, index);
      assert.ok(expanded.spokenScript.split(/\s+/).length >= oldText.split(/\s+/).length * 2);
      assert.ok(expanded.spokenScript.split('\n\n').at(-1)!.startsWith(reel.ctaText));
      assert.ok(expanded.duration.includes('words'));
      assert.equal(reelProduction({ ...legacy, ...expanded }, index).spokenScript, expanded.spokenScript);
    }
  }
});

test('reel panels and full exports place the spoken script and visuals after the CTA', () => {
  const idea = EDITORIAL_MOCK_IDEAS.find(idea => idea.pack)!;
  const pieces = selectDraftContents(idea.pack);
  for (const piece of pieces.filter(piece => piece.kind === 'reel')) {
    const labels = piece.sections.map(section => section.label);
    assert.ok(labels.indexOf('Spoken script') > labels.indexOf('Call to action'));
    assert.ok(labels.indexOf('What to show · Suggested video visuals') > labels.indexOf('Spoken script'));
    const html = renderToStaticMarkup(<IdeaDetailModal idea={idea} initialTab="pack" initialContentOrder={piece.order} onClose={() => {}} onUpdateGate={() => {}} onUpdateCta={() => {}} />);
    assert.ok(html.includes('Spoken script'));
    assert.ok(html.includes('What to show · Suggested video visuals'));
  }
  const output = draftPackToText(idea.title, pieces);
  for (const reel of idea.pack!.reels) assert.ok(output.includes(reel.spokenScript!));
});
