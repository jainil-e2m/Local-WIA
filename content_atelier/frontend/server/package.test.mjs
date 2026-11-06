// 0.F3: the app has its own name, and carries no model SDK (model calls are the Python backend's, through one module).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (name) => readFileSync(new URL(`../${name}`, import.meta.url), 'utf8');

test('the package is named for the app, not the template', () => {
  const manifest = JSON.parse(read('package.json'));
  assert.equal(manifest.name, 'content-atelier-app');
  assert.equal(JSON.parse(read('package-lock.json')).name, 'content-atelier-app');
});

test('no model SDK is a dependency, in the manifest or the lock file', () => {
  const manifest = JSON.parse(read('package.json'));
  const declared = Object.keys({ ...manifest.dependencies, ...manifest.devDependencies });
  assert.deepEqual(declared.filter((name) => /genai|openai|anthropic|gemini/i.test(name)), []);
  assert.doesNotMatch(read('package-lock.json'), /@google\/genai/);
});
