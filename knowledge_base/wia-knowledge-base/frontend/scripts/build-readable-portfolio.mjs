/** Build-time helper only. The generated HTML has no dependency on this script. */
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { stripTypeScriptTypes } from 'node:module';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import * as Lucide from 'lucide-react';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const originalExport = await readFile(resolve(root, 'exports/client-portfolio.html'), 'utf8');
const output = resolve(root, 'exports/client-portfolio-readable.html');

// Reuse the exact existing font files; there are no downloads in this builder.
const embeddedFonts = [...originalExport.matchAll(/@font-face\s*\{[^}]+\}/g)].map(match => match[0]).join('\n');
if (!embeddedFonts) throw new Error('The original standalone font package was not found.');

const image = async (path, type) => `data:${type};base64,${(await readFile(resolve(root, path))).toString('base64')}`;
const assets = {
  flower: await image('src/assets/sidebar-floral-blue.png', 'image/png'),
  logo: await image('public/logos/wia_logo.webp', 'image/webp')
};
const favicon = await image('public/logos/wia_favicon.png', 'image/png');

// Export plain, readable JSON from the original fictional records.
const dataSource = stripTypeScriptTypes(await readFile(resolve(root, 'src/data.ts'), 'utf8'));
const originalData = await import(`data:text/javascript;base64,${Buffer.from(dataSource).toString('base64')}`);
const data = Object.fromEntries(['CLIENTS', 'EVIDENCE', 'INITIAL_ACTIONS', 'CALLS', 'INVOICES', 'EVENTS', 'TEAM', 'DEMO_DATE'].map(name => [name, originalData[name]]));

// SVG markup is embedded, rather than importing an icon package at runtime.
const iconNames = [
  'ArrowLeft', 'ArrowLeftToLine', 'ArrowRight', 'ArrowUpRight', 'Bell', 'BookOpen',
  'CalendarDays', 'Check', 'CheckCheck', 'CheckCircle2', 'ChevronDown', 'ChevronLeft',
  'ChevronRight', 'CircleCheck', 'Clipboard', 'Clock3', 'Command', 'Download',
  'FileCheck2', 'FileText', 'FolderOpen', 'HeartHandshake', 'History', 'House', 'Info',
  'LayoutGrid', 'List', 'ListChecks', 'Mail', 'Menu', 'MessageSquare', 'PanelLeftClose',
  'Plug', 'Quote', 'ReceiptText', 'Search', 'ShieldCheck', 'Sparkles', 'Target',
  'UserRound', 'Users', 'Video', 'X'
];
const icons = Object.fromEntries(iconNames.map(name => [name, renderToStaticMarkup(createElement(Lucide[name], { size: 14, 'aria-hidden': true }))]));

function readableCss(input) {
  let result = '', line = '', depth = 0, quote = '', comment = false, parentheses = 0;
  const flush = () => {
    if (line.trim()) result += `${'  '.repeat(Math.max(0, depth))}${line.trim()}\n`;
    line = '';
  };
  for (let index = 0; index < input.length; index++) {
    const character = input[index], next = input[index + 1];
    if (comment) {
      line += character;
      if (character === '*' && next === '/') { line += '/'; index++; comment = false; flush(); }
      continue;
    }
    if (quote) {
      line += character;
      if (character === '\\') { line += input[++index] || ''; continue; }
      if (character === quote) quote = '';
      continue;
    }
    if (character === '/' && next === '*') { flush(); comment = true; line += '/*'; index++; continue; }
    if (character === '"' || character === "'") { quote = character; line += character; continue; }
    if (character === '(') parentheses++;
    if (character === ')') parentheses--;
    if (!parentheses && character === '{') { line += ' {'; flush(); depth++; }
    else if (!parentheses && character === '}') { flush(); depth--; line = '}'; flush(); result += '\n'; }
    else if (!parentheses && character === ';') { line += ';'; flush(); }
    else line += character === '\r' || character === '\n' ? ' ' : character;
  }
  flush();
  return result;
}

const stylesheets = [
  ['FOUNDATIONS, PORTFOLIO, CLIENT RECORDS AND DIALOGS', 'src/styles.css'],
  ['ACTION ROWS AND SHARED CLIENT ACTION LAYOUTS', 'src/views/Actions.css'],
  ['COMPACT WORKSPACE TITLE', 'src/components/WorkspaceTitle.css'],
  ['BLUE COLOUR VARIANT', 'src/blue-theme.css']
];
let css = '';
for (const [label, path] of stylesheets) {
  const source = (await readFile(resolve(root, path), 'utf8')).replace(/@import\s+(?:url\([^)]*\)|"[^"]*"|'[^']*')\s*;/g, '');
  css += `\n/* ==================== ${label} ==================== */\n\n${readableCss(source)}`;
}
css += `
/* ==================== STANDALONE DOM ADAPTATIONS ==================== */
[hidden] { display: none !important; }
.sidebar .nav-item:disabled { opacity: 1; cursor: default; }
.export-source-list { display: grid; gap: 12px; }
.export-source-list .source-card { width: 100%; }
.export-copy-text { width: 100%; min-height: 320px; padding: 16px; font: 12px/1.7 monospace; }
.sidebar-orbit { contain: layout paint; }
`;
const runtime = await readFile(resolve(root, 'scripts/portfolio-standalone/runtime.js'), 'utf8');
const safeJson = value => JSON.stringify(value, null, 2).replaceAll('<', '\\u003c');
const html = `<!doctype html>
<!--
WIA CLIENT PORTFOLIO — EDITABLE, SINGLE-FILE HANDOFF

Open this file directly in a browser. No server, npm, React, CDN, or network
connection is required. This is the restored Client Portfolio design, with the
open-action metric and source coverage retained. All six fictional records and
all client tabs are included; Attendance applies only to accelerator clients.

HOW TO MAKE VARIATIONS
1. Edit #portfolio-styles for layout, colour, typography, and responsive changes.
2. Edit renderClientCard() or the named render functions for each client tab.
3. Edit #portfolio-data for the fictional content and initial action records.
4. Leave #embedded-fonts, #portfolio-assets, and #portfolio-icons alone unless
   changing assets. Base64 blobs are isolated from the editable design code.
5. Reset local edits with localStorage.removeItem('wia-readable-portfolio-actions-v1')
   and reload. This key is separate from the live app and earlier HTML export.

SCOPE
Client Portfolio, every client-record tab, source drawers, invoice terms,
editable commitments, search, account context, alerts, and related call briefs.
Other workspace navigation items remain visible for visual context, but are
disabled because they are outside the Client Portfolio handoff.
-->
<html lang="en" data-variant="blue">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#f6f7fb">
  <meta name="description" content="Editable standalone WIA Client Portfolio and all client record tabs.">
  <title>Client Portfolio · WIA Client Knowledge</title>
  <style id="portfolio-styles">
${css}
  </style>
</head>
<body>
  <!-- The shared shell and active view are rendered into this container. -->
  <div id="app"></div>
  <noscript>This interactive client portfolio requires JavaScript enabled.</noscript>

  <!-- READABLE JAVASCRIPT: shared components, tab renderers and interactions. -->
  <script id="portfolio-runtime" type="module">
${runtime.replaceAll('</script', '<\\/script')}
  </script>

  <!-- EDITABLE RECORDS: these are fictional frontend demonstration records. -->
  <script id="portfolio-data" type="application/json">
${safeJson(data)}
  </script>

  <!-- SVG ICON LIBRARY: original Lucide shapes, without a package dependency. -->
  <script id="portfolio-icons" type="application/json">
${safeJson(icons)}
  </script>

  <!-- EMBEDDED ASSETS: isolated here to keep the editable code easy to read. -->
  <script id="portfolio-assets" type="application/json">
${safeJson(assets)}
  </script>
  <style id="embedded-fonts">
${embeddedFonts}
  </style>
  <link rel="icon" href="${favicon}">
</body>
</html>
`;

// Inline modules defer until parsing completes, so the JSON below already exists.
// There are no imports; modules also work when this file is opened via file://.
await writeFile(output, html);
console.log(`Created ${output}\n${(Buffer.byteLength(html) / 1024 / 1024).toFixed(2)} MB; plain JavaScript; ${CLIENT_TAB_COUNT(data.CLIENTS)} client tab views.`);

function CLIENT_TAB_COUNT(clients) {
  return clients.reduce((total, client) => total + (client.type === 'accelerator' ? 8 : 7), 0);
}
