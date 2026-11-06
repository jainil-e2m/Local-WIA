import axios from "axios";

/**
 * Normalize public service URLs so path concatenation never produces `//`.
 *
 * Currently unused: every audit service now resolves to a literal same-origin
 * BFF path, so nothing reads a browser-visible URL that would need normalizing.
 * Kept for the next service onboarded before it moves behind the proxy.
 */
export const normalizeBaseUrl = (value: string | undefined) =>
  (value ?? "").trim().replace(/\/+$/, "");

/** Create a consistent client for one independently deployed service. */
export function createApi(baseURL: string) {
  const api = axios.create({
    baseURL,
    timeout: 10_000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (import.meta.env.DEV) {
        console.error("[api]", error?.config?.url, error?.response?.status ?? error.message);
      }
      return Promise.reject(error);
    },
  );

  return api;
}
