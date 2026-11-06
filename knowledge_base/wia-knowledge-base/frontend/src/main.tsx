import { lazy, StrictMode, Suspense } from 'react';
import { createRoot } from 'react-dom/client';
import kb from '@kb-live';
import './styles.css';
import './blue-theme.css';
import './views/ClientRecord.css';
// MVP styles come last so they override the base rules, as in the reviewed page.
import './mvp.css';

// Vite removes the annotation tooling from production builds; the HTML export keeps it for review.
const DevAgentation = import.meta.env.DEV || import.meta.env.MODE.startsWith('export')
  ? lazy(() => import('./components/DevAgentation'))
  : null;

document.documentElement.dataset.variant = new URLSearchParams(window.location.search).get('variant') === 'blue' ? 'blue' : 'gold';

const root = document.getElementById('root')!;

/** Production never falls back to the sample data: without the portfolio it says so and stops. */
function unavailable(why: string) {
  root.innerHTML = `<main style="font-family:Poppins,system-ui,sans-serif;max-width:560px;margin:18vh auto;padding:0 24px;color:#1f2a24">
    <h1 style="font-size:22px;font-weight:600;margin:0 0 8px">The client portfolio isn't available</h1>
    <p style="margin:0;color:#5b665f;line-height:1.6">${why}</p></main>`;
}

async function boot() {
  if (import.meta.env.MODE === 'portfolio') {
    const res = await fetch('/api/v1/portfolio', { credentials: 'same-origin' }).catch(() => null);
    const data = res?.ok ? await res.json().catch(() => null) : null;
    if (!data?.meta) {
      unavailable(res?.status === 404 ? 'The portfolio hasn’t been built yet. An admin runs <code>kb portfolio refresh</code>.'
        : 'The Knowledge Base can’t be reached right now. Try again in a minute.');
      return;
    }
    Object.assign(kb, data);
  }
  // In order, before any view evaluates: real KB records replace the samples, then client details edited in
  // the KB (name, aliases, logo) are layered on top.
  await import('./kbLive');
  await import('./clientDetails');
  const { default: App } = await import('./App');
  await import('./financeLive');
  createRoot(root).render(
    <StrictMode>
      <App />
      {DevAgentation && <Suspense fallback={null}><DevAgentation /></Suspense>}
    </StrictMode>
  );
}

void boot();
