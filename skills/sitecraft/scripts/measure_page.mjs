#!/usr/bin/env node
// Browser lab observations, never a Lighthouse score or real-user CWV certificate.
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {mkdir, writeFile} from 'node:fs/promises';
import {dirname} from 'node:path';

function argsFrom(argv) {
  const a = {runs: 3, profile: 'mobile', settleMs: 1000, warm: false};
  const keys = {'--url': 'url', '--report': 'report', '--playwright-module': 'module',
    '--channel': 'channel', '--expect-title': 'expectedTitle', '--runs': 'runs',
    '--profile': 'profile', '--settle-ms': 'settleMs', '--cpu-rate': 'cpuRate',
    '--latency-ms': 'latencyMs', '--download-kbps': 'downloadKbps', '--upload-kbps': 'uploadKbps'};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--warm') { a.warm = true; continue; }
    if (!keys[argv[i]] || !argv[i + 1]) throw Error(`Unknown or incomplete option: ${argv[i]}`);
    a[keys[argv[i]]] = argv[++i];
  }
  if (!['mobile', 'desktop'].includes(a.profile)) throw Error('--profile must be mobile or desktop');
  const url = new URL(a.url);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw Error('--url must be HTTP(S) without embedded credentials');
  const mobile = a.profile === 'mobile';
  for (const [key, fallback] of Object.entries({runs: 3, settleMs: 1000,
    cpuRate: mobile ? 4 : 1, latencyMs: mobile ? 150 : 0,
    downloadKbps: mobile ? 1600 : 0, uploadKbps: mobile ? 750 : 0})) {
    a[key] = Number(a[key] ?? fallback);
    if (!Number.isFinite(a[key]) || a[key] < 0) throw Error(`Invalid ${key}`);
  }
  if (!Number.isInteger(a.runs) || a.runs < 1 || a.runs > 10 || a.cpuRate < 1 || a.settleMs > 10000) throw Error('Invalid run count, CPU rate, or settle interval');
  return a;
}

function observePage() {
  const m = window.__staticReleaseMetrics = {lcp: null, cls: null};
  const supported = PerformanceObserver.supportedEntryTypes || [];
  if (supported.includes('largest-contentful-paint')) {
    new PerformanceObserver(list => { for (const e of list.getEntries()) m.lcp = e.startTime; })
      .observe({type: 'largest-contentful-paint', buffered: true});
  }
  if (supported.includes('layout-shift')) {
    m.cls = 0;
    let start = 0, previous = 0, value = 0;
    new PerformanceObserver(list => {
      for (const e of list.getEntries()) {
        if (e.hadRecentInput) continue;
        if (e.startTime - previous < 1000 && e.startTime - start < 5000) value += e.value;
        else { start = e.startTime; value = e.value; }
        previous = e.startTime;
        m.cls = Math.max(m.cls, value);
      }
    }).observe({type: 'layout-shift', buffered: true});
  }
}

function headers(raw = {}) {
  const allowed = new Set(['cache-control', 'content-encoding', 'content-type', 'content-length', 'etag', 'last-modified']);
  return Object.fromEntries(Object.entries(raw).filter(([k]) => allowed.has(k.toLowerCase())).map(([k, v]) => [k.toLowerCase(), String(v)]));
}

async function run(a) {
  const require = createRequire(resolve(process.cwd(), 'package.json'));
  let chromium;
  try { ({chromium} = require(a.module || 'playwright')); }
  catch { throw Error('Playwright is not available. Reuse a project installation with --playwright-module; no dependencies were installed.'); }
  const browser = await chromium.launch({headless: true, ...(a.channel ? {channel: a.channel} : {})});
  const samples = [];
  let throttleMethod = 'none';
  try {
    for (let i = 0; i < a.runs; i++) {
      const mobile = a.profile === 'mobile';
      const context = await browser.newContext({viewport: mobile ? {width: 390, height: 844} : {width: 1440, height: 900},
        isMobile: mobile, hasTouch: mobile, deviceScaleFactor: 1, serviceWorkers: 'block', locale: 'zh-CN'});
      try {
        await context.addInitScript(observePage);
        const page = await context.newPage();
        const cdp = await context.newCDPSession(page);
        await cdp.send('Network.enable');
        await cdp.send('Network.setCacheDisabled', {cacheDisabled: true});
        await cdp.send('Emulation.setCPUThrottlingRate', {rate: a.cpuRate});
        if (a.latencyMs || a.downloadKbps || a.uploadKbps) {
          const network = {latency: a.latencyMs, downloadThroughput: a.downloadKbps ? a.downloadKbps * 1000 / 8 : -1,
            uploadThroughput: a.uploadKbps ? a.uploadKbps * 1000 / 8 : -1};
          try {
            await cdp.send('Network.emulateNetworkConditionsByRule', {offline: false, matchedNetworkConditions: [{urlPattern: '', ...network}]});
            throttleMethod = 'Network.emulateNetworkConditionsByRule';
          } catch (e) {
            if (!/not found|wasn't found|unknown method/i.test(e.message)) throw e;
            await cdp.send('Network.emulateNetworkConditions', {offline: false, ...network});
            throttleMethod = 'Network.emulateNetworkConditions (legacy fallback)';
          }
        }
        let resources = new Map(), pageErrors = [], consoleErrors = [];
        page.on('pageerror', e => pageErrors.push(e.message));
        page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
        cdp.on('Network.requestWillBeSent', e => resources.set(e.requestId, {url: e.request.url, type: e.type,
          encoded_bytes: 0, received_encoded_body_bytes: 0, decoded_body_bytes: 0, byte_count_complete: false, finished: false}));
        cdp.on('Network.responseReceived', e => {
          const r = resources.get(e.requestId);
          if (r) Object.assign(r, {status: e.response.status, headers: headers(e.response.headers),
            from_disk_cache: !!e.response.fromDiskCache, from_service_worker: !!e.response.fromServiceWorker});
        });
        cdp.on('Network.dataReceived', e => {
          const r = resources.get(e.requestId);
          if (r) {
            r.received_encoded_body_bytes += e.encodedDataLength;
            r.decoded_body_bytes += e.dataLength;
            if (!r.byte_count_complete) r.encoded_bytes = r.received_encoded_body_bytes;
          }
        });
        cdp.on('Network.loadingFinished', e => {
          const r = resources.get(e.requestId);
          if (r) Object.assign(r, {encoded_bytes: e.encodedDataLength, byte_count_complete: true, finished: true});
        });
        cdp.on('Network.loadingFailed', e => {
          const r = resources.get(e.requestId);
          if (r) Object.assign(r, {error: e.errorText, finished: true});
        });
        async function visit(cacheMode, record = true) {
          resources = new Map(); pageErrors = []; consoleErrors = [];
          const response = await page.goto(a.url, {waitUntil: 'load', timeout: 25000});
          if (!response || !response.ok()) throw Error(`Document returned HTTP ${response?.status() ?? 'no response'}`);
          const title = await page.title();
          if (a.expectedTitle && !title.includes(a.expectedTitle)) throw Error('Page title does not match --expect-title; possible login gate or wrong page');
          await page.waitForTimeout(a.settleMs);
          if (!record) return;
          const metrics = await page.evaluate(() => {
            const n = performance.getEntriesByType('navigation')[0];
            const paint = performance.getEntriesByName('first-contentful-paint')[0];
            const m = window.__staticReleaseMetrics;
            return {ttfb_ms: n?.responseStart ?? null, fcp_ms: paint?.startTime ?? null,
              lcp_observed_ms: m?.lcp ?? null, cls_observed: m?.cls ?? null,
              dom_content_loaded_ms: n?.domContentLoadedEventEnd ?? null,
              load_event_ms: n?.loadEventEnd ?? null, inp_ms: null};
          });
          const rows = [...resources.values()].filter(r => /^https?:/.test(r.url));
          const issueRows = rows.filter(r => r.error || r.status >= 400 || !r.finished);
          samples.push({cache_mode: cacheMode, title, final_url: page.url(), metrics,
            document_headers: headers(await response.allHeaders()), resource_count: rows.length,
            transferred_bytes: rows.reduce((n, r) => n + r.encoded_bytes, 0),
            transferred_bytes_complete: rows.every(r => r.byte_count_complete),
            resources: rows, request_issues: issueRows, javascript_errors: [...pageErrors], console_errors: [...consoleErrors]});
        }
        await visit('cold');
        if (a.warm && i === a.runs - 1) {
          await cdp.send('Network.setCacheDisabled', {cacheDisabled: false});
          await visit('prime', false); // Cache-disabled cold run did not prime a reusable cache.
          await visit('warm');
        }
      } finally { await context.close(); }
    }
    const cold = samples.filter(s => s.cache_mode === 'cold');
    const summary = {};
    for (const key of ['ttfb_ms', 'fcp_ms', 'lcp_observed_ms', 'cls_observed']) {
      const values = cold.map(s => s.metrics[key]).filter(Number.isFinite).sort((a, b) => a - b);
      const middle = Math.floor(values.length / 2);
      summary[key] = {median: !values.length ? null : values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2,
        max: values.length ? values[values.length - 1] : null};
    }
    return {status: 'measured', measured_at_utc: new Date().toISOString(), url: a.url,
      environment: {browser: browser.version(), profile: a.profile, viewport: a.profile === 'mobile' ? '390x844' : '1440x900',
        device_scale_factor: 1, cpu_rate: a.cpuRate, latency_ms: a.latencyMs, download_kbps: a.downloadKbps,
        upload_kbps: a.uploadKbps, transport_throttling_method: throttleMethod, settle_ms: a.settleMs, service_workers: 'blocked'},
      cold_summary: summary, samples,
      limitations: ['Lab samples from this machine/network, not real-device or real-user p75 data.',
        'LCP/CLS are observations within the declared interval; later changes may be missed.',
        'INP is not measured. No Lighthouse score was generated.',
        'CDP encodedDataLength is observed HTTP data, not ZIP bytes or TCP/TLS connection overhead; redirect accounting may be incomplete.',
        'For in-flight or failed requests, observed body bytes are included but the total is a lower bound; inspect transferred_bytes_complete and request_issues.',
        'No scrolling: this is an initial-load window, not a count of all below-fold or future interaction resources.',
        'A measured result is not a pass: inspect budgets, HTTP errors, missing metrics and actual page identity.']};
  } finally { await browser.close(); }
}

if (process.argv.includes('--help')) {
  console.log('node measure_page.mjs --url HTTP_URL [--profile mobile|desktop] [--runs 3] [--warm] [--expect-title TEXT]\n  [--playwright-module MODULE_PATH] [--channel chrome] [--settle-ms 1000] [--report PATH]\n  [--cpu-rate N] [--latency-ms N] [--download-kbps N] [--upload-kbps N]\nMobile default: 390x844, DPR 1, 4x CPU slowdown, 150ms latency, 1600/750 decimal kbps. Desktop: unthrottled.');
} else {
  let a, result;
  try { a = argsFrom(process.argv.slice(2)); result = await run(a); }
  catch (e) { result = {status: 'failed', error: e.message}; process.exitCode = 1; }
  const encoded = JSON.stringify(result, null, 2) + '\n';
  if (a?.report) { await mkdir(dirname(resolve(a.report)), {recursive: true}); await writeFile(a.report, encoded); }
  process.stdout.write(encoded);
}
