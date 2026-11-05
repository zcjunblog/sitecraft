import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import {readFile, mkdtemp} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {resolve, extname} from 'node:path';

const root = fileURLToPath(new URL('../assets/', import.meta.url));
const enabled = !!process.env.PLAYWRIGHT_MODULE;
let browser, server, url, workspaceRoot;
before(async () => {
  if (!enabled) return;
  const require = createRequire(resolve(process.cwd(), 'package.json'));
  const {chromium} = require(process.env.PLAYWRIGHT_MODULE);
  browser = await chromium.launch({headless:true, ...(process.env.BROWSER_CHANNEL ? {channel:process.env.BROWSER_CHANNEL} : {})});
  const temporary = await mkdtemp(resolve(tmpdir(), 'sitecraft-workspace-'));
  workspaceRoot = resolve(temporary, 'site');
  const assembled = spawnSync('python3', [fileURLToPath(new URL('../scripts/design_assets.py',import.meta.url)), 'assemble',
    '--spec',resolve(root,'example-workspace-spec.json'),'--site',workspaceRoot,'--plan',resolve(temporary,'plan.json')],{encoding:'utf8'});
  assert.equal(assembled.status,0,assembled.stderr);
  server = createServer(async (req,res) => {
    const path = new URL(req.url,'http://localhost').pathname;
    try {
      const selected = path.startsWith('/workspace/') ? workspaceRoot : root;
      const relative = path.startsWith('/workspace/') ? path.slice('/workspace'.length) : path;
      const filename = resolve(selected, '.' + (relative === '/' ? (selected === root ? '/example.html' : '/index.html') : relative));
      if (!filename.startsWith(selected)) throw Error('Outside root');
      const body = await readFile(filename);
      res.writeHead(200,{'Content-Type':{'.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml','.html':'text/html'}[extname(filename)] || 'application/octet-stream'});
      res.end(body);
    } catch {res.writeHead(404);res.end();}
  });
  await new Promise(done => server.listen(0,'127.0.0.1',done));
  url = `http://127.0.0.1:${server.address().port}/`;
});
after(async () => {await browser?.close(); if (server) await new Promise(done=>server.close(done));});

test('example has no overflow and an initially reachable primary on desktop and mobile', {skip:!enabled}, async () => {
  for (const viewport of [{width:1440,height:900},{width:390,height:844},{width:360,height:800}]) {
    const page = await browser.newPage({viewport});
    const errors=[]; page.on('pageerror',error=>errors.push(error.message));
    await page.goto(url); await page.locator('.hero img').evaluate(img=>img.decode());
    const state=await page.locator('[data-sitecraft-primary]').evaluate(el=>({bottom:el.getBoundingClientRect().bottom,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth}));
    assert.equal(state.overflow,false); assert.ok(state.bottom<=state.height); assert.deepEqual(errors,[]);
    await page.locator('[data-sitecraft-primary]').click();
    await page.waitForFunction(()=>document.querySelector('#objects').getBoundingClientRect().top<innerHeight);
    await page.close();
  }
});
test('mobile menu opens with keyboard and Escape restores focus and scrolling', {skip:!enabled}, async()=>{
  const page=await browser.newPage({viewport:{width:390,height:844}}); await page.goto(url);
  const toggle=page.locator('[data-open-menu]'); await toggle.focus(); await page.keyboard.press('Enter');
  assert.equal(await page.locator('#site-menu').evaluate(el=>el.open),true);
  assert.equal(await toggle.getAttribute('aria-expanded'),'true');
  await page.keyboard.press('Escape'); await page.waitForFunction(()=>!document.querySelector('#site-menu').open);
  assert.equal(await toggle.evaluate(el=>el===document.activeElement),true);
  assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('is-modal-open')),false);
  await page.close();
});
test('contact preview treats markup as text and writes no network or storage data', {skip:!enabled},async()=>{
  const page=await browser.newPage(); const writes=[];
  page.on('request',request=>{if(request.method()!=='GET')writes.push(request.url());});
  await page.goto(url); await page.locator('[data-open-contact]').click();
  await page.locator('input[name=name]').fill('测试'); await page.locator('textarea').fill('<img src=x onerror=alert(1)>');
  await page.locator('#contact-form button').click();
  assert.match(await page.locator('#contact-result').innerText(),/留言未发送、未保存/);
  assert.equal(await page.locator('#contact-result img').count(),0);
  assert.equal(await page.evaluate(()=>localStorage.length),0); assert.deepEqual(writes,[]);
  await page.keyboard.press('Escape'); await page.waitForFunction(()=>!document.querySelector('#contact-dialog').open); await page.close();
});
test('reduced motion closes the dialog without waiting for animation', {skip:!enabled},async()=>{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'}); await page.goto(url);
  await page.locator('[data-open-menu]').click();
  assert.equal(await page.locator('#site-menu').evaluate(el=>getComputedStyle(el).animationName),'none');
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#site-menu').evaluate(el=>el.open),false); await page.close();
});
test('product DOM switches actual content with keyboard and fits the phone', {skip:!enabled},async()=>{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
  await page.goto(url+'workspace/');
  const buttons=page.locator('[data-work-item]');
  await buttons.nth(1).focus(); await page.keyboard.press('Enter');
  assert.equal(await buttons.nth(1).getAttribute('aria-pressed'),'true');
  assert.equal(await buttons.nth(0).getAttribute('aria-pressed'),'false');
  assert.equal(await page.locator('.workspace-detail h3').innerText(),'检查手机上的主要入口');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.equal(await page.locator('.workspace').evaluate(el=>getComputedStyle(el,'::before').animationName),'none');
  await page.close();
});
