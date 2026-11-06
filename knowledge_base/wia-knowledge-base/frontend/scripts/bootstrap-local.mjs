// Offline fallback: copy the dependency closure already installed for Content Atelier.
// Standard installs should use `npm ci` with the accompanying lockfile.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = path.resolve(root, process.argv[2] || '../../content_atelier/frontend');
const sourceLock = JSON.parse(fs.readFileSync(path.join(source, 'node_modules/.package-lock.json'), 'utf8'));
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const selected = new Set();
const queue = Object.keys({ ...manifest.dependencies, ...manifest.devDependencies }).map(name => `node_modules/${name}`);

function resolveDependency(name, from) {
  let cursor = path.posix.dirname(from);
  const candidates = [`${from}/node_modules/${name}`];
  while (cursor && cursor !== '.') {
    if (!cursor.endsWith('node_modules')) candidates.push(`${cursor}/node_modules/${name}`);
    cursor = path.posix.dirname(cursor);
  }
  candidates.push(`node_modules/${name}`);
  return candidates.find(key => sourceLock.packages[key] && fs.existsSync(path.join(source, key, 'package.json')));
}

while (queue.length) {
  const key = queue.shift();
  if (selected.has(key)) continue;
  if (!sourceLock.packages[key]) throw new Error(`Installed dependency unavailable: ${key}`);
  const meta = JSON.parse(fs.readFileSync(path.join(source, key, 'package.json'), 'utf8'));
  selected.add(key);
  for (const [name, version] of Object.entries({ ...meta.dependencies, ...meta.optionalDependencies, ...meta.peerDependencies })) {
    const resolved = resolveDependency(name, key);
    if (resolved) queue.push(resolved);
    else if (meta.dependencies?.[name] && !meta.optionalDependencies?.[name]) throw new Error(`Missing required dependency ${name}@${version} for ${key}`);
  }
}

const packages = { '': { name: manifest.name, version: manifest.version, dependencies: manifest.dependencies, devDependencies: manifest.devDependencies } };
for (const key of selected) {
  fs.cpSync(path.join(source, key), path.join(root, key), { recursive: true });
  packages[key] = sourceLock.packages[key];
}
fs.mkdirSync(path.join(root, 'node_modules/.bin'), { recursive: true });
for (const bin of ['vite', 'tsc', 'tsserver']) {
  for (const suffix of ['', '.cmd', '.ps1']) {
    const sourceBin = path.join(source, 'node_modules/.bin', bin + suffix);
    if (fs.existsSync(sourceBin)) fs.copyFileSync(sourceBin, path.join(root, 'node_modules/.bin', bin + suffix));
  }
}
// Include optional packages from the source lock in the reproducible lockfile,
// even when this platform does not install them.
for (const key of selected) {
  const entry = sourceLock.packages[key];
  for (const name of Object.keys(entry.optionalDependencies || {})) {
    const optionalKey = `node_modules/${name}`;
    if (sourceLock.packages[optionalKey]) packages[optionalKey] = sourceLock.packages[optionalKey];
  }
}
fs.writeFileSync(path.join(root, 'package-lock.json'), JSON.stringify({ name: manifest.name, version: manifest.version, lockfileVersion: 3, requires: true, packages }, null, 2) + '\n');
console.log(`Prepared ${selected.size} installed dependency packages from Content Atelier.`);
