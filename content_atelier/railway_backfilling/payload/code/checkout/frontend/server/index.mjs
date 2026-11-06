import { createApp } from './app.mjs';

const port = Number(process.env.PORT || 8080);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('PORT must be a valid TCP port.');
const app = createApp({
  authOrigin: process.env.COMMAND_CENTER_AUTH_ORIGIN,
  publicAuthOrigin: process.env.COMMAND_CENTER_PUBLIC_ORIGIN,
  backendOrigin: process.env.ATELIER_BACKEND_ORIGIN,
  backendSecret: process.env.ATELIER_API_SECRET,
  deploymentId: process.env.RAILWAY_DEPLOYMENT_ID || undefined,
  production: process.env.NODE_ENV === 'production',
});
// IPv6 dual stack supports Railway's private network as well as public ingress.
const server = app.listen(port, '::', () => console.log(`[atelier] Listening on ${port}`));
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.once(signal, () => {
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(1), 10_000).unref();
  });
}
