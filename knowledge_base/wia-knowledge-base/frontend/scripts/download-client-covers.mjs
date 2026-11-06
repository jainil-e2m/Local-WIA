import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

// Curated decorative stock photos. Original pages and license remain in the local manifest.
const photos = [
  ['olive-still-life', '8101551', 'green-plant-in-clear-glass-vase-beside-a-jar-with-wooden-lid'],
  ['sunlit-vase', '6858594', 'creative-vase-with-dried-plant-against-white-wall'],
  ['botanical-shadow', '4256345', 'vase-with-green-plant-on-beige-background-in-sunlight'],
  ['single-stem', '8987438', 'flower-on-white-vase'],
  ['white-roses', '10363632', 'white-roses-in-a-glass-vase'],
  ['olive-window', '33797579', 'rustic-vase-with-olive-branches-by-window'],
  ['quiet-arches', '9336723', 'interior-with-white-walls'],
  ['morning-linen', '1930313', 'white-curtain'],
  ['sheer-light', '7501400', 'window-covered-with-white-curtains'],
  ['warm-plaster', '30332204', 'rough-beige-textured-surface-background'],
  ['marble-bloom', '7814435', 'flowers-by-a-marble-wall'],
];
const directory = new URL('../public/covers/', import.meta.url);
await mkdir(directory, { recursive: true });
const manifest = await Promise.all(photos.map(async ([id, photoId, slug]) => {
  const download = `https://images.pexels.com/photos/${photoId}/pexels-photo-${photoId}.jpeg?auto=compress&cs=tinysrgb&w=1800`;
  const response = await fetch(download, { signal: AbortSignal.timeout(60000) });
  if (!response.ok || !response.headers.get('content-type')?.startsWith('image/')) throw new Error(`Cannot download ${id}: ${response.status}`);
  const data = Buffer.from(await response.arrayBuffer());
  await writeFile(new URL(`${id}.jpg`, directory), data);
  console.log(`${id}: ${(data.length / 1024).toFixed(0)} KB`);
  return { id, file: `${id}.jpg`, source: `https://www.pexels.com/photo/${slug}-${photoId}/`, download, license: 'https://www.pexels.com/license/', downloadedOn: new Date().toISOString().slice(0, 10) };
}));
await writeFile(new URL('sources.json', directory), JSON.stringify(manifest, null, 2) + '\n');
console.log(`Downloaded ${manifest.length} covers to ${fileURLToPath(directory)}`);
