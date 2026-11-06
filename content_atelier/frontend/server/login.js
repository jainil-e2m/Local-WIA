const form = document.getElementById('login');
const button = form.querySelector('button');
const error = document.getElementById('error');
// A deep link survives sign-in: the server sends the page the person asked for as ?returnTo=, and only a path on this
// host is followed (the same rule as server/sso.mjs localReturnTo). The address is resolved the way the browser will
// resolve it (it drops tabs and newlines, and reads a backslash as a slash), and only its path and query are followed,
// so "/<tab>/elsewhere" can never become "//elsewhere".
function returnPath() {
  const value = new URLSearchParams(window.location.search).get('returnTo');
  if (!value || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u001f\u007f]/.test(value)) return '/';
  let url;
  try { url = new URL(value, window.location.origin); } catch { return '/'; }
  if (url.origin !== window.location.origin || url.pathname.startsWith('//')) return '/';
  return url.pathname === '/login' || url.pathname.startsWith('/api/') ? '/' : url.pathname + url.search;
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  button.disabled = true;
  button.textContent = 'Signing in…';
  error.hidden = true;
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: form.email.value, password: form.password.value }),
      signal: AbortSignal.timeout(15_000),
    });
    const result = await response.json();
    if (!response.ok || !result.user?.email) throw new Error(result.error || 'Sign-in failed. Please retry.');
    form.password.value = '';
    window.location.replace(returnPath());
  } catch (problem) {
    error.textContent = problem instanceof Error ? problem.message : 'Unable to sign in. Please retry.';
    error.hidden = false;
    button.disabled = false;
    button.textContent = 'Sign in';
  }
});
