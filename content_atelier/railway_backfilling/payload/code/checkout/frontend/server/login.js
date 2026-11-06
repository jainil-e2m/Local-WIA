const form = document.getElementById('login');
const button = form.querySelector('button');
const error = document.getElementById('error');
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
    window.location.replace('/');
  } catch (problem) {
    error.textContent = problem instanceof Error ? problem.message : 'Unable to sign in. Please retry.';
    error.hidden = false;
    button.disabled = false;
    button.textContent = 'Sign in';
  }
});
