/** Google user OAuth storage for local read-only source verification. */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { parseEnv } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
export const directory = path.dirname(fileURLToPath(import.meta.url));
export const root = path.resolve(directory, '../../../..');
export const tokenPath = path.join(root, 'frontend/.data/knowledge-base-google/oauth-tokens.json');
export const scopes = ['https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/drive.readonly'];
export const calendarScopes = ['https://www.googleapis.com/auth/calendar.calendarlist.readonly',
  'https://www.googleapis.com/auth/calendar.events.readonly'];
export async function config() {
  const env = parseEnv(await readFile(path.join(root, 'frontend/.env'), 'utf8'));
  const c = { clientId: env.GOOGLE_CLIENT_ID?.trim(), clientSecret: env.GOOGLE_CLIENT_SECRET?.trim(),
    redirectUri: env.GOOGLE_REDIRECT_URI?.trim() };
  if (!c.clientId || !c.clientSecret || !c.redirectUri) throw new Error('google_oauth_configuration_missing');
  if (c.redirectUri !== 'http://localhost:8765/oauth/google/callback') throw new Error('unexpected_local_callback_uri');
  return c;
}
export async function storedTokens() {
  try { return JSON.parse(await readFile(tokenPath, 'utf8')); } catch { return null; }
}
export async function storeTokens(data, c, previous = null) {
  const tokens = { ...data, refresh_token: data.refresh_token ?? previous?.refresh_token ?? null,
    scope: data.scope ?? previous?.scope ?? '', client_id: c.clientId,
    received_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + Number(data.expires_in ?? 3600) * 1000).toISOString() };
  await mkdir(path.dirname(tokenPath), { recursive: true });
  await writeFile(tokenPath, JSON.stringify(tokens, null, 2) + '\n', { mode: 0o600 });
  return tokens;
}
export async function tokenRequest(parameters) {
  const response = await fetch('https://oauth2.googleapis.com/token', { method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(parameters), redirect: 'error', signal: AbortSignal.timeout(25000) });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error('google_token_exchange_failed');
    error.oauthError = typeof data.error === 'string' ? data.error : 'unknown';
    error.httpStatus = response.status; throw error;
  }
  return data;
}
export async function accessToken() {
  const c = await config(); let tokens = await storedTokens();
  if (!tokens || tokens.client_id !== c.clientId) throw new Error('google_user_authorization_required');
  if (tokens.access_token && Date.parse(tokens.expires_at) > Date.now() + 60000) return tokens.access_token;
  if (!tokens.refresh_token) throw new Error('google_reauthorization_required_no_refresh_token');
  const data = await tokenRequest({ grant_type: 'refresh_token', refresh_token: tokens.refresh_token,
    client_id: c.clientId, client_secret: c.clientSecret });
  tokens = await storeTokens(data, c, tokens);
  return tokens.access_token;
}
