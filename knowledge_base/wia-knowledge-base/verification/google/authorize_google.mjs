/** Loopback-only OAuth consent helper. No email/file modifications or watch registration.
 * node knowledge_base/wia-knowledge-base/verification/google/authorize_google.mjs
 * Tokens are saved only beneath frontend/.data/, excluded by frontend/.gitignore.
 */
import http from 'node:http';
import { randomBytes, createHash, timingSafeEqual } from 'node:crypto';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { config, storedTokens, storeTokens, tokenRequest, scopes, calendarScopes, directory } from './oauth_store.mjs';

const c = await config();
const calendarMode = process.argv.includes('--calendar');
const requestedScopes = calendarMode ? [...scopes, ...calendarScopes] : scopes;
let pending = null;
const report = { started_at_utc: new Date().toISOString(), callback: c.redirectUri,
  requested_scopes: requestedScopes, status: 'awaiting_user_authorization',
  credential_configuration_present: true, email_or_file_modifications: false,
  watches_registered: false };
const statusFile = path.join(directory, calendarMode ? 'calendar_authorization_status.json' : 'authorization_status.json');
const saveStatus = () => writeFile(statusFile, JSON.stringify(report, null, 2) + '\n');
const esc = s => String(s).replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const html = (res, status, title, body) => {
  res.writeHead(status, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
    'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'" });
  res.end(`<!doctype html><html><head><title>${esc(title)}</title><style>body{font:17px system-ui;max-width:720px;margin:60px auto;padding:24px;color:#16313c}a{color:#086888}li{margin:12px 0}code{background:#f0f4f5;padding:3px}</style></head><body><h1>${esc(title)}</h1>${body}</body></html>`);
};
const server = http.createServer(async (req, res) => {
  try {
    if (req.headers.host !== 'localhost:8765' && req.headers.host !== '127.0.0.1:8765') {
      res.writeHead(400); res.end('Invalid host'); return;
    }
    const url = new URL(req.url, 'http://localhost:8765');
    if (req.method !== 'GET') { res.writeHead(405); res.end(); return; }
    if (url.pathname === '/status') {
      res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify(report)); return;
    }
    if (url.pathname === '/') {
      const tokens = await storedTokens();
      const granted = new Set((tokens?.scope ?? '').split(' '));
      const connected = tokens?.client_id === c.clientId && requestedScopes.every(s => granted.has(s));
      html(res, 200, connected ? 'Google connection saved' : calendarMode ? 'Connect WIA Google Calendar' : 'Connect WIA Gmail and Drive',
        connected ? '<p>Credentials are saved locally. Return to the Codex chat for source verification.</p><p><a href="/connect">Authorise another account / reconnect</a></p>'
          : calendarMode
            ? '<p>Enable the Google Calendar API and add the read-only calendar-list and event scopes to this project, then sign in with hello@weddingindustryads.com.</p><p>This adds read-only Calendar access and retains the existing Gmail/Drive permissions. It does not create events, change invitations, send emails, edit files or register notifications.</p><p><a href="/connect">Continue to Google sign-in</a></p><p>Use your regular browser. The Calendar tests will run after the additional permissions are granted.</p>'
            : '<p>Sign in with the WIA Google account that owns the target mailbox and can read the client files.</p><p>This requests read-only Gmail and Drive access for Knowledge Base source testing. It does not send email, edit files, or create notifications.</p><p><a href="/connect">Continue to Google sign-in</a></p><p>Use your regular browser. If Google reports <code>org_internal</code>, the account is outside this Cloud project’s parent organisation.</p>');
      return;
    }
    if (url.pathname === '/connect') {
      if (req.headers['sec-fetch-site'] === 'cross-site') { res.writeHead(403); res.end(); return; }
      const state = randomBytes(32).toString('base64url');
      const verifier = randomBytes(48).toString('base64url');
      pending = { state, verifier, expires: Date.now() + 10 * 60 * 1000 };
      const auth = new URL('https://accounts.google.com/o/oauth2/v2/auth');
      const parameters = { client_id: c.clientId, redirect_uri: c.redirectUri,
        response_type: 'code', scope: requestedScopes.join(' '), access_type: 'offline',
        prompt: 'consent select_account', state, code_challenge_method: 'S256',
        code_challenge: createHash('sha256').update(verifier).digest('base64url') };
      for (const [k,v] of Object.entries(parameters)) auth.searchParams.set(k,v);
      res.writeHead(302, { Location: auth.href, 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' });
      res.end(); return;
    }
    if (url.pathname === '/oauth/google/callback') {
      const received = url.searchParams.get('state') ?? '';
      if (!pending || Date.now() > pending.expires || Buffer.byteLength(received) !== Buffer.byteLength(pending.state)
        || !timingSafeEqual(Buffer.from(received), Buffer.from(pending.state))) {
        html(res, 400, 'Authorisation session expired', '<p>Return to <a href="/">the connection page</a> and start again.</p>'); return;
      }
      const verifier = pending.verifier; pending = null;
      if (url.searchParams.has('error')) {
        const reason = url.searchParams.get('error');
        report.status = 'authorization_not_completed';
        report.oauth_error = /^[a-z_]+$/.test(reason) ? reason : 'authorization_error';
        await saveStatus();
        html(res, 400, 'Google authorisation not completed', '<p>No user connection was saved. Return to the Codex chat with the error shown by Google.</p>'); return;
      }
      const code = url.searchParams.get('code');
      if (!code) { html(res, 400, 'Missing authorisation code', '<p>Start again from the connection page.</p>'); return; }
      const tokens = await tokenRequest({ grant_type: 'authorization_code', code,
        client_id: c.clientId, client_secret: c.clientSecret, redirect_uri: c.redirectUri,
        code_verifier: verifier });
      await storeTokens(tokens, c);
      report.granted_scopes = (tokens.scope ?? '').split(' ').filter(Boolean);
      report.missing_scopes = requestedScopes.filter(s => !report.granted_scopes.includes(s));
      report.status = report.missing_scopes.length ? 'partial_scope_grant' : 'authorized';
      report.authorized_at_utc = new Date().toISOString();
      report.refresh_token_present = Boolean(tokens.refresh_token);
      await saveStatus();
      // Redirect immediately so the code is not retained in the visible success-page URL.
      res.writeHead(303, { Location: '/', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' });
      res.end(); console.log('Google user authorization saved. No tokens were printed.'); return;
    }
    res.writeHead(404); res.end();
  } catch(e) {
    report.status = 'authorization_handler_error'; report.error_type = e.name;
    if (e.oauthError) report.oauth_error = e.oauthError;
    if (e.httpStatus) report.http_status = e.httpStatus;
    await saveStatus();
    if (!res.headersSent) html(res, 500, 'Connection could not be saved', '<p>Return to Codex for the saved error status. No credentials are displayed here.</p>');
    else res.end();
    console.log('OAuth helper error: ' + (e.oauthError ?? e.name));
  }
});
server.on('error', error => { console.error('Local listener error: ' + error.code); process.exitCode = 1; });
await saveStatus();
server.listen(8765, '127.0.0.1', () => console.log('Local OAuth helper ready: http://localhost:8765/'));
const timeout = setTimeout(() => { server.close(); console.log('Local OAuth helper stopped after one hour.'); }, 3600000);
server.on('close', () => clearTimeout(timeout));
