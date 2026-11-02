import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {gzipSync} from 'node:zlib';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';

const run = promisify(execFile);
const script = fileURLToPath(new URL('../scripts/measure_page.mjs', import.meta.url));
const modulePath = process.env.PLAYWRIGHT_MODULE;

test('real browser measures the intended page, wire headers, warm visit and errors', {skip: !modulePath}, async () => {
  const requested = [];
  const server = http.createServer((req, res) => {
    requested.push(req.url);
    if (req.url === '/favicon.ico') { res.writeHead(204); res.end(); return; }
    if (req.url === '/stream') {
      res.writeHead(200, {'Content-Type': 'application/octet-stream', 'Cache-Control': 'no-store'});
      res.write(Buffer.alloc(1024 * 1024, 65));
      const timer = setTimeout(() => res.end(), 2000);
      res.on('close', () => clearTimeout(timer));
      return;
    }
    const bodies = {
      '/': ['text/html', '<!doctype html><meta name="viewport" content="width=device-width"><title>Audit fixture</title><link rel="stylesheet" href="/a.css"><h1>Real loading fixture</h1><img src="/one.svg" width="20" height="20"><script src="/a.js" defer></script><div style="height:10000px"></div><img loading="lazy" src="/late.svg" width="20" height="20">'],
      '/a.css': ['text/css', 'h1{font-size:32px;color:#123}'],
      '/a.js': ['application/javascript', 'window.fixtureReady=true;'],
      '/one.svg': ['image/svg+xml', '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="red"/></svg>'],
      '/late.svg': ['image/svg+xml', '<svg xmlns="http://www.w3.org/2000/svg"/>'],
      '/diagnostic': ['text/html', '<!doctype html><title>Audit diagnostic</title><h1>Stream measurement</h1><script>console.error("SENTINEL_CONSOLE_ERROR");fetch("/stream").then(r=>r.arrayBuffer())</script>']
    };
    if (!bodies[req.url]) { res.writeHead(404); res.end('missing'); return; }
    const [type, body] = bodies[req.url];
    const encoded = gzipSync(body);
    res.writeHead(200, {'Content-Type': type, 'Content-Encoding': 'gzip', 'Content-Length': encoded.length,
      'Cache-Control': req.url === '/' ? 'no-cache' : 'public, max-age=3600'});
    res.end(encoded);
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const url = `http://127.0.0.1:${server.address().port}/`;
  const args = [script, '--url', url, '--playwright-module', modulePath, '--runs', '1', '--profile', 'desktop', '--settle-ms', '200'];
  try {
    const {stdout} = await run(process.execPath, [...args, '--warm', '--expect-title', 'Audit fixture'], {timeout: 30000});
    const r = JSON.parse(stdout);
    assert.equal(r.status, 'measured');
    assert.equal(r.samples.length, 2);
    assert.deepEqual(r.samples.map(s => s.cache_mode), ['cold', 'warm']);
    const first = r.samples[0];
    assert.equal(first.title, 'Audit fixture');
    assert.equal(first.document_headers['content-encoding'], 'gzip');
    assert.ok(first.metrics.fcp_ms > 0);
    assert.ok(first.metrics.lcp_observed_ms > 0);
    assert.equal(first.metrics.inp_ms, null);
    assert.ok(first.transferred_bytes > 0);
    assert.ok(first.resources.some(s => s.url.endsWith('/a.css')));
    assert.equal(requested.includes('/late.svg'), false);
    const diagnostic = await run(process.execPath, [...args, '--url', url + 'diagnostic', '--settle-ms', '500'], {timeout: 30000});
    const sample = JSON.parse(diagnostic.stdout).samples[0];
    assert.ok(sample.console_errors.some(s => s.includes('SENTINEL_CONSOLE_ERROR')));
    const stream = sample.resources.find(s => s.url.endsWith('/stream'));
    assert.equal(stream.finished, false);
    assert.ok(stream.encoded_bytes > 0);
    assert.ok(sample.transferred_bytes >= stream.encoded_bytes);
    assert.equal(sample.transferred_bytes_complete, false);
    await assert.rejects(run(process.execPath, [...args, '--expect-title', 'Wrong title'], {timeout: 30000}), error => {
      const failure = JSON.parse(error.stdout);
      assert.equal(failure.status, 'failed');
      assert.match(failure.error, /title/i);
      return true;
    });
  } finally {
    await new Promise(r => server.close(r));
  }
});
