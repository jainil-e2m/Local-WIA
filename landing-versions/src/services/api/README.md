# API services

Clients for independently deployed services used by the central dashboard.

- `axios.config.ts` — shared URL normalization and Axios client factory.
- `audits.ts` — routes Technical SEO through the dashboard's authenticated
  same-origin BFF; future AI/On-Page services use their `VITE_*_AUDIT_URL`.
- `auth.ts` — same-origin client for the central dashboard's Express auth API.
