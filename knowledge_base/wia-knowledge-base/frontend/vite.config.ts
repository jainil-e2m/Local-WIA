import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

const live = (mode: string) => mode === 'export-live';
// 'wia' = the local dev server on real KB records (npm run dev:wia); 'export-wia' = the single-file export.
const wia = (mode: string) => mode === 'export-wia' || mode === 'wia';
// 'portfolio' = the production build (npm run build:live): data comes from GET /api/v1/portfolio at start.
const kbLive = (mode: string) => mode === 'portfolio' ? './src/kb-live.runtime.ts' : wia(mode) ? './src/kb-live.local.json' : './src/kb-live.stub.json';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // /api goes to the local KB API (uvicorn on 8010), so the Leads tab reads live figures without CORS.
  server: { hmr: { host: 'localhost' }, proxy: { '/api': 'http://127.0.0.1:8010' } },
  // Real GHL finance data is bundled only into the local live export; every other build gets an empty stub.
  // Real KB client records (src/kb-live.local.json) are bundled only into the local WIA export.
  resolve: { alias: {
    '@finance-live': fileURLToPath(new URL(live(mode) ? './src/finance-live.local.json' : './src/finance-live.stub.json', import.meta.url)),
    '@dubsado-live': fileURLToPath(new URL(live(mode) ? './src/dubsado-live.local.json' : './src/dubsado-live.stub.json', import.meta.url)),
    '@kb-live': fileURLToPath(new URL(kbLive(mode), import.meta.url)),
  } },
  // The HTML exports inline one script, so their builds keep the annotation toolbar in a single bundle.
  build: mode === 'export' || live(mode) || mode === 'export-wia'
    ? { outDir: live(mode) ? 'dist-export-live' : wia(mode) ? 'dist-export-wia' : 'dist-export', rollupOptions: { output: { codeSplitting: false } } }
    : {},
}));
