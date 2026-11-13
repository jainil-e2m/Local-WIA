import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import prettier from "eslint-config-prettier";

export default tseslint.config(
  // Ignore build output and generated files
  { ignores: ["dist", "coverage", "node_modules"] },

  // Base JS + TypeScript recommended rules for all source files
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      // SOP §3.2: console.log warns in dev, error in prod (warn|error allowed)
      "no-console": ["warn", { allow: ["warn", "error"] }],
      // SOP §3.2: flag unused variables (allow leading-underscore opt-out)
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },

  // Config files run in Node — allow Node globals, relax browser-only rules
  {
    files: ["*.{js,ts}", "vite.config.ts"],
    languageOptions: { globals: globals.node },
  },

  // shadcn/ui primitives intentionally export a component plus its `variants`
  // helper from one file — the Fast Refresh rule doesn't apply to them.
  {
    files: ["src/components/ui/**/*.{ts,tsx}"],
    rules: { "react-refresh/only-export-components": "off" },
  },

  // Keep Prettier authoritative for formatting — must be last
  prettier,
);
