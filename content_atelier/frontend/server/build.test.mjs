// 7.F2: an image built with no arguments is the real app; the mock needs an explicit build argument.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (name) => readFileSync(new URL(`../${name}`, import.meta.url), 'utf8');

test('the Dockerfile builds the API-backed app unless a build argument asks for the mock', () => {
  const dockerfile = read('Dockerfile');
  assert.match(dockerfile, /^ARG VITE_ATELIER_MODE=backend\s*$/m);
  assert.match(dockerfile, /^ENV VITE_ATELIER_MODE=\$VITE_ATELIER_MODE\s*$/m);
  // The argument is declared in the stage that runs the build, before it, and only those two values are accepted.
  const build = dockerfile.split(/^FROM /m).find((stage) => stage.startsWith('node:24-alpine AS build'));
  assert.ok(build.indexOf('ARG VITE_ATELIER_MODE') < build.indexOf('RUN npm run build'));
  assert.match(build, /backend\|mock/);
});

// 6.F3: a plain `npm run build` (the variable unset) is the real app too; only an explicit "mock" gives the demo.
test('the compose file passes the same default, and App.tsx gives the mock only for an explicit "mock"', () => {
  assert.match(read('docker-compose.yml'), /VITE_ATELIER_MODE: \$\{VITE_ATELIER_MODE:-backend\}/);
  assert.match(read('src/App.tsx'), /VITE_ATELIER_MODE === 'mock' \? <MockApp \/> : <AppRoutes \/>/);
});
