import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { VIEWS } from './viewRegistry';
import { FIXTURE_COMPONENT_FILES } from '../mock/sampleViews';

/* 1.F1, 1.F4, 6.F3: every view of the real app reads stored data and has a path of its own; nothing the real app imports
   reaches the demo build, its sample screens or the built-in examples, so its bundle carries none of them. (CI's builds are
   checked by hand with a grep of dist/assets for the demo's strings; this check needs no build.) */

const src = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

function resolve(from: string, specifier: string): string | null {
  if (!specifier.startsWith('.')) return null;
  const base = path.resolve(path.dirname(from), specifier);
  for (const candidate of [base, `${base}.ts`, `${base}.tsx`, path.join(base, 'index.ts'), path.join(base, 'index.tsx')]) {
    if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  }
  return null;
}

/** Every source file reachable from these entry files by value imports (an `import type` is erased from the bundle), not
    walking into the files in `stop`. */
export function reachable(entries: string[], stop: string[] = []): Set<string> {
  const seen = new Set<string>();
  const queue = [...entries];
  while (queue.length) {
    const file = queue.pop()!;
    if (seen.has(file) || stop.includes(file)) continue;
    seen.add(file);
    const text = readFileSync(file, 'utf8');
    for (const match of text.matchAll(/(?:^|\n)\s*(import|export)\s+(type\s+)?([^'";]*?)\s*from\s+['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)|(?:^|\n)\s*import\s+['"]([^'"]+)['"]/g)) {
      if (match[2]) continue;
      const target = resolve(file, match[4] ?? match[5] ?? match[6]);
      if (target) queue.push(target);
    }
  }
  return seen;
}

const relative = (file: string) => path.relative(src, file).split(path.sep).join('/');

test('6.F3: nothing the real app imports reaches the demo build, the sample screens or the examples', () => {
  // The real app is main.tsx with App.tsx's real branch, the routes (the build drops App.tsx's demo branch).
  const entries = [path.join(src, 'main.tsx'), path.join(src, 'app', 'AppRoutes.tsx')];
  const files = [...reachable(entries, [path.join(src, 'App.tsx')])].map(relative);
  const fixtures = (FIXTURE_COMPONENT_FILES as readonly string[]).map(file => `components/${file}`);
  const leaked = files.filter(file => file.startsWith('mock/') || file.startsWith('data/') || fixtures.includes(file)
    || /(?:SampleDataWorkspace|SampleDataMarker|studioDeployment|mockStudioSimulation)\b/.test(file));
  // The walk must see the app, or the check proves nothing.
  assert.ok(files.includes('components/SQLBriefs.tsx') && files.includes('components/PackDetail.tsx'), 'the walk must reach the screens');
  assert.deepEqual(leaked, [], 'the real app must not import these (keep them in src/mock, reached only from src/mock/MockApp.tsx)');
});

test('6.F3: the real app has no /sample/* view, and every view has a path of its own', () => {
  const all = VIEWS.map(view => view.path);
  assert.equal(new Set(all).size, all.length);
  assert.ok(all.every(view => !view.startsWith('/sample/')));
});

test('2.F1: the real moments ledger is a view of its own and imports no examples', () => {
  const real = VIEWS.find(view => view.id === 'moments-ledger');
  assert.equal(real?.path, '/moments');
  for (const file of ['MomentsLedger.tsx', 'MomentDetail.tsx', 'ExtractionHealth.tsx']) {
    assert.ok(!(FIXTURE_COMPONENT_FILES as readonly string[]).includes(file), `${file} is a real view and must not be a fixture component`);
    const text = readFileSync(path.join(src, 'components', file), 'utf8');
    assert.ok(!/from '\.\.\/(data\/|types\/atelier|testing\/)/.test(text), `${file} imports no examples and no test fixtures`);
  }
});
