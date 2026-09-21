import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('../src/api.js', import.meta.url), 'utf8');
const { request, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
let captured;
globalThis.fetch = async (path, options) => {
  captured = { path, options };
  return new Response(JSON.stringify({ phase: 'job' }), { status: 200 });
};
assert.deepEqual(await request('/api/action', 'test-token', { op: 'display' }), { phase: 'job' });
assert.equal(captured.options.headers.Authorization, 'Bearer test-token');
assert.equal(captured.options.keepalive, true);
assert.deepEqual(JSON.parse(captured.options.body), { op: 'display' });
globalThis.fetch = async () => new Response(JSON.stringify({ error: 'stale' }), { status: 409 });
await assert.rejects(request('/api/action', 'test-token', {}), error => error instanceof ApiError && error.status === 409);
globalThis.fetch = async () => { throw new Error('disconnected'); };
await assert.rejects(request('/api/me'), error => error instanceof ApiError && error.status === 0);
console.log('API checks passed: credentials, JSON, keepalive, stale responses, connection failure.');
