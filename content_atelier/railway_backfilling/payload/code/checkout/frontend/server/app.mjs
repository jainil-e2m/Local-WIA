import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { createSsoRouter } from './sso.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));

export function validateAuthOrigin(value, settingName = 'COMMAND_CENTER_AUTH_ORIGIN') {
  if (!value) throw new Error(`${settingName} is required. Set it to the service origin.`);
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error(`${settingName} must be an HTTP(S) origin without credentials or a path.`);
  }
  return url.origin;
}

export function createApp({ authOrigin, publicAuthOrigin, backendOrigin, backendSecret, deploymentId = randomUUID(), distDir = path.join(here, '..', 'dist'), production = true, timeoutMs = 10_000, fetcher = fetch }) {
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
  app.get('/login', (_req, res) => res.sendFile(path.join(here, 'login.html')));
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

  // Forward only the three existing Command Center auth endpoints. Accounts,
  // password checks, signing keys and login rate limiting stay in that service.
  app.use('/api/auth', express.json({ limit: '16kb' }), async (req, res) => {
    const method = { '/session': 'GET', '/login': 'POST', '/logout': 'POST' }[req.path];
    if (!method) return res.status(404).json({ error: 'Unknown authentication endpoint.' });
    if (req.method !== method) return res.set('Allow', method).status(405).json({ error: 'Method not allowed.' });
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
  app.use('/api/atelier', express.json({ limit: '64kb' }), async (req, res) => {
    if (!sessionCookie(req)) return res.status(401).json({ error: 'Sign in to Content Atelier.' });
    if (!['GET', 'POST', 'PATCH'].includes(req.method)) return res.sendStatus(405);
    if (req.method !== 'GET' && (req.headers['sec-fetch-site'] === 'cross-site' || (req.headers.origin && req.headers.origin !== `${production || req.secure ? 'https' : 'http'}://${req.get('host')}`))) {
      return res.status(403).json({ error: 'Use the Content Atelier workspace.' });
    }
    const id = '[A-Za-z0-9_-]{1,140}';
    const allowed = req.method === 'GET'
      ? new RegExp(`^/(weeks(?:/${id})?|moments/${id}|transcripts/${id}|runs/${id}/comparison(?:\\.csv)?|briefs(?:/${id}(?:/(versions|export\\.json|export\\.md))?)?|angles/${id}/research)$`)
      : req.method === 'PATCH'
        ? new RegExp(`^/(angles|briefs)/${id}$`)
        : new RegExp(`^/(weeks/${id}/(runs|reassess)|jobs/${id}/retry|runs/${id}/encode|angles/${id}/(quality|decision|brief)|briefs/${id}/(answers|review|clearance|decision|revise)|search/transcripts)$`);
    const intakeAllowed = req.method === 'GET'
      ? new RegExp(`^/intake/(overview|sources/${id}|buckets/${id}|revisions/${id}/original|assets/${id}/content)$`)
      : req.method === 'POST'
        ? new RegExp(`^/intake/(refresh|complete|search|connections/(slack|fathom)/activate|jobs/${id}/retry)$`)
        : null;
    const productionAllowed = req.method === 'GET'
      ? new RegExp('^/(calendar(?:/config)?|packs(?:/' + id + '(?:/production)?)?)$')
      : req.method === 'PATCH' ? new RegExp('^/calendar/' + id + '$')
      : new RegExp('^/(packs/' + id + '/(decision|schedule)|briefs/' + id + '/pack|calendar/' + id + '/cancel)$');
    if (!allowed.test(req.path) && !intakeAllowed?.test(req.path) && !productionAllowed.test(req.path)) return res.sendStatus(404);
    const params = new URLSearchParams(req.url.split('?')[1] || '');
    if (params.size) {
      const keys = req.path === '/calendar' ? ['from','to','status','cursor'] :
        ['/briefs','/packs'].includes(req.path) ? ['week_id','status','limit','offset'] : [];
      if (req.method !== 'GET' || !keys.length) return res.sendStatus(404);
      const seen = new Set();
      for (const [key,value] of params) {
        if (seen.has(key) || !keys.includes(key)) return res.sendStatus(404);
        seen.add(key);
        if (key === 'week_id' && !new RegExp('^'+id+'$').test(value) ||
            key === 'status' && !(req.path === '/calendar' ? ['active','published'] : ['pending','approved','rejected']).includes(value) ||
            ['limit','offset','cursor'].includes(key) && (!/^\d+$/.test(value) || +value > (key === 'limit' ? 100 : 1000000) || key === 'limit' && +value < 1) ||
            ['from','to'].includes(key) && (value.length > 50 || !/(Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value)))) return res.sendStatus(404);
      }
      if (req.path === '/calendar' && (!params.has('from') || !params.has('to'))) return res.sendStatus(404);
    }
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
      const upstream = await fetcher(`${storageOrigin}/storage${req.path}${query}`, {
        method: req.method, redirect: 'manual', signal: AbortSignal.timeout(timeoutMs),
        headers: { accept: 'application/json', 'content-type': 'application/json', authorization: `Bearer ${backendSecret}`, 'x-atelier-email': user.email, 'x-atelier-actor': typeof user.id === 'string' && user.id.trim() && user.id.length <= 320 ? user.id : user.email },
        ...(req.method !== 'GET' ? { body: JSON.stringify(req.body || {}) } : {}),
      });
      const csvReport = req.method === 'GET' && req.path.endsWith('/comparison.csv') && upstream.ok;
      const markdown = req.method === 'GET' && req.path.endsWith('/export.md') && upstream.ok;
      const attachment = req.method === 'GET' && /^\/intake\/assets\/[^/]+\/content$/.test(req.path) && upstream.ok;
      if (attachment) {
        if (!upstream.headers.get('content-type')?.includes('application/octet-stream')) return res.sendStatus(502);
        res.set('Content-Disposition', `attachment; filename="${req.path.split('/')[3]}"`);
        return res.status(upstream.status).type('application/octet-stream').send(Buffer.from(await upstream.arrayBuffer()));
      }
      if (upstream.status >= 300 && upstream.status < 400 || !upstream.headers.get('content-type')?.includes(markdown ? 'text/markdown' : csvReport ? 'text/csv' : 'application/json')) {
        return res.status(502).json({ error: 'Weekly backend returned an unexpected response.' });
      }
      if (csvReport) res.set('Content-Disposition', 'attachment; filename="angle-comparison.csv"');
      if (markdown) res.set('Content-Disposition', 'attachment; filename="content-brief.md"');
      return res.status(upstream.status).type(markdown ? 'text/markdown' : csvReport ? 'text/csv' : 'application/json').send(await upstream.text());
    } catch {
      return res.status(503).json({ error: 'Weekly backend or authentication is unavailable. Retry shortly.' });
    }
  });
  app.use('/api', (req, res, next) => {
    if (req.method === 'GET' && req.path === '/studio/deployment') return next();
    res.status(404).json({ error: 'Unknown API endpoint. This UI uses the saved mock workflow.' });
  });

  // The compiled mock library contains meeting-derived material. Protect the
  // assets themselves as well as index.html rather than relying on a UI guard.
  app.use(async (req, res, next) => {
    if (!sessionCookie(req)) return res.redirect(302, '/login');
    try {
      const upstream = await fetcher(`${origin}/api/auth/session`, {
        headers: headersFor(req), redirect: 'manual', signal: AbortSignal.timeout(timeoutMs),
      });
      if (upstream.status === 401) return res.redirect(302, '/login');
      if (!upstream.ok || !upstream.headers.get('content-type')?.includes('application/json')) throw new Error('Unavailable');
      const { user } = await upstream.json();
      if (!user?.email || !['team', 'client'].includes(user.role)) throw new Error('Invalid session');
      next();
    } catch {
      res.status(503).type('text/plain').send('Command Center authentication is unavailable. Please retry.');
    }
  });
  app.get('/api/studio/deployment', (_req, res) => res.json({ deploymentId }));
  app.use(express.static(distDir, { dotfiles: 'deny', index: false, cacheControl: false }));
  // Missing assets must return a 404, never the SPA HTML with a wrong MIME type.
  app.get('*', (req, res) => {
    if (path.extname(req.path)) return res.sendStatus(404);
    res.sendFile(path.join(distDir, 'index.html'));
  });
  app.use((error, _req, res, _next) => {
    res.status(error.status || 500).json({ error: error.type === 'entity.too.large' ? 'Request too large.' : 'Request could not be processed.' });
  });
  return app;
}
