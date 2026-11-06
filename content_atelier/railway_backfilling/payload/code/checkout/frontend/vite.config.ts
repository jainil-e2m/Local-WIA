import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, loadEnv} from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'COMMAND_CENTER_');
  const authOrigin = process.env.COMMAND_CENTER_AUTH_ORIGIN || env.COMMAND_CENTER_AUTH_ORIGIN || `http://localhost:${process.env.API_PORT || 8787}`;
  const atelierProxy = process.env.ATELIER_BFF_ORIGIN || 'http://localhost:8080';
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // The browser keeps the Command Center HttpOnly cookie; no credentials are duplicated.
      proxy: { '/api/auth': { target: authOrigin }, '/api/atelier': { target: atelierProxy } },
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
    preview: { proxy: { '/api/auth': { target: authOrigin }, '/api/atelier': { target: atelierProxy } } },
  };
});
