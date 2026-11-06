import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { DOCUMENT_DETAIL, DOCUMENT_LIST, ME_APPROVER, WAITING, seed } from '../testing/fixtures';
import { DocumentsView, DocumentView } from './DocumentsView';
import { readFilters, writeFilters, documentQuery, NO_FILTERS } from '../utils/documents';

const VIEWER = { ...ME_APPROVER, role: 'viewer', roles: ['viewer'], can: Object.fromEntries(Object.keys(ME_APPROVER.can).map(k => [k, false])) };
const LIST = { ...DOCUMENT_LIST, items: [...DOCUMENT_LIST.items, WAITING] };
const visible = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/\s+/g, ' ');

function backend(me: unknown, writes: { url: string; body: unknown }[], answer?: (url: string, body: unknown) => Response) {
  return stubFetch((url, options) => {
    if (url.endsWith('/me')) return json(me);
    if (options?.method === 'POST') {
      const body = JSON.parse(String(options.body));
      writes.push({ url, body });
      return answer ? answer(url, body) : json({});
    }
    if (url.startsWith('/api/atelier/documents/')) return json(DOCUMENT_DETAIL);
    return json(LIST);
  });
}

test('1.F6: a waiting call is marked, counted and can be listed on its own', () => {
  const text = visible(renderScreen(<DocumentsView />, { url: '/sources/documents', seed: [seed('/documents', { limit: 50, offset: 0 }, LIST)] }));
  assert.ok(text.includes('Zoom Meeting') && text.includes('Needs a call type'));
  assert.match(renderScreen(<DocumentsView />, { url: '/sources/documents', seed: [seed('/documents', { limit: 50, offset: 0 }, LIST)] }), /<option value="true">Needs a call type<\/option>/, 'listed on its own under More filters');
  const filters = readFilters(new URLSearchParams('needs_review=true'));
  assert.equal(filters.needs_review, 'true');
  assert.equal(writeFilters(filters).toString(), 'needs_review=true');
  assert.deepEqual(documentQuery(filters), { needs_review: true, limit: 50, offset: 0 });
  assert.equal(readFilters(new URLSearchParams('needs_review=maybe')).needs_review, '');
  assert.equal(writeFilters(NO_FILTERS).toString(), '');
});

test('1.F6: an editor classifies a waiting call from the list; the decision is sent with its reason and the list is read again', async t => {
  const writes: { url: string; body: unknown }[] = [];
  const network = backend(ME_APPROVER, writes, () => json({ ...DOCUMENT_DETAIL, ...WAITING, needs_review: false, classification: { call_type: 'office_hours', method: 'person' }, call_type: 'office_hours' }));
  t.after(network.restore);
  const ui = await mount(<DocumentsView />, { url: '/sources/documents' });
  t.after(() => ui.unmount());
  await ui.settle();
  const form = ui.container.querySelector('form[aria-label="Classify Zoom Meeting"]')!;
  assert.ok(form, 'only the waiting call offers the control in the list');
  assert.equal(ui.container.querySelectorAll('form[aria-label^="Classify"]').length, 1);
  const save = [...form.querySelectorAll('button')].find(b => b.textContent === 'Save the call type')!;
  assert.equal(save.disabled, true, 'a call type and a reason are both needed');
  await ui.choose(form.querySelector('select')!, 'office_hours');
  await ui.type(form.querySelector('input')!, 'Several members asked questions');
  const reads = network.calls.filter(c => c.url.startsWith('/api/atelier/documents?')).length;
  await ui.click(save);
  await ui.settle();
  assert.deepEqual(writes, [{ url: '/api/atelier/documents/t_3/classification', body: { call_type: 'office_hours', reason: 'Several members asked questions' } }]);
  assert.match(ui.text(), /Saved as Office hours, included\./);
  assert.ok(network.calls.filter(c => c.url.startsWith('/api/atelier/documents?')).length > reads, 'the list is read again');
});

test('1.F6: a refused classification says why', async t => {
  const writes: { url: string; body: unknown }[] = [];
  const network = backend(ME_APPROVER, writes, () => json({ detail: 'Gate 1 edits require an editor or approver' }, 403));
  t.after(network.restore);
  const ui = await mount(<DocumentView />, { url: '/sources/documents/t_3', pattern: '/sources/documents/:transcriptId' });
  t.after(() => ui.unmount());
  // The person's roles are read once the document is there (its body asks for them), so the control comes a read later.
  await ui.settle();
  await ui.settle();
  const form = ui.container.querySelector('form[aria-label^="Classify"]')!;
  assert.match(ui.text(), /Change the call type/);
  await ui.choose(form.querySelector('select')!, 'vendor');
  await ui.type(form.querySelector('input')!, 'A supplier');
  await ui.click([...form.querySelectorAll('button')].find(b => b.textContent === 'Save the call type')!);
  await ui.settle();
  assert.match(ui.text(), /require an editor/);
});

test('1.F6, 1.F7: a viewer sees neither the classification control nor the upload', async t => {
  const network = backend(VIEWER, []);
  t.after(network.restore);
  const ui = await mount(<DocumentsView />, { url: '/sources/documents' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /Needs a call type/);
  assert.equal(ui.container.querySelector('form[aria-label^="Classify"]'), null);
  assert.ok(![...ui.container.querySelectorAll('button')].some(b => b.textContent === 'Upload a transcript'), 'no upload button');
});

/** "Upload a transcript" in the page header opens the form in a dialog. */
async function openUpload(ui: Awaited<ReturnType<typeof mount>>) {
  await ui.click([...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Upload a transcript') ?? null);
  const dialog = ui.container.querySelector('[role="dialog"][aria-label="Upload a transcript"]');
  assert.ok(dialog, 'the dialog opened');
  return ui.container.querySelector('form[aria-label="Upload a transcript"]') as HTMLFormElement;
}

async function chooseFile(ui: Awaited<ReturnType<typeof mount>>, file: File) {
  const input = ui.container.querySelector('input[type="file"]') as HTMLInputElement;
  Object.defineProperty(input, 'files', { value: [file], configurable: true });
  await ui.tick(input);
  input.dispatchEvent(new window.Event('change', { bubbles: true }));
  await ui.settle();
}

test('1.F7: an editor uploads a Zoom transcript with its date; the result links to the document', async t => {
  const writes: { url: string; body: unknown }[] = [];
  const network = backend(ME_APPROVER, writes, (_url, body) => json({ transcript_id: 't_9', created: (body as { occurred_at: unknown }).occurred_at !== null, run_id: 'docrun_1',
    document: { ...WAITING, transcript_id: 't_9', title: 'Member review.vtt' } }));
  t.after(network.restore);
  const ui = await mount(<DocumentsView />, { url: '/sources/documents' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.equal(ui.container.querySelector('form[aria-label="Upload a transcript"]'), null, 'the form is not printed on the page');
  const form = await openUpload(ui);
  await chooseFile(ui, new File(['WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\nAlex: Hello.\n'], 'Member review.vtt', { type: 'text/vtt' }));
  await ui.type(form.querySelector('input[type="date"]') as HTMLInputElement, '2026-10-14');
  await ui.click([...form.querySelectorAll('button')].find(b => b.textContent === 'Upload')!);
  await ui.settle();
  assert.equal(writes.length, 1);
  assert.equal(writes[0].url, '/api/atelier/documents/import');
  assert.deepEqual(writes[0].body, { filename: 'Member review.vtt', content: 'WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\nAlex: Hello.\n', source_type: 'zoom', occurred_at: '2026-10-14T12:00:00Z' });
  assert.match(ui.text(), /Added: Member review\.vtt\. It is sorted and dated shortly\./);
  assert.match(ui.container.innerHTML, /href="\/sources\/documents\/t_9"/);
});

test('1.F7: a file that is not a transcript is refused before it is sent, and the server\'s reason is shown', async t => {
  const writes: { url: string; body: unknown }[] = [];
  const network = backend(ME_APPROVER, writes, () => json({ detail: 'The file could not be imported: ValueError: Refusing an empty transcript' }, 422));
  t.after(network.restore);
  const ui = await mount(<DocumentsView />, { url: '/sources/documents' });
  t.after(() => ui.unmount());
  await ui.settle();
  const form = await openUpload(ui);
  const upload = () => ui.click([...form.querySelectorAll('button')].find(b => b.textContent === 'Upload')!).then(ui.settle);
  await chooseFile(ui, new File(['%PDF'], 'call.pdf'));
  await upload();
  assert.match(ui.text(), /Choose a \.txt, \.vtt or \.webvtt file/);
  await chooseFile(ui, new File(['   '], 'blank.txt'));
  await upload();
  assert.match(ui.text(), /This file is empty/);
  assert.equal(writes.length, 0);
  await chooseFile(ui, new File(['WEBVTT\n'], 'empty.vtt'));
  await upload();
  assert.equal(writes.length, 1);
  assert.match(ui.text(), /Refusing an empty transcript/);
});
