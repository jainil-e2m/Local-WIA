import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
try {
  const { clientSectionHash } = await server.ssrLoadModule('/src/clientDestinations.ts');
  const { routeFromHash } = await server.ssrLoadModule('/src/App.tsx');
  const { CLIENTS, INITIAL_ACTIONS } = await server.ssrLoadModule('/src/data.ts');
  const { default: Finance } = await server.ssrLoadModule('/src/views/MoneyRevised.tsx');
  const { default: Health } = await server.ssrLoadModule('/src/views/HealthRevised.tsx');
  const props = { actions: INITIAL_ACTIONS, viewer: 'Whitney', navigate() {}, openClient() {}, openCall() {}, updateAction() {}, showEvidence() {}, notify() {}, setViewer() {}, addAction() {} };
  for (const client of CLIENTS) {
    for (const [tab, view, Component] of [['money', 'money', Finance], ['health', 'health-v2', Health]]) {
      const target = clientSectionHash(client.id, tab);
      const route = routeFromHash(`#${target}`);
      const legacy = routeFromHash(`#clients/${client.id}/${tab}`);
      for (const parsed of [route, legacy]) {
        assert.equal(parsed.view, view);
        assert.equal(parsed.clientScope, client.id);
        assert.equal(parsed.clientId, undefined, 'Must leave the client-record workspace');
      }
      const html = renderToStaticMarkup(createElement(Component, { ...props, clientId: client.id })).replaceAll('&amp;', '&').replaceAll('&#x27;', "'");
      assert.ok(html.includes(tab === 'money' ? 'Finance client filter' : 'Health client filter'));
      assert.ok(html.includes('Clear client filter'));
      assert.ok(html.includes(client.name), `${tab}: selected client is visible`);
      if (tab === 'health') {
        assert.ok(html.includes('Eight weeks, both sides'), 'Client health link opens the full detail view');
        assert.ok(!html.includes('hv-client-card'), 'Client health link skips the card picker');
      }
      // The custom selector does not render its options until opened. Other client names
      // here would therefore mean another client's actual records escaped the scope.
      for (const other of CLIENTS.filter(item => item.id !== client.id)) {
        assert.ok(!html.includes(other.name), `${tab}/${client.id} leaked ${other.name}`);
      }
    }
    assert.equal(clientSectionHash(client.id, 'meetings'), `clients/${client.id}/meetings`);
  }
  assert.equal(routeFromHash('#money').clientScope, undefined);
  assert.equal(routeFromHash('#health-v2').clientScope, undefined);
  assert.equal(routeFromHash('#money/not-a-real-client').clientScope, undefined);
  console.log(`PASS: ${CLIENTS.length} clients redirect to both main workspaces; legacy links resolve; rendered client records stay isolated; ordinary tabs and all-client routes still work.`);
} finally {
  await server.close();
}
