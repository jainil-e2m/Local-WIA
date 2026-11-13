import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// --live builds the LOCAL-ONLY export with real GHL finance data (never share it).
const live = process.argv.includes('--live');
// --wia builds the LOCAL-ONLY export with real KB client records from the intake test (never share it).
const wia = process.argv.includes('--wia');
const dist = resolve(root, live ? 'dist-export-live' : wia ? 'dist-export-wia' : 'dist-export');
const output = resolve(root, live ? 'exports/client-portfolio.local.html' : wia ? 'exports/client-portfolio-wia.html' : 'exports/client-portfolio.html');
const mime = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.woff2': 'font/woff2', '.ttf': 'font/ttf' };
const fontUrl = 'https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Poppins:wght@400;500;600;700&display=swap';

async function download(url) {
  const response = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 Chrome/126.0.0.0 Safari/537.36' }, signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error(`Download failed: ${response.status} ${url}`);
  return response;
}

let html = await readFile(resolve(dist, 'index.html'), 'utf8');
const jsPath = html.match(/<script[^>]+src="([^"]+)"[^>]*><\/script>/)?.[1];
const cssPath = html.match(/<link[^>]+href="([^"]+\.css)"[^>]*>/)?.[1];
if (!jsPath || !cssPath) throw new Error('Run npm run export (it builds with the annotation toolbar first).');
let js = await readFile(resolve(dist, `.${jsPath}`), 'utf8');
let css = await readFile(resolve(dist, `.${cssPath}`), 'utf8');

// Embed the original font files so the HTML retains the typography offline.
let fonts;
let fontCount;
try {
  fonts = await (await download(fontUrl)).text();
  const urls = [...new Set([...fonts.matchAll(/url\((https:[^)]+)\)/g)].map(match => match[1]))];
  const fontData = await Promise.all(urls.map(async url => {
    const response = await download(url);
    return [url, `data:${response.headers.get('content-type') || 'font/woff2'};base64,${Buffer.from(await response.arrayBuffer()).toString('base64')}`];
  }));
  for (const [url, data] of fontData) fonts = fonts.replaceAll(url, data);
  fontCount = fontData.length;
} catch (error) {
  // Rebuilding offline can reuse only the font faces from the previous self-contained export.
  const previous = await readFile(output, 'utf8').catch(() => '');
  const faces = [...previous.matchAll(/@font-face\s*\{[^}]*\}/g)].map(match => match[0]).filter(face => /url\(["']?data:/.test(face));
  if (!faces.length) throw error;
  fonts = faces.join('\n');
  fontCount = faces.length;
  console.log('Font download unavailable; reusing embedded fonts from the existing export.');
}
css = fonts + '\n' + css.replace(/@import\s+(?:url\([^)]*\)|"[^"]*"|'[^']*')\s*;/g, '');

// Inline every bundled image referenced by the production HTML, CSS, or JS.
const assets = [...new Set([...`${html}\n${css}\n${js}`.matchAll(/\/(?:assets|logos|covers)\/[\w.-]+\.(?:png|webp|jpe?g)/g)].map(match => match[0]))];
for (const asset of assets) {
  const data = `data:${mime[extname(asset)]};base64,${(await readFile(resolve(dist, `.${asset}`))).toString('base64')}`;
  html = html.replaceAll(asset, data);
  css = css.replaceAll(asset, data);
  js = js.replaceAll(asset, data);
}

// Default to the requested blue portfolio and isolate edits from the live preview.
js = js.replace(/document\.documentElement\.dataset\.variant=[^,;]+/, 'document.documentElement.dataset.variant=new URLSearchParams(window.location.search).get("variant")!=="gold"?"blue":"gold"');
js = js.replaceAll('wia-knowledge-preview-actions-v2', live ? 'wia-client-portfolio-local-actions-v2' : wia ? 'wia-client-portfolio-wia-actions-v2' : 'wia-client-portfolio-html-actions-v2');
html = html.replace(/<script[^>]+src="[^"]+"[^>]*><\/script>/, '');
html = html.replace(/<link[^>]+href="[^"]+\.css"[^>]*>/, '');
html = html.replace(/<link[^>]+(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^>]*>/g, '');
html = html.replace('<title>WIA · Client Knowledge Base</title>', live ? '<title>LOCAL · real finance data · WIA Client Knowledge</title>' : wia ? '<title>LOCAL · real client data · WIA Client Knowledge</title>' : '<title>Client Portfolio · WIA Client Knowledge</title>');
html = html.replace('</head>', () => `<style>${css.replaceAll('</style', '<\\/style')}</style>\n</head>`);
html = html.replace('</body>', () => `<script>if (!location.hash) location.hash = 'clients';</script>\n<script type="module">${js.replaceAll('</script', '<\\/script')}</script>\n</body>`);
await mkdir(dirname(output), { recursive: true });
await writeFile(output, html);
console.log(`Created ${output}\n${(Buffer.byteLength(html) / 1024 / 1024).toFixed(2)} MB; ${fontCount} embedded font files; ${assets.length} embedded images.`);
