import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {normalizeApiBase, requestJSON} from '../dist/api-client.js';

const here = 'https://app.example/';
const allowed = ['https://api.example'];
for (const address of ['https://evil.example', 'http://api.example', 'https://api.example.evil/', 'https://api.example@evil.example/', 'https://user:pass@api.example', 'https://api.example/?x=1', 'https://api.example/#x', 'javascript:alert(1)', 'data:text/plain,test', 'ftp://localhost', '//api.example', 'http://127.0.0.1']) {
  assert.throws(() => normalizeApiBase(address, allowed, here), address);
}
assert.equal(normalizeApiBase('https://api.example/v1/', allowed, here), 'https://api.example/v1');
assert.equal(normalizeApiBase('', [], here), '');
assert.equal(normalizeApiBase('https://app.example/', [], here), 'https://app.example');
assert.equal(normalizeApiBase('http://127.0.0.1:8768/', [], 'http://127.0.0.1:8768/'), 'http://127.0.0.1:8768');
assert.throws(() => normalizeApiBase('http://127.0.0.1:8769', [], 'http://127.0.0.1:8768/'));

// A real HTTP redirect must not forward signed credentials, even if its target
// would normally be reachable. Use fake session data and loopback servers only.
let leaked = 0;
const target = createServer((req, res) => { leaked++; res.end('{}'); });
await new Promise(resolve => target.listen(0, '127.0.0.1', resolve));
const source = createServer((req, res) => {
  res.writeHead(307, {Location: `http://127.0.0.1:${target.address().port}/api/bootstrap`});
  res.end();
});
await new Promise(resolve => source.listen(0, '127.0.0.1', resolve));
globalThis.location = {href: `http://127.0.0.1:${source.address().port}/`};
try {
  await assert.rejects(requestJSON('', '/api/bootstrap', {initData: 'fake-signed-session'}));
  assert.equal(leaked, 0);
} finally {
  source.closeAllConnections(); target.closeAllConnections();
  await Promise.all([new Promise(resolve => source.close(resolve)), new Promise(resolve => target.close(resolve))]);
}

let authenticatedRequests = 0;
globalThis.fetch = async (url, options) => {
  if (String(url).endsWith('/config.json')) return {ok: true, json: async () => ({apiOrigins: []})};
  authenticatedRequests++;
  return {ok: true, json: async () => ({})};
};
await assert.rejects(requestJSON('https://evil.example', '/api/bootstrap', {initData: 'fake-signed-session'}));
assert.equal(authenticatedRequests, 0);
console.log('API client: URL allowlist, loopback rules, credential redirect and saved-origin rejection passed.');
