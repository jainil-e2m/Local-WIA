import type { KbLive } from './kbLive';

// The production build ('portfolio' mode): empty until main.tsx fills it from GET /api/v1/portfolio,
// before any view module evaluates. Other builds resolve '@kb-live' to a JSON file instead.
const kb: KbLive = {};
export default kb;
