import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const script = fileURLToPath(new URL('../scripts/review_site.mjs', import.meta.url));
const modulePath = process.env.PLAYWRIGHT_MODULE;
const html = (body, css = '') => `<!doctype html><html lang="zh"><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>首屏检查样例</title><style>body{margin:20px}a,button{display:inline-block;padding:12px}
#flowers{margin-top:1200px} ${css}</style></head><body>
<h1>今天的花</h1>${body}</body></html>`;

test('draft review checks real first-screen paths and assets', { skip: !modulePath }, async t => {
  let submissions = 0;
  const routes = {
    '/good': html('<a id="primary" href="#花单">查看花单</a><section id="花单" style="margin-top:1200px">今日可选花束</section>'),
    '/below': html('<div class="gap"></div><a id="primary" href="#flowers">查看花单</a><section id="flowers">花束</section>',
      '@media(max-width:600px){.gap{height:900px}}'),
    '/missing': html('<a id="primary" href="#flowers">查看花单</a>'),
    '/empty': html('<a id="primary" href="#">查看花单</a>'),
    '/obstructed': html('<a id="primary" href="#flowers">查看花单</a><div style="position:fixed;inset:0;background:white;z-index:9"></div><section id="flowers">花束</section>'),
    '/prevented': html('<a id="primary" href="#flowers" onclick="event.preventDefault()">查看花单</a><section id="flowers">花束</section>'),
    '/dialog': html('<button id="primary" onclick="document.querySelector(\'#dialog\').hidden=false">打开花单</button><div id="dialog" hidden>今日花束</div>'),
    '/form': html('<form action="/submit" method="post"><button id="primary">提交预约</button></form>'),
    '/assets': html('<a id="primary" href="#flowers">查看花单</a><img src="/bad.svg" width="40" height="40"><section id="flowers">花束</section>',
      '@font-face{font-family:Broken;src:url(/bad.woff2)}h1{font-family:Broken,sans-serif}'),
    '/motion': html('<a id="primary" href="#flowers">查看花单</a><div class="scene">Scene</div><section id="flowers">花束</section>',
      '.scene{width:100px;height:100px;animation:move 1s linear infinite alternate}@keyframes move{to{transform:translateX(120px);background:red}}'),
  };
  const server = createServer((req, res) => {
    if (req.url === '/submit') submissions++;
    if (req.url === '/favicon.ico') { res.writeHead(204); res.end(); return; }
    const body = routes[req.url];
    res.writeHead(200, { 'Content-Type': body ? 'text/html; charset=utf-8' :
      req.url === '/bad.woff2' ? 'font/woff2' : 'image/svg+xml' });
    res.end(body || 'not a valid asset');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const output = await mkdtemp(join(tmpdir(), 'sitecraft-review-'));
  async function review(name, extra = [], draft = true) {
    const args = [script, '--url', base + '/' + name, '--out', join(output, name),
      '--playwright-module', modulePath, '--settle-ms', '0'];
    if (draft) args.push('--draft');
    args.push(...extra);
    let code = 0;
    try { await run(process.execPath, args, { timeout: 25000 }); }
    catch (error) { code = error.code; }
    const report = JSON.parse(await readFile(join(output, name, 'review.json'), 'utf8'));
    return { code, report, issues: report.profiles.flatMap(profile => profile.issues.map(issue => issue.code)) };
  }
  try {
    await t.test('requires the actual primary selector in draft mode', async () => {
      const result = await review('good');
      assert.equal(result.code, 1);
      assert.match(result.report.reason, /primary/);
    });
    await t.test('checks and follows a Unicode fragment after the initial screenshots', async () => {
      const result = await review('good', ['--primary', '#primary']);
      assert.equal(result.code, 0);
      assert.equal(result.report.status, 'pass');
      assert.equal(result.report.profiles.length, 2);
      assert(result.report.profiles.every(profile => profile.primary_action.status === 'pass'));
    });
    await t.test('detects a mobile primary action below the first viewport', async () => {
      const result = await review('below', ['--primary', '#primary']);
      assert.equal(result.code, 1);
      assert(result.issues.includes('primary_outside_viewport'));
      assert(!result.issues.includes('primary_obstructed'));
    });
    for (const name of ['missing', 'empty', 'prevented']) {
      await t.test('rejects ' + name + ' fragment actions', async () => {
        const result = await review(name, ['--primary', '#primary']);
        assert.equal(result.code, 1);
        assert(result.issues.some(code => code.startsWith('primary_')));
      });
    }
    await t.test('detects an obstructed primary action', async () => {
      const result = await review('obstructed', ['--primary', '#primary']);
      assert.equal(result.code, 1);
      assert(result.issues.includes('primary_obstructed'));
    });
    await t.test('tests an explicitly declared local dialog target', async () => {
      const result = await review('dialog', ['--primary', '#primary', '--primary-target', '#dialog']);
      assert.equal(result.code, 0);
      assert(result.report.profiles.every(profile => profile.primary_action.status === 'pass'));
    });
    await t.test('does not submit a form to test its action', async () => {
      const result = await review('form', ['--primary', '#primary', '--primary-target', 'form']);
      assert.equal(result.code, 1);
      assert(result.issues.includes('primary_action_unverified'));
      assert.equal(submissions, 0);
    });
    await t.test('detects corrupt images and fonts even with HTTP 200', async () => {
      const result = await review('assets', ['--primary', '#primary']);
      assert.equal(result.code, 1);
      assert(result.issues.includes('broken_visible_image'));
      assert(result.issues.includes('font_load_failed'));
    });
    await t.test('captures real intermediate motion frames for desktop and mobile', async () => {
      const plan = join(output, 'motion-plan.json');
      await writeFile(plan, JSON.stringify({ motion: { trigger: 'Watch the live scene',
        desktop: { type: 'load' }, mobile: { type: 'load' } } }));
      const result = await review('motion', ['--primary', '#primary', '--motion-plan', plan]);
      assert.equal(result.code, 0);
      const capture = JSON.parse(await readFile(join(output, 'motion', 'motion-capture.json'), 'utf8'));
      for (const profile of ['desktop', 'mobile']) {
        const frames = capture.motion[profile];
        assert.equal(frames.length, 3);
        assert(frames[0].ms < frames[1].ms && frames[1].ms < frames[2].ms);
        const images = await Promise.all(frames.map(frame => readFile(join(output, 'motion', frame.file))));
        assert(!images[0].equals(images[1]));
      }
    });
    await t.test('keeps the three-profile default check usable without a primary selector', async () => {
      const result = await review('good', [], false);
      assert.equal(result.code, 0);
      assert.equal(result.report.profiles.length, 3);
    });
  } finally {
    await new Promise(resolve => server.close(resolve));
    await rm(output, { recursive: true, force: true });
  }
});
