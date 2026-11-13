/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Respect an externally assigned PORT (e.g. Claude's dev-server launcher
    // picking a free port when 5173 is taken) while keeping 5173 as the
    // default for a plain `npm run dev`.
    port: Number(process.env.PORT) || 5173,
    // When a launcher pins PORT, honour it exactly. Silently drifting to some
    // other free port is how a stale URL ends up in the address bar while the
    // server is actually up somewhere else. With no explicit PORT, stay
    // forgiving so a plain `npm run dev` still works when 5173 is taken.
    strictPort: Boolean(process.env.PORT),
    host: true,
    // Auth API lives on the local Express server (`npm run dev:api`); proxying
    // keeps /api same-origin in dev so the session cookie behaves like prod.
    //
    // API_PORT exists because 8787 is a single global slot: a BFF already
    // holding it belongs to whoever started it, and a second one silently
    // fails to bind — which means your server-side changes are simply not
    // loaded while the app looks fine. Two sessions can now each run their
    // own pair. Default unchanged, so `npm run dev` needs no env at all.
    proxy: {
      "/api": `http://localhost:${process.env.API_PORT ?? 8787}`,
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      exclude: ["src/main.tsx", "src/test/**", "**/*.d.ts"],
    },
  },
});
