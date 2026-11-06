import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NO_FILTERS, callLabel, clock, dateLine, documentQuery, filterCount, inclusionLine, pageRange, readFilters, writeFilters } from './documents';

const read = (query: string) => readFilters(new URLSearchParams(query));

test('1.F3: the filters come from the URL, and a value that is not one of the known ones is ignored', () => {
  const filters = read('source_type=zoom&call_type=client_1to1&included=false&extraction_status=failed&date_state=undated&client_id=client_maple&q=%20follow-up%20&from=2026-01-01&to=2026-03-31&limit=100&offset=100');
  assert.deepEqual(filters, { source_type: 'zoom', call_type: 'client_1to1', included: 'false', extraction_status: 'failed', date_state: 'undated', client_id: 'client_maple',
    q: 'follow-up', needs_review: '', from: '2026-01-01', to: '2026-03-31', limit: 100, offset: 100 });
  assert.deepEqual(read('source_type=email&call_type=sales&included=maybe&extraction_status=x&date_state=y&from=2026-02-30&to=tomorrow&limit=7&offset=-3&needs_review=false'), NO_FILTERS);
  assert.deepEqual(read(''), NO_FILTERS);
});

test('1.F3: the URL carries only what differs from the plain list, and reads back to the same filters', () => {
  assert.equal(writeFilters(NO_FILTERS).toString(), '');
  const filters = { ...NO_FILTERS, call_type: 'workshop' as const, q: 'budget season', from: '2026-02-01', limit: 25, offset: 50 };
  assert.equal(writeFilters(filters).toString(), 'call_type=workshop&q=budget+season&from=2026-02-01&limit=25&offset=50');
  assert.deepEqual(read(writeFilters(filters).toString()), filters);
  assert.equal(filterCount(filters), 3);
});

test('1.F3: the request carries the filters, the date window as datetimes with an offset, and the page', () => {
  assert.deepEqual(documentQuery(NO_FILTERS), { limit: 50, offset: 0 });
  assert.deepEqual(documentQuery({ ...NO_FILTERS, source_type: 'fathom', included: 'true', client_id: 'c1', q: 'ads', from: '2026-01-01', to: '2026-03-31', limit: 200, offset: 400 }),
    { source_type: 'fathom', included: true, client_id: 'c1', q: 'ads', from: '2026-01-01T00:00:00Z', to: '2026-04-01T00:00:00Z', limit: 200, offset: 400 });
});

test('1.F3: a document is dated with its source or explicitly undated, and excluded with its reason', () => {
  assert.equal(dateLine({ date_state: 'dated', occurred_at: '2026-03-04T15:00:00Z', date_source: 'file_name' }), '4 Mar 2026, dated from file name');
  assert.equal(dateLine({ date_state: 'dated', occurred_at: '2026-03-04T15:00:00Z', date_source: null }), '4 Mar 2026, source not recorded');
  assert.match(dateLine({ date_state: 'undated', occurred_at: null, date_source: null }), /^Undated: no evidence/);
  assert.equal(inclusionLine({ included: true, exclusion_reason: null }), 'Included');
  assert.equal(inclusionLine({ included: false, exclusion_reason: 'Vendor calls are not content evidence' }), 'Excluded: Vendor calls are not content evidence');
  assert.equal(inclusionLine({ included: false, exclusion_reason: null }), 'Excluded, no reason recorded');
  assert.equal(callLabel('office_hours'), 'Office hours');
  assert.equal(callLabel(null), 'Not classified');
});

test('1.F3: the page range and a passage clock read plainly', () => {
  assert.equal(pageRange({ total: 170, offset: 50, limit: 50 }, 50), '51 to 100 of 170');
  assert.equal(pageRange({ total: 0, offset: 0, limit: 50 }, 0), 'No documents');
  assert.equal(clock(64000), '1:04');
  assert.equal(clock(3_725_000), '1:02:05');
  assert.equal(clock(null), '');
});
