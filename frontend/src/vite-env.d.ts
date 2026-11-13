/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Public navigation destination, compiled into the bundle at build time. */
  readonly VITE_CONTENT_ATELIER_URL?: string;
  /** The deployed Client Knowledge Base (its "View Here" signs in through /api/auth/knowledge-base). */
  readonly VITE_KNOWLEDGE_BASE_URL?: string;
}
