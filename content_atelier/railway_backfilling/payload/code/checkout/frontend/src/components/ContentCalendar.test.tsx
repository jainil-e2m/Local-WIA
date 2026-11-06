import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { ContentCalendar, buildCivilMonth, octoberDemoPosts, octoberMockPosts, packCalendarPosts } from '../testing/legacyCalendar';
import { INITIAL_IDEAS } from '../data/mockData';
import { EDITORIAL_MOCK_IDEAS } from '../data/editorialMockData';

test('October 2026 opens on Thursday with 31 real days', () => {
  const cells = buildCivilMonth({ year: 2026, month: 9 });
  assert.deepEqual(cells.slice(0, 4).map(cell => [cell.label, cell.inMonth]), [[28, false], [29, false], [30, false], [1, true]]);
  assert.equal(cells.filter(cell => cell.inMonth).length, 31);
  assert.equal(cells.length, 35);
  assert.deepEqual(cells.slice(-2).map(cell => [cell.label, cell.inMonth]), [[31, true], [1, false]]);
});
test('existing posts and generated mock packs populate October without changing workflow records', () => {
  const ideas = [...INITIAL_IDEAS, ...EDITORIAL_MOCK_IDEAS];
  const snapshot = JSON.stringify(ideas);
  const posts = octoberMockPosts(ideas);
  assert.equal(posts.length, EDITORIAL_MOCK_IDEAS.filter(idea => idea.pack).length * 5);
  assert.ok(posts.length > 0);
  assert.ok(posts.every(post => post.day >= 1 && post.day <= 31 && ideas.some(idea => idea.id === post.ideaId && idea.pack)));
  const html = renderToStaticMarkup(<ContentCalendar ideas={ideas} onSelectIdea={() => {}} />);
  assert.match(html, /October\s*2026/);
  assert.ok(!html.includes('April 2025'));
  assert.ok(html.includes('Content creators attention...'));
  assert.ok(!html.includes(' more</button>'));
  assert.equal((html.match(/line-clamp-2/g) ?? []).length, 14);
  assert.ok(!html.includes('>Content Pack</span>'));
  assert.equal(JSON.stringify(ideas), snapshot);
});

test('calendar cards show content formats and titles, without platforms or metrics', () => {
  const html = renderToStaticMarkup(<ContentCalendar ideas={INITIAL_IDEAS} onSelectIdea={() => {}} />);
  for (const format of ['Email', 'Carousel', 'Reel']) assert.ok(html.includes(`>${format}</span>`));
  assert.ok(!html.includes('>Post</span>'));
  for (const hidden of ['KLAVIYO', 'LINKEDIN', 'INSTAGRAM', '>VIDEO<', 'Impressions', 'Open Rate', '128 Saves', '1.2k Views', 'Cleared by Whitney']) assert.ok(!html.includes(hidden));
  assert.ok(html.includes('Content creators attention...'));
  assert.ok(html.includes('9:00 AM'));
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

test('October demo has fourteen postings, two or three per calendar week, stable across reloads', () => {
  const ideas = [...INITIAL_IDEAS, ...EDITORIAL_MOCK_IDEAS];
  const before = JSON.stringify(ideas);
  const posts = octoberDemoPosts(ideas);
  assert.equal(posts.length, 14);
  assert.equal(new Set(posts.map(post => post.day)).size, 14);
  const weekly = Array.from({ length: 5 }, (_, week) => posts.filter(post => Math.floor((post.day + 2) / 7) === week).length);
  assert.deepEqual(weekly, [3, 3, 3, 3, 2]);
  assert.deepEqual(octoberDemoPosts(ideas), posts);
  assert.deepEqual(octoberDemoPosts([...ideas].reverse()), posts);
  assert.ok(posts.some(post => post.id.startsWith('oct-demo')));
  assert.equal(JSON.stringify(ideas), before);
});

test('editing a publishing schedule never replaces the default fourteen-post October demo view', () => {
  const scheduled = EDITORIAL_MOCK_IDEAS.find(idea => idea.pack)!;
  const library = [...INITIAL_IDEAS, ...EDITORIAL_MOCK_IDEAS].map(idea => idea.id === scheduled.id ? { ...idea, publishingApprovedAt: '2026-10-06T00:00:00Z', scheduledAt: '2027-01-07T03:30:00Z' } : idea);
  const snapshot = JSON.stringify(library);
  const html = renderToStaticMarkup(<ContentCalendar ideas={library} onSelectIdea={() => {}} />);
  assert.match(html, /October\s*2026/);
  assert.equal((html.match(/line-clamp-2/g) ?? []).length, 14);
  assert.equal(octoberDemoPosts(library).length, 14);
  const future = renderToStaticMarkup(<ContentCalendar initialMonth={{ year: 2027, month: 0 }} ideas={library} onSelectIdea={() => {}} />);
  assert.match(future, /January\s*2027/);
  assert.ok(future.includes('4 more'));
  assert.equal(JSON.stringify(library), snapshot);
});

test('October 2025 is cleared while October 2026 retains demo posts and manual schedules', () => {
  const source = EDITORIAL_MOCK_IDEAS.find(idea => idea.pack)!;
  const library = [...INITIAL_IDEAS, ...EDITORIAL_MOCK_IDEAS].map(idea => idea.id === source.id ? { ...idea, publishingApprovedAt: '2026-10-06T00:00:00Z', scheduledAt: '2026-10-07T03:30:00Z' } : idea);
  const snapshot = JSON.stringify(library);
  const old = renderToStaticMarkup(<ContentCalendar initialMonth={{ year: 2025, month: 9 }} ideas={library} onSelectIdea={() => {}} />);
  assert.equal((old.match(/line-clamp-2/g) ?? []).length, 0);
  const current = renderToStaticMarkup(<ContentCalendar ideas={library} onSelectIdea={() => {}} />);
  assert.equal((current.match(/line-clamp-2/g) ?? []).length, 15);
  assert.ok(current.includes('4 more'));
  assert.equal(JSON.stringify(library), snapshot);
});
