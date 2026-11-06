import crypto from 'node:crypto';
import express from 'express';

const STATE_COOKIE = 'atelier_sso_state';
const COOKIE_PATH = '/api/auth/sso';
const tokenPattern = /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;
const loopback = new Set(['localhost', '127.0.0.1', '[::1]']);

export function localReturnTo(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\r\n]/.test(value)) return '/';
  try {
    const decoded = decodeURIComponent(value.split('?')[0]);
    if (decoded.startsWith('//') || /[\\\r\n]/.test(decoded)) return '/';
    const url = new URL(value, 'https://atelier.invalid');
    return url.origin === 'https://atelier.invalid' && !url.pathname.startsWith('//') && !url.pathname.startsWith('/api/auth/') && url.pathname !== '/login' ? url.pathname + url.search : '/';
  } catch { return '/'; }
}

/** Browser-bound state + server-held PKCE verifier. No session or verifier is
 * sent in a browser URL. Pending transactions expire and are consumed once.
 */
export function createSsoRouter({ authOrigin, publicAuthOrigin = authOrigin, production, fetcher = fetch, timeoutMs = 10_000, now = Date.now, lifetimeMs = 180_000, capacity = 1000 }) {
  let publicUrl;
  try {
    const url = new URL(publicAuthOrigin);
    if (!url.username && !url.password && url.pathname === '/' && !url.search && !url.hash && (url.protocol === 'https:' || (url.protocol === 'http:' && !production && loopback.has(url.hostname)))) publicUrl = url;
  } catch { /* Direct sign-in remains available when the browser origin is unset. */ }
  const transactions = new Map();
  const router = express.Router();
  router.use((_req, res, next) => {
    res.set({ 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' });
    next();
  });
  const stateCookie = (state, maxAge) => `${STATE_COOKIE}=${state}; Path=${COOKIE_PATH}; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${production ? '; Secure' : ''}`;
  const readState = req => (req.headers.cookie || '').split(';').map(part => part.trim()).find(part => part.startsWith(`${STATE_COOKIE}=`))?.slice(STATE_COOKIE.length + 1);
  const purge = () => { for (const [state, entry] of transactions) if (entry.expiresAt <= now()) transactions.delete(state); };

  router.get('/start', (req, res) => {
    if (!publicUrl) return res.status(503).type('text/plain').send('Set COMMAND_CENTER_PUBLIC_ORIGIN to the public HTTPS Command Center origin to enable automatic sign-in.');
    purge();
    const previous = readState(req);
    if (previous) transactions.delete(previous);
    if (transactions.size >= capacity) return res.status(503).type('text/plain').send('Sign-in is busy. Please retry shortly.');
    const state = crypto.randomBytes(32).toString('base64url');
    const verifier = crypto.randomBytes(48).toString('base64url');
    const callback = new URL('/api/auth/sso/callback', `${production || req.secure ? 'https' : 'http'}://${req.get('host')}`).href;
    transactions.set(state, { verifier, callback, returnTo: localReturnTo(req.query.returnTo), expiresAt: now() + lifetimeMs });
    const authorize = new URL('/api/auth/content-atelier/authorize', publicUrl.origin);
    authorize.searchParams.set('redirect_uri', callback);
    authorize.searchParams.set('state', state);
    authorize.searchParams.set('code_challenge', crypto.createHash('sha256').update(verifier).digest('base64url'));
    authorize.searchParams.set('code_challenge_method', 'S256');
    res.setHeader('Set-Cookie', stateCookie(state, Math.floor(lifetimeMs / 1000)));
    res.redirect(302, authorize.href);
  });

  router.get('/callback', async (req, res) => {
    purge();
    const { state, code } = req.query;
    const browserState = readState(req);
    if (typeof state !== 'string' || !browserState || state !== browserState || typeof code !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(code)) {
      return res.status(400).type('text/plain').send('Sign-in could not be verified. Open Content Atelier from Command Center again.');
    }
    const transaction = transactions.get(state);
    if (!transaction) return res.status(400).type('text/plain').send('Sign-in expired or was already completed. Open Content Atelier again.');
    transactions.delete(state);
    res.setHeader('Set-Cookie', stateCookie('', 0));
    try {
      const upstream = await fetcher(`${authOrigin}/api/auth/content-atelier/exchange`, {
        method: 'POST', redirect: 'manual', signal: AbortSignal.timeout(timeoutMs),
        headers: { accept: 'application/json', 'content-type': 'application/json' },
        body: JSON.stringify({ code, redirect_uri: transaction.callback, code_verifier: transaction.verifier }),
      });
      if (!upstream.ok || !upstream.headers.get('content-type')?.includes('application/json')) throw new Error('Exchange failed');
      const { sessionToken, expiresIn, user } = await upstream.json();
      if (typeof sessionToken !== 'string' || sessionToken.length > 4096 || !tokenPattern.test(sessionToken) || !Number.isFinite(expiresIn) || expiresIn < 1 || typeof user?.email !== 'string' || typeof user.name !== 'string' || !['team', 'client'].includes(user.role)) throw new Error('Invalid session');
      const cookie = `wahha_session=${encodeURIComponent(sessionToken)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${Math.min(Math.floor(expiresIn), 604800)}${production ? '; Secure' : ''}`;
      res.setHeader('Set-Cookie', [stateCookie('', 0), cookie]);
      res.redirect(302, transaction.returnTo);
    } catch {
      res.status(502).type('text/plain').send('Command Center sign-in could not be completed. Open Content Atelier from Command Center again, or use /login.');
    }
  });
  return router;
}
