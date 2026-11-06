/** Stable IDs are the persisted contract; file names and credits can change independently. */
export type CoverCategory = 'Architecture' | 'Botanical' | 'Texture';
export interface ClientCover {
  id: string;
  name: string;
  category: CoverCategory;
  image: string;
  position: string;
  source: string;
  credit: string;
}

const photographs = [
  ['olive-still-life', 'Olive still life', 'Botanical', '8101551', 'green-plant-in-clear-glass-vase-beside-a-jar-with-wooden-lid', '50% 48%', '/covers/olive-still-life.jpg'],
  ['sunlit-vase', 'Sunlit ceramic', 'Botanical', '6858594', 'creative-vase-with-dried-plant-against-white-wall', '50% 48%', '/covers/sunlit-vase.jpg'],
  ['botanical-shadow', 'Botanical shadows', 'Botanical', '4256345', 'vase-with-green-plant-on-beige-background-in-sunlight', '50% 50%', '/covers/botanical-shadow.jpg'],
  ['single-stem', 'A single stem', 'Botanical', '8987438', 'flower-on-white-vase', '50% 40%', '/covers/single-stem.jpg'],
  ['white-roses', 'White roses', 'Botanical', '10363632', 'white-roses-in-a-glass-vase', '50% 40%', '/covers/white-roses.jpg'],
  ['olive-window', 'Olive by the window', 'Botanical', '33797579', 'rustic-vase-with-olive-branches-by-window', '50% 45%', '/covers/olive-window.jpg'],
  ['quiet-arches', 'Quiet arches', 'Architecture', '9336723', 'interior-with-white-walls', '50% 42%', '/covers/quiet-arches.jpg'],
  ['morning-linen', 'Morning linen', 'Texture', '1930313', 'white-curtain', '50% 50%', '/covers/morning-linen.jpg'],
  ['sheer-light', 'Sheer light', 'Texture', '7501400', 'window-covered-with-white-curtains', '50% 50%', '/covers/sheer-light.jpg'],
  ['warm-plaster', 'Warm plaster', 'Texture', '30332204', 'rough-beige-textured-surface-background', '50% 50%', '/covers/warm-plaster.jpg'],
  ['marble-bloom', 'Marble & bloom', 'Botanical', '7814435', 'flowers-by-a-marble-wall', '50% 40%', '/covers/marble-bloom.jpg'],
] as const;

export const CLIENT_COVERS: ClientCover[] = [
  { id: 'olive-arch', name: 'Olive & arch', category: 'Architecture', image: '/covers/olive-arch.png', position: 'center', source: '', credit: 'Created for WIA with OpenAI ImageGen' },
  ...photographs.map(([id, name, category, photoId, slug, position, image]) => ({ id, name, category, image, position, source: `https://www.pexels.com/photo/${slug}-${photoId}/`, credit: 'Pexels · free stock photograph' })),
];
export const DEFAULT_COVER_ID = 'olive-arch';
export const coverById = (id?: string) => CLIENT_COVERS.find(cover => cover.id === id) || CLIENT_COVERS[0];

// One key per stable client ID avoids overwriting another client's selection.
// A live service can hydrate Client.coverId and persist the same ID through its client update endpoint.
const storageKey = (clientId: string) => `wia-client-cover-v1:${clientId}`;
export function savedCoverId(clientId: string, fallback?: string): string {
  try { return coverById(localStorage.getItem(storageKey(clientId)) || fallback).id; }
  catch { return coverById(fallback).id; }
}
export function saveCoverId(clientId: string, coverId: string): boolean {
  try { localStorage.setItem(storageKey(clientId), coverById(coverId).id); return true; }
  catch { return false; }
}
