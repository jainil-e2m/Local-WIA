import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { ContentCalendar, buildCivilMonth, octoberDemoPosts, octoberMockPosts, packCalendarPosts } from '../testing/legacyCalendar';
import { INITIAL_IDEAS } from '../data/mockData';
import { EDITORIAL_MOCK_IDEAS } from '../data/editorialMockData';
import { FATHOM_WEEKLY_ANGLES } from '../data/fathomWeeklyAngles';

const currentIdea = FATHOM_WEEKLY_ANGLES[0];
const scheduledCurrentIdea = { ...currentIdea, pack: currentIdea.mockContentPack!, publishingApprovedAt: '2026-10-20T00:00:00Z', scheduledAt: '2026-10-21T03:30:00Z' };

test('October 2026 opens on Thursday with 31 real days', () => {
  const cells = buildCivilMonth({ year: 2026, month: 9 });
  assert.deepEqual(cells.slice(0, 4).map(cell => [cell.label, cell.inMonth]), [[28, false], [29, false], [30, false], [1, true]]);
  assert.equal(cells.filter(cell => cell.inMonth).length, 31);
  assert.equal(cells.length, 35);
  assert.deepEqual(cells.slice(-2).map(cell => [cell.label, cell.inMonth]), [[31, true], [1, false]]);
});
test('unscheduled mock packs leave October empty without changing workflow records', () => {
  const ideas = [...INITIAL_IDEAS, ...EDITORIAL_MOCK_IDEAS];
  const snapshot = JSON.stringify(ideas);
  const html = renderToStaticMarkup(<ContentCalendar ideas={ideas} onSelectIdea={() => {}} />);
  assert.match(html, /October\s*2026/);
  assert.equal((html.match(/line-clamp-2/g) ?? []).length, 0);
  assert.ok(!html.includes('Content creators attention...'));
  assert.deepEqual(octoberDemoPosts(ideas), []);
  assert.equal(JSON.stringify(ideas), snapshot);
});
test('calendar cards show scheduled content titles without platforms or metrics', () => {
  const html = renderToStaticMarkup(<ContentCalendar ideas={[scheduledCurrentIdea]} onSelectIdea={() => {}} />);
  assert.ok(html.includes(renderToStaticMarkup(<span>{scheduledCurrentIdea.pack.email.subjectLines[0]}</span>).slice(6, -7)));
  assert.ok(html.includes('>Email</span>'));
  assert.ok(html.includes('4 more'));
  for (const hidden of ['KLAVIYO', 'LINKEDIN', 'INSTAGRAM', 'Impressions', 'Open Rate', '128 Saves', '1.2k Views']) assert.ok(!html.includes(hidden));
  assert.ok(html.includes('09:00 IST'));
});
test('scheduled packs produce only Email, Carousel and Reel with individual titles', () => {
  const idea = EDITORIAL_MOCK_IDEAS.find(item => item.pack)!;
  const posts = packCalendarPosts(idea, 10, '09:30 IST');
  assert.deepEqual(posts.map(post => post.channel), ['Email', 'Carousel', 'Reel', 'Reel', 'Reel']);
  assert.equal(new Set(posts.map(post => post.id)).size, 5);
  assert.equal(posts[0].title, idea.pack!.email.subjectLines[0]);
  assert.equal(posts[1].title, idea.pack!.carousel.title);
  assert.equal(posts[2].title, idea.pack!.reels[0].angleTitle);
  assert.ok(posts.every(post => post.ideaId === idea.id && post.day === 10 && post.time === '09:30 IST'));
});
test('explicitly scheduled mocks are not duplicated as historical demo entries', () => {
  const idea = EDITORIAL_MOCK_IDEAS.find(item => item.pack)!;
  assert.equal(octoberMockPosts([{ ...idea, scheduledAt: '2026-10-10T04:00:00Z' }]).length, 0);
});

test('daily previews have uniform height and extra-content links are centered below', () => {
  const scheduled = EDITORIAL_MOCK_IDEAS.find(idea => idea.pack)!;
  const html = renderToStaticMarkup(<ContentCalendar initialMonth={{ year: 2026, month: 9 }} ideas={[{ ...scheduled, publishingApprovedAt: '2026-10-01T00:00:00Z', scheduledAt: '2026-10-10T04:00:00Z' }]} onSelectIdea={() => {}} />);
  const cards = html.match(/<button[^>]*class="[^"]*h-\[72px\][^"]*"[\s\S]*?<\/button>/g) ?? [];
  assert.ok(cards.length > 0);
  assert.equal(cards.length, (html.match(/line-clamp-2/g) ?? []).length);
  assert.ok(cards.every(card => card.includes('flex-col') && card.includes('overflow-hidden')));
  const moreLinks = html.match(/<div class="flex justify-center pt-0\.5"><button[^>]*aria-label="Show \d+ more content items[^>]*>[\s\S]*?<\/button><\/div>/g) ?? [];
  assert.ok(moreLinks.length > 0);
  assert.equal(moreLinks.length, (html.match(/aria-label="Show \d+ more content items/g) ?? []).length);
  assert.ok(html.includes('atelier-calendar-cell min-h-[128px]'));
  assert.ok(moreLinks.every(link => link.includes('leading-[14px]')));
  assert.ok(moreLinks.every(link => link.includes('w-full rounded-full') && link.includes('text-center')));
});

test('sample postings stay absent across reloads and record ordering', () => {
  const ideas = [...INITIAL_IDEAS, ...EDITORIAL_MOCK_IDEAS];
  const before = JSON.stringify(ideas);
  assert.deepEqual(octoberDemoPosts(ideas), []);
  assert.deepEqual(octoberDemoPosts([...ideas].reverse()), []);
  assert.equal(JSON.stringify(ideas), before);
});
test('moving a current-week schedule moves its calendar postings without demo replacements', () => {
  const library = [{ ...scheduledCurrentIdea, scheduledAt: '2027-01-07T03:30:00Z' }];
  const snapshot = JSON.stringify(library);
  const html = renderToStaticMarkup(<ContentCalendar ideas={library} onSelectIdea={() => {}} />);
  assert.equal((html.match(/line-clamp-2/g) ?? []).length, 0);
  const future = renderToStaticMarkup(<ContentCalendar initialMonth={{ year: 2027, month: 0 }} ideas={library} onSelectIdea={() => {}} />);
  assert.match(future, /January\s*2027/);
  assert.equal((future.match(/line-clamp-2/g) ?? []).length, 1);
  assert.ok(future.includes('4 more'));
  assert.equal(JSON.stringify(library), snapshot);
});
test('only current-week saved schedules appear and older scheduled mocks stay hidden', () => {
  const previous = EDITORIAL_MOCK_IDEAS.find(idea => idea.pack)!;
  const library = [scheduledCurrentIdea, { ...previous, publishingApprovedAt: '2026-10-06T00:00:00Z', scheduledAt: '2026-10-07T03:30:00Z' }];
  const snapshot = JSON.stringify(library);
  const old = renderToStaticMarkup(<ContentCalendar initialMonth={{ year: 2025, month: 9 }} ideas={library} onSelectIdea={() => {}} />);
  assert.equal((old.match(/line-clamp-2/g) ?? []).length, 0);
  const current = renderToStaticMarkup(<ContentCalendar ideas={library} onSelectIdea={() => {}} />);
  assert.equal((current.match(/line-clamp-2/g) ?? []).length, 1);
  assert.ok(current.includes('4 more'));
  assert.equal(JSON.stringify(library), snapshot);
});