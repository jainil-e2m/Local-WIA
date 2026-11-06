import '../testing/setupDom';
import React, { useState } from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mount } from '../testing/dom';
import { mergeEditorialMocks } from '../data/editorialMockData';
import { advanceEditorialItem } from '../utils/editorialWorkflow';
import { approvePackForScheduling } from './utils/publishingSchedule';
import { EditorialHub } from './components/EditorialHub';

function Studio() {
  const [ideas, setIdeas] = useState(() => mergeEditorialMocks([]));
  return <EditorialHub ideas={ideas} mode="weekly" onReview={() => {}} onSwitchSection={() => {}} onAddAngle={() => {}} onSchedule={() => {}}
    onUpdateGate={(id, gate) => setIdeas(previous => previous.map(idea => idea.id === id ? advanceEditorialItem(idea, gate, '2026-10-20T06:00:00Z') : idea))}
    onApprovePack={id => setIdeas(previous => previous.map(idea => idea.id === id ? approvePackForScheduling(idea) : idea))} />;
}

test('approvals open the next stage and focus the same concept through scheduling', async () => {
  const page = await mount(<Studio />);
  try {
    const selected = page.container.querySelectorAll<HTMLElement>('[data-editorial-idea-id]')[1];
    const id = selected.dataset.editorialIdeaId!;
    const button = (label: string) => Array.from(page.container.querySelectorAll('button')).find(element => element.textContent?.includes(label))!;
    await page.click(Array.from(selected.querySelectorAll('button')).find(element => element.textContent?.includes('Approve & create brief'))!);
    for (const [stage, action] of [['briefs', 'Approve & generate pack'], ['packs', 'Approve for publishing'], ['scheduled', null]] as const) {
      assert.equal(page.container.querySelector(`#editorial-${stage}-tab`)?.getAttribute('aria-pressed'), 'true');
      const cards = page.container.querySelectorAll<HTMLElement>('[data-editorial-idea-id]');
      assert.equal(cards.length, 1);
      assert.equal(cards[0].dataset.editorialIdeaId, id);
      assert.equal(document.activeElement, cards[0]);
      if (action) await page.click(button(action));
    }
    assert.ok(page.text().includes('Awaiting scheduling'));
    await page.click(button('Show all scheduled'));
    await page.click(page.container.querySelector('#editorial-angles-tab'));
    assert.equal(page.container.querySelectorAll('[data-editorial-idea-id]').length, 3);
  } finally { await page.unmount(); }
});
