/// <reference types="node" />
/* The Node server as it is deployed (server/index.mjs, serving dist/), started for a browser test against the stubs. */
import { spawn, type ChildProcess } from 'node:child_process';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { BACKEND_SECRET, startStubs, type Stubs } from './stubs';

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

const freePort = () => new Promise<number>((resolve, reject) => {
  const probe = net.createServer();
  probe.once('error', reject);
  probe.listen(0, '127.0.0.1', () => { const { port } = probe.address() as net.AddressInfo; probe.close(() => resolve(port)); });
});

async function waitForHealth(origin: string, server: ChildProcess, log: string[]) {
  for (let attempt = 0; attempt < 150; attempt++) {
    if (server.exitCode !== null) throw new Error(`The Node server exited with ${server.exitCode}: ${log.join('')}`);
    try { if ((await fetch(`${origin}/health`)).ok) return; } catch { /* not listening yet */ }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`The Node server did not answer /health: ${log.join('')}`);
}

export interface Atelier { origin: string; stubs: Stubs; log: string[]; stop: () => Promise<void> }

/** The stubs, and the Node server on a free port pointed at them. */
export async function startAtelier(): Promise<Atelier> {
  const stubs = await startStubs();
  const port = await freePort();
  const origin = `http://127.0.0.1:${port}`;
  const log: string[] = [];
  const server = spawn(process.execPath, ['server/index.mjs'], {
    cwd: frontend,
    // No public Command Center origin: this host's own sign-in, so nothing redirects to another host.
    env: { ...process.env, PORT: String(port), NODE_ENV: 'test', COMMAND_CENTER_AUTH_ORIGIN: stubs.authOrigin, COMMAND_CENTER_PUBLIC_ORIGIN: '',
      ATELIER_BACKEND_ORIGIN: stubs.backendOrigin, ATELIER_API_SECRET: BACKEND_SECRET },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  server.stdout?.on('data', chunk => log.push(String(chunk)));
  server.stderr?.on('data', chunk => log.push(String(chunk)));
  try { await waitForHealth(origin, server, log); } catch (error) { server.kill(); await stubs.close(); throw error; }
  return {
    origin, stubs, log,
    stop: async () => {
      if (server.exitCode === null) await new Promise(resolve => { server.once('exit', resolve); server.kill(); });
      await stubs.close();
    },
  };
}
