import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createSsoRouter, localReturnTo, publicCommandCenterOrigin } from './sso.mjs';
import { DEFAULT_BODY_LIMIT, IMPORT_BODY_LIMIT, UPLOAD_BODY_LIMIT, METHODS, bodyLimitFor, isLongRead, queryAllowed, routeAllowed } from './allowlist.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
// The week's pack document as a Word file (NP.B12; backend packs/document_docx.py).
const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

export function validateAuthOrigin(value, settingName = 'COMMAND_CENTER_AUTH_ORIGIN') {
  if (!value) throw new Error(`${settingName} is required. Set it to the service origin.`);
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error(`${settingName} must be an HTTP(S) origin without credentials or a path.`);
  }
  return url.origin;
}

// A file the bundle could hold, by its type. Any other path is a page of the app, even with a dot in it (a knowledge
// version such as /knowledge/versions/wia-kb-2026-10-25.c-8ba81fcc is a page, not a file).
const ASSET = /\.(?:js|mjs|css|map|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot|json|txt|html?|xml|webmanifest|mp4|webm|pdf)$/i;
export const isAsset = pathname => ASSET.test(pathname);

export function createApp({ authOrigin, publicAuthOrigin, backendOrigin, backendSecret, distDir = path.join(here, '..', 'dist'), production = true, timeoutMs = 10_000, longReadTimeoutMs = 60_000, fetcher = fetch }) {
  const origin = validateAuthOrigin(authOrigin);
  const storageOrigin = backendOrigin ? validateAuthOrigin(backendOrigin, 'ATELIER_BACKEND_ORIGIN') : null;
  const app = express();
  app.disable('x-powered-by');
  app.set('trust proxy', 1);
  app.use((_req, res, next) => {
    res.set({
      'X-Frame-Options': 'DENY',
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'Cache-Control': 'private, no-store',
    });
    next();
  });
  app.get('/health', (_req, res) => res.type('text/plain').send('ok\n'));
  // One sign-in and one sign-out for Command Center and the Atelier (S.C1). With COMMAND_CENTER_PUBLIC_ORIGIN set (every
  // deployment sets it), signing in happens on Command Center and comes back through the PKCE hand-off (sso.mjs), so one
  // session serves both apps; /login?direct=1 keeps this host's own form (it checks the same Command Center accounts).
  const commandCenter = publicAuthOrigin ? publicCommandCenterOrigin(publicAuthOrigin, production) : null;
  app.get('/login', (req, res) => {
    if (commandCenter && req.query.direct !== '1') {
      const returnTo = typeof req.query.returnTo === 'string' ? localReturnTo(req.query.returnTo) : '/';
      return res.redirect(302, returnTo === '/' ? '/api/auth/sso/start' : `/api/auth/sso/start?returnTo=${encodeURIComponent(returnTo)}`);
    }
    res.sendFile(path.join(here, 'login.html'));
  });
  app.get('/login.js', (_req, res) => res.sendFile(path.join(here, 'login.js')));
  // Public brand asset; meeting-derived workspace assets remain protected.
  app.get('/logos/wia_favicon.png', (_req, res) => res.sendFile(path.join(distDir, 'logos', 'wia_favicon.png')));
  app.use('/api/auth/sso', createSsoRouter({ authOrigin: origin, publicAuthOrigin, production, timeoutMs, fetcher }));

  const sessionCookie = req => (req.headers.cookie || '').split(';').map(part => part.trim()).find(part => part.startsWith('wahha_session=')) || '';
  const headersFor = req => ({
    accept: 'application/json',
    cookie: sessionCookie(req),
    'x-forwarded-proto': production || req.secure ? 'https' : 'http',
    'x-forwarded-for': req.ip,
  });

  // Sign-out ends the session in both apps: Command Center revokes the token (both apps hold the same one), this host's
  // cookie is cleared here, and the browser passes through Command Center's /api/auth/signout to clear its cookie too.
  // `from=command-center` marks the second leg of a sign-out Command Center started, which ends on its sign-in page.
  app.get('/api/auth/signout', async (req, res) => {
    res.set({ 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' });
    if (sessionCookie(req)) {
      try {
        await fetcher(`${origin}/api/auth/logout`, {
          method: 'POST', headers: { ...headersFor(req), 'content-type': 'application/json' }, body: '{}',
          redirect: 'manual', signal: AbortSignal.timeout(timeoutMs),
        });
      } catch { /* The cookies are still cleared; Command Center's leg below revokes the session again. */ }
    }
    res.setHeader('Set-Cookie', `wahha_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${production ? '; Secure' : ''}`);
    if (!commandCenter) return res.redirect(302, '/login');
    res.redirect(302, req.query.from === 'command-center' ? `${commandCenter}/login` : `${commandCenter}/api/auth/signout?from=atelier`);
  });

  // Forward only the three existing Command Center auth endpoints. Accounts,
  // password checks, signing keys and login rate limiting stay in that service.
  app.use('/api/auth', express.json({ limit: '16kb' }), async (req, res) => {
    const method = { '/session': 'GET', '/login': 'POST', '/logout': 'POST' }[req.path];
    if (!method) return res.status(404).json({ error: 'Unknown authentication endpoint.' });
    if (req.method !== method) return res.set('Allow', method).status(405).json({ error: 'Method not allowed.' });
    // Every session check says how this host signs a person in, so the app's sign-in link can go straight to Command
    // Center's hand-off with the page's path (one hop, 6.F8), or to this host's own form when no public origin is set.
    if (method === 'GET') res.set('X-Atelier-Sign-In', commandCenter ? 'command-center' : 'form');
    // Reject cross-origin login/logout submissions, including login CSRF.
    if (method === 'POST' && (req.headers['sec-fetch-site'] === 'cross-site' || (req.headers.origin && req.headers.origin !== `${production || req.secure ? 'https' : 'http'}://${req.get('host')}`))) {
      return res.status(403).json({ error: 'Use the Content Atelier sign-in page.' });
    }
    try {
      const upstream = await fetcher(`${origin}/api/auth${req.path}`, {
        method,
        headers: { ...headersFor(req), 'content-type': 'application/json' },
        ...(method === 'POST' ? { body: JSON.stringify(req.body || {}) } : {}),
        redirect: 'manual',
        signal: AbortSignal.timeout(timeoutMs),
      });
      // A proxy to an HTML login/redirect is a configuration error, not auth.
      if ((upstream.status >= 300 && upstream.status < 400) || !upstream.headers.get('content-type')?.includes('application/json')) {
        return res.status(502).json({ error: 'Command Center returned an unexpected authentication response.' });
      }
      const cookies = upstream.headers.getSetCookie();
      if (cookies.length) {
        res.setHeader('Set-Cookie', cookies.map(cookie => {
          // Issue the upstream signed token for this host. Never broaden its
          // domain; separate Railway domains cannot share host-only cookies.
          let local = cookie.replace(/;\s*Domain=[^;]*/gi, '');
          if (production && !/;\s*Secure(?:;|$)/i.test(local)) local += '; Secure';
          return local;
        }));
      }
      res.status(upstream.status).type('application/json').send(await upstream.text());
    } catch {
      res.status(502).json({ error: 'Command Center authentication is unavailable. Please retry.' });
    }
  });
  // Resolve the actual session for every SQL request. Browser-supplied actor,
  // authorization and provider credentials are never forwarded to the backend.
  // The body limit is tight (64 KB); only the CSV import and the transcript upload may send more (allowlist.mjs).
  const parsers = new Map([DEFAULT_BODY_LIMIT, IMPORT_BODY_LIMIT, UPLOAD_BODY_LIMIT].map(limit => [limit, express.json({ limit })]));
  app.use('/api/atelier', (req, res, next) => (parsers.get(bodyLimitFor(req.method, req.path)) ?? parsers.get(DEFAULT_BODY_LIMIT))(req, res, next), async (req, res) => {
    if (!sessionCookie(req)) return res.status(401).json({ error: 'Sign in to Content Atelier.' });
    if (!METHODS.includes(req.method)) return res.sendStatus(405);
    if (req.method !== 'GET' && (req.headers['sec-fetch-site'] === 'cross-site' || (req.headers.origin && req.headers.origin !== `${production || req.secure ? 'https' : 'http'}://${req.get('host')}`))) {
      return res.status(403).json({ error: 'Use the Content Atelier workspace.' });
    }
    if (!routeAllowed(req.method, req.path)) return res.sendStatus(404);
    const params = new URLSearchParams(req.url.split('?')[1] || '');
    if (!queryAllowed(req.method, req.path, params)) return res.sendStatus(404);
    const query = params.size ? `?${params.toString()}` : '';
    try {
      const session = await fetcher(`${origin}/api/auth/session`, {
        headers: headersFor(req), redirect: 'manual', signal: AbortSignal.timeout(timeoutMs),
      });
      if (session.status === 401) return res.status(401).json({ error: 'Session expired.' });
      if (!session.ok || !session.headers.get('content-type')?.includes('application/json')) throw new Error('Auth unavailable');
      const { user } = await session.json();
      // This initial corpus is an internal multi-client meeting pool. Client
      // access needs explicit content scope before it can use these SQL routes.
      if (typeof user?.email !== 'string' || !user.email.trim() || user.email.length > 320 || user.role !== 'team') return res.status(403).json({ error: 'Team access is required for weekly source review.' });
      if (!storageOrigin || !backendSecret) return res.status(503).json({ error: 'Weekly storage backend is not configured.' });
      // Exports, original transcripts and attachments are large reads: they get the longer timeout, nothing else does.
      const upstream = await fetcher(`${storageOrigin}/storage${req.path}${query}`, {
        method: req.method, redirect: 'manual', signal: AbortSignal.timeout(isLongRead(req.method, req.path) ? longReadTimeoutMs : timeoutMs),
        headers: { accept: 'application/json', 'content-type': 'application/json', authorization: `Bearer ${backendSecret}`, 'x-atelier-email': user.email, 'x-atelier-actor': user.email },
        ...(req.method !== 'GET' ? { body: JSON.stringify(req.body || {}) } : {}),
      });
      const csvReport = req.method === 'GET' && req.path.endsWith('/comparison.csv') && upstream.ok;
      // Markdown: a brief's export, the week's review document (5.B14), whose 502 here was found by the N1 shakedown, and the
      // week's pack document (NP.B12, NP.F4).
      const reviewDocument = req.method === 'GET' && /^\/weeks\/[^/]+\/review\.md$/.test(req.path) && upstream.ok;
      const packDocument = req.method === 'GET' && /^\/weeks\/[^/]+\/packs\.md$/.test(req.path) && upstream.ok;
      const markdown = req.method === 'GET' && (req.path.endsWith('/export.md') || reviewDocument || packDocument) && upstream.ok;
      const attachment = req.method === 'GET' && /^\/intake\/assets\/[^/]+\/content$/.test(req.path) && upstream.ok;
      if (attachment) {
        if (!upstream.headers.get('content-type')?.includes('application/octet-stream')) return res.sendStatus(502);
        res.set('Content-Disposition', `attachment; filename="${req.path.split('/')[3]}"`);
        return res.status(upstream.status).type('application/octet-stream').send(Buffer.from(await upstream.arrayBuffer()));
      }
      // The week's pack document (NP.B12) and review document (5.B14) as Word files: binary, relayed byte for byte, and only
      // when the backend says .docx.
      const wordFile = req.method === 'GET' && upstream.ok ? /^\/weeks\/[^/]+\/(packs|review)\.docx$/.exec(req.path) : null;
      if (wordFile) {
        if (!upstream.headers.get('content-type')?.includes(DOCX)) return res.sendStatus(502);
        res.set('Content-Disposition', `attachment; filename="content-atelier-${wordFile[1]}-${req.path.split('/')[2]}.docx"`);
        return res.status(upstream.status).type(DOCX).send(Buffer.from(await upstream.arrayBuffer()));
      }
      if (upstream.status >= 300 && upstream.status < 400 || !upstream.headers.get('content-type')?.includes(markdown ? 'text/markdown' : csvReport ? 'text/csv' : 'application/json')) {
        return res.status(502).json({ error: 'Weekly backend returned an unexpected response.' });
      }
      if (csvReport) res.set('Content-Disposition', 'attachment; filename="angle-comparison.csv"');
      if (markdown) res.set('Content-Disposition', reviewDocument ? `attachment; filename="content-atelier-review-${req.path.split('/')[2]}.md"`
        : packDocument ? `attachment; filename="content-atelier-packs-${req.path.split('/')[2]}.md"` : 'attachment; filename="content-brief.md"');
      return res.status(upstream.status).type(markdown ? 'text/markdown' : csvReport ? 'text/csv' : 'application/json').send(await upstream.text());
    } catch {
      return res.status(503).json({ error: 'Weekly backend or authentication is unavailable. Retry shortly.' });
    }
  });
  // Every API this host answers is above: anything else under /api is a plain 404, whoever asks (6.F4).
  app.use('/api', (_req, res) => res.status(404).json({ error: 'Unknown API endpoint.' }));

  // The compiled bundle contains meeting-derived material. Protect the
  // assets themselves as well as index.html rather than relying on a UI guard.
  // A page asked for without a session goes to sign-in carrying its path, so a deep link survives sign-in; localReturnTo
  // accepts only a path on this host. With Command Center's public origin set, the page goes straight to its hand-off
  // (one hop, 6.F8: sso.mjs keeps the path through the round trip); otherwise to this host's form, whose login.js follows
  // it. Assets go to plain /login, so a script or image request never starts a hand-off.
  const signIn = req => {
    const page = req.method === 'GET' && !isAsset(req.path) && !req.path.startsWith('/api/');
    const returnTo = page ? localReturnTo(req.originalUrl) : '/';
    const query = returnTo === '/' ? '' : `?returnTo=${encodeURIComponent(returnTo)}`;
    return page && commandCenter ? `/api/auth/sso/start${query}` : `/login${query}`;
  };
  app.use(async (req, res, next) => {
    if (!sessionCookie(req)) return res.redirect(302, signIn(req));
    try {
      const upstream = await fetcher(`${origin}/api/auth/session`, {
        headers: headersFor(req), redirect: 'manual', signal: AbortSignal.timeout(timeoutMs),
      });
      if (upstream.status === 401) return res.redirect(302, signIn(req));
      if (!upstream.ok || !upstream.headers.get('content-type')?.includes('application/json')) throw new Error('Unavailable');
      const { user } = await upstream.json();
      if (!user?.email || !['team', 'client'].includes(user.role)) throw new Error('Invalid session');
      // The application is team-only (S.F3, R50): a client session receives no
      // index.html, bundle or fixture, only this notice.
      if (user.role !== 'team') {
        return res.status(403).type('text/plain').send('Content Atelier is available to the WIA team only. Sign in with a team account.');
      }
      next();
    } catch {
      res.status(503).type('text/plain').send('Command Center authentication is unavailable. Please retry.');
    }
  });
  app.use(express.static(distDir, { dotfiles: 'deny', index: false, cacheControl: false }));
  // Missing assets must return a 404, never the SPA HTML with a wrong MIME type.
  app.get('*', (req, res) => {
    if (isAsset(req.path)) return res.sendStatus(404);
    res.sendFile(path.join(distDir, 'index.html'));
  });
  app.use((error, _req, res, _next) => {
    res.status(error.status || 500).json({ error: error.type === 'entity.too.large' ? 'Request too large.' : 'Request could not be processed.' });
  });
  return app;
}
