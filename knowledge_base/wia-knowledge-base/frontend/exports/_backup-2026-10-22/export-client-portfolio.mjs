import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dist = resolve(root, 'dist');
const output = resolve(root, 'exports/client-portfolio.html');
const mime = { '.png': 'image/png', '.webp': 'image/webp', '.woff2': 'font/woff2', '.ttf': 'font/ttf' };
const fontUrl = 'https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Poppins:wght@400;500;600;700&display=swap';

async function download(url) {
  const response = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 Chrome/126.0.0.0 Safari/537.36' }, signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error(`Download failed: ${response.status} ${url}`);
  return response;
}

let html = await readFile(resolve(dist, 'index.html'), 'utf8');
const jsPath = html.match(/<script[^>]+src="([^"]+)"[^>]*><\/script>/)?.[1];
const cssPath = html.match(/<link[^>]+href="([^"]+\.css)"[^>]*>/)?.[1];
if (!jsPath || !cssPath) throw new Error('Run npm run build before exporting.');
let js = await readFile(resolve(dist, `.${jsPath}`), 'utf8');
let css = await readFile(resolve(dist, `.${cssPath}`), 'utf8');

// Embed the original font files so the HTML retains the typography offline.
let fonts = await (await download(fontUrl)).text();
const urls = [...new Set([...fonts.matchAll(/url\((https:[^)]+)\)/g)].map(match => match[1]))];
const fontData = await Promise.all(urls.map(async url => {
  const response = await download(url);
  return [url, `data:${response.headers.get('content-type') || 'font/woff2'};base64,${Buffer.from(await response.arrayBuffer()).toString('base64')}`];
}));
for (const [url, data] of fontData) fonts = fonts.replaceAll(url, data);
css = fonts + '\n' + css.replace(/@import\s+(?:url\([^)]*\)|"[^"]*"|'[^']*')\s*;/g, '');

// Inline every bundled image referenced by the production HTML, CSS, or JS.
const assets = [...new Set([...`${html}\n${css}\n${js}`.matchAll(/\/(?:assets|logos)\/[\w.-]+\.(?:png|webp)/g)].map(match => match[0]))];
for (const asset of assets) {
  const data = `data:${mime[extname(asset)]};base64,${(await readFile(resolve(dist, `.${asset}`))).toString('base64')}`;
  html = html.replaceAll(asset, data);
  css = css.replaceAll(asset, data);
  js = js.replaceAll(asset, data);
}

// Default to the requested blue portfolio and isolate edits from the live preview.
js = js.replace(/document\.documentElement\.dataset\.variant=[^,;]+/, 'document.documentElement.dataset.variant=new URLSearchParams(window.location.search).get("variant")!=="gold"?"blue":"gold"');
js = js.replaceAll('wia-knowledge-preview-actions-v1', 'wia-client-portfolio-html-actions-v1');
html = html.replace(/<script[^>]+src="[^"]+"[^>]*><\/script>/, '');
html = html.replace(/<link[^>]+href="[^"]+\.css"[^>]*>/, '');
html = html.replace(/<link[^>]+(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^>]*>/g, '');
html = html.replace('<title>WIA · Client Knowledge Base</title>', '<title>Client Portfolio · WIA Client Knowledge</title>');
html = html.replace('</head>', () => `<style>${css.replaceAll('</style', '<\\/style')}</style>\n</head>`);
html = html.replace('</body>', () => `<script>if (!location.hash) location.hash = 'clients';</script>\n<script type="module">${js.replaceAll('</script', '<\\/script')}</script>\n</body>`);
await mkdir(dirname(output), { recursive: true });
await writeFile(output, html);
console.log(`Created ${output}\n${(Buffer.byteLength(html) / 1024 / 1024).toFixed(2)} MB; ${fontData.length} embedded font files; ${assets.length} embedded images.`);
