#!/usr/bin/env node
import { createRequire } from 'node:module';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { parseArgs } from 'node:util';

const options = {
  url: { type: 'string' },
  out: { type: 'string' },
  primary: { type: 'string' },
  'primary-target': { type: 'string' },
  scene: { type: 'string' },
  'fallback-url': { type: 'string' },
  'fallback-visible': { type: 'string' },
  'playwright-module': { type: 'string' },
  channel: { type: 'string' },
  'settle-ms': { type: 'string', default: '1500' },
  draft: { type: 'boolean' },
  'full-page': { type: 'boolean' },
  'motion-plan': { type: 'string' },
  help: { type: 'boolean' },
};

const profiles = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844, mobile: true },
  { name: 'reduced-motion', width: 390, height: 844, mobile: true, reduced: true },
];

async function visible(page, selector, timeout = 2500) {
  try {
    const target = page.locator(selector).first();
    await target.waitFor({ state: 'visible', timeout });
    return await target.evaluate(element => {
      for (let node = element; node; node = node.parentElement) {
        const style = getComputedStyle(node);
        if (Number(style.opacity) === 0 || style.visibility !== 'visible') return false;
      }
      return true;
    });
  } catch {
    return false;
  }
}

async function fitsViewport(page, selector) {
  return page.locator(selector).first().evaluate(element => {
    const rect = element.getBoundingClientRect();
    return rect.top >= 0 && rect.left >= 0 &&
      rect.right <= document.documentElement.clientWidth &&
      rect.bottom <= window.innerHeight;
  });
}

async function checkPrimaryAction(page, args) {
  const action = page.locator(args.primary).first();
  const state = await action.evaluate((element, targetSelector) => {
    const rect = element.getBoundingClientRect();
    const hit = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2);
    const href = element.getAttribute('href');
    const destination = href === null ? null : new URL(href, location.href);
    const local = destination === null || (destination.origin === location.origin &&
      destination.pathname === location.pathname && destination.search === location.search);
    const targetId = destination?.hash ? decodeURIComponent(destination.hash.slice(1)) : null;
    const target = targetSelector ? document.querySelector(targetSelector) :
      targetId ? document.getElementById(targetId) : null;
    return {
      href, target_id: targetId, target_selector: targetSelector || null,
      target_exists: !!target,
      outside_viewport: rect.top < 0 || rect.left < 0 ||
        rect.right > document.documentElement.clientWidth || rect.bottom > innerHeight,
      obstructed: !hit || !element.contains(hit),
      disabled: element.matches(':disabled') || element.getAttribute('aria-disabled') === 'true',
      supported: local && (targetId !== null || !!targetSelector) &&
        !(element.form && (element.type === 'submit' || element.type === 'image')),
    };
  }, args['primary-target']);
  const failure = (code, detail) => ({ ...state, status: 'fail', code, detail });
  if (state.disabled) return failure('primary_disabled', args.primary);
  if (state.outside_viewport) return failure('primary_outside_viewport', args.primary);
  if (state.obstructed) return failure('primary_obstructed', args.primary);
  if (!state.supported) {
    return failure('primary_action_unverified', 'Use an in-page link or declare --primary-target for a local, non-submitting control.');
  }
  if (!state.target_exists) return failure('primary_target_missing', state.target_selector || state.target_id);
  // Only exercise local prototype controls. Prevent form/API writes and navigation while checking them.
  await page.route('**/*', route => {
    const request = route.request();
    return request.method() !== 'GET' || request.isNavigationRequest() ? route.abort() : route.continue();
  });
  try {
    await action.click({ timeout: 1800 });
    await page.waitForFunction(({ target_selector, target_id }) => {
      const target = target_selector ? document.querySelector(target_selector) : document.getElementById(target_id);
      if (!target || !target.checkVisibility({ opacityProperty: true, visibilityProperty: true })) return false;
      const rect = target.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < innerHeight &&
        rect.right > 0 && rect.left < innerWidth;
    }, state, { timeout: 1800 });
    return { ...state, status: 'pass' };
  } catch (error) {
    return failure('primary_target_unreachable', error.message);
  }
}

async function captureMotion(page, profile, plan, output) {
  const captured = {};
  for (const [effect, configuration] of Object.entries(plan)) {
    const action = configuration[profile.name];
    if (!configuration.trigger?.trim() || !action) throw Error(`Missing motion action: ${effect}/${profile.name}`);
    await page.goto(profile.url, { waitUntil: 'load', timeout: 12000 });
    const blockWrites = route => {
      const request = route.request();
      return request.method() !== 'GET' || request.isNavigationRequest() ? route.abort() : route.continue();
    };
    await page.route('**/*', blockWrites);
    try {
      const started = Date.now();
      if (action.type === 'click') await page.locator(action.selector).first().click({ timeout: 1800 });
      else if (action.type === 'hover') await page.locator(action.selector).first().hover({ timeout: 1800 });
      else if (action.type === 'scroll') {
        await page.locator(action.selector).first().evaluate(element => element.scrollIntoView({ behavior: 'smooth' }));
      } else if (action.type === 'pointer') {
        if (![action.x, action.y].every(value => Number.isFinite(value) && value >= 0 && value <= 1)) {
          throw Error('Pointer x and y must be viewport fractions from 0 to 1.');
        }
        await page.mouse.move(profile.width * action.x, profile.height * action.y);
      } else if (action.type !== 'load') throw Error(`Unsupported motion action: ${action.type}`);
      const frames = [];
      for (const targetMs of [0, 120, 360]) {
        await page.waitForTimeout(Math.max(0, targetMs - (Date.now() - started)));
        const file = `${effect}-${profile.name}-${targetMs}.png`;
        await page.screenshot({ path: join(output, file), timeout: 8000 });
        frames.push({ ms: Date.now() - started, file });
      }
      captured[effect] = { trigger: configuration.trigger, frames };
    } finally {
      await page.unroute('**/*', blockWrites);
    }
  }
  return captured;
}

async function review(browser, profile, args, output) {
  const context = await browser.newContext({
    viewport: { width: profile.width, height: profile.height },
    isMobile: !!profile.mobile,
    hasTouch: !!profile.mobile,
    deviceScaleFactor: 1,
    reducedMotion: profile.reduced ? 'reduce' : 'no-preference',
    serviceWorkers: 'block',
  });
  const issues = [];
  const note = (code, detail) => issues.push({ code, detail });
  const result = { profile: profile.name, url: profile.url, issues };
  try {
    const page = await context.newPage();
    page.on('pageerror', error => note('javascript_error', error.message));
    page.on('requestfailed', request => note('request_failed', request.url()));
    page.on('response', response => {
      if (response.status() >= 400) note('http_error', `${response.status()} ${response.url()}`);
    });
    const response = await page.goto(profile.url, { waitUntil: 'load', timeout: 12000 });
    if (response && !response.ok()) note('document_error', String(response.status()));
    await page.waitForTimeout(args.settleMs);
    result.title = await page.title();
    if (!result.title.trim()) note('missing_title', 'Document title is empty.');
    if (!await visible(page, 'h1')) {
      note('missing_heading', 'No visible primary heading.');
    } else if (args.draft && !await fitsViewport(page, 'h1')) {
      note('heading_outside_viewport', 'The full heading does not fit in the first viewport.');
    }
    if (args.primary && !await visible(page, args.primary)) {
      note('missing_primary', args.primary);
    }
    if (args.scene && !profile.reduced && !profile.fallback && !await visible(page, args.scene)) {
      note('missing_live_scene', args.scene);
    }
    if (profile.fallback) {
      if (!await visible(page, args['fallback-visible'])) note('missing_fallback', args['fallback-visible']);
      if (args.scene && await visible(page, args.scene, 500)) note('live_scene_in_fallback', args.scene);
    }
    const layout = await page.evaluate(() => {
      const root = document.documentElement;
      const broken = [...document.images].filter(image => {
        const rect = image.getBoundingClientRect();
        return rect.width && rect.height && rect.bottom > 0 && rect.top < innerHeight &&
          image.checkVisibility({ opacityProperty: true, visibilityProperty: true }) &&
          (image.currentSrc || image.getAttribute('src') || image.getAttribute('srcset')) &&
          image.complete && !image.naturalWidth;
      });
      return {
        viewport: [innerWidth, innerHeight],
        content_width: root.scrollWidth,
        overflow_px: Math.max(0, root.scrollWidth - root.clientWidth),
        broken_images: broken.map(image => image.currentSrc || image.getAttribute('src')),
        pending_images: [...document.images].filter(image => {
          const rect = image.getBoundingClientRect();
          return !image.complete && rect.width && rect.height && rect.top < innerHeight &&
            rect.bottom > 0 && image.checkVisibility({ opacityProperty: true, visibilityProperty: true });
        }).map(image => image.currentSrc || image.getAttribute('src')),
        failed_fonts: [...document.fonts].filter(font => font.status === 'error').map(font => font.family),
        pending_fonts: [...document.fonts].filter(font => font.status === 'loading').map(font => font.family),
      };
    });
    result.layout = layout;
    if (layout.overflow_px > 1) note('horizontal_overflow', `${layout.overflow_px}px`);
    for (const src of layout.broken_images) note('broken_visible_image', src);
    for (const src of layout.pending_images) note('pending_visible_image', src);
    for (const family of layout.failed_fonts) note('font_load_failed', family);
    for (const family of layout.pending_fonts) note('font_still_loading', family);
    const screenshot = `${profile.name}.png`;
    await page.screenshot({ path: join(output, screenshot), timeout: 8000 });
    result.screenshot = screenshot;
    if (args['full-page']) {
      const full = `${profile.name}-full.png`;
      await page.screenshot({ path: join(output, full), fullPage: true, timeout: 8000 });
      result.screenshot_full = full;
    }
    if (args.motionPlan && !profile.reduced && !profile.fallback) {
      result.motion_capture = await captureMotion(page, profile, args.motionPlan, output);
      await page.goto(profile.url, { waitUntil: 'load', timeout: 12000 });
      await page.waitForTimeout(args.settleMs);
    }
    if (args.draft || args['primary-target']) {
      if (await visible(page, args.primary, 500)) {
        result.primary_action = await checkPrimaryAction(page, args);
        if (result.primary_action.status !== 'pass') note(result.primary_action.code, result.primary_action.detail);
      }
    }
  } catch (error) {
    note('browser_check_failed', error.message);
  } finally {
    await context.close();
  }
  return result;
}

async function run(args, output) {
  if ((args.draft || args['primary-target']) && !args.primary) {
    throw Error('--draft and --primary-target require --primary with the actual main control selector.');
  }
  const url = new URL(args.url);
  if (args['motion-plan']) {
    args.motionPlan = JSON.parse(await readFile(args['motion-plan'], 'utf8'));
    if (!args.motionPlan || Array.isArray(args.motionPlan) || !Object.keys(args.motionPlan).length ||
        Object.keys(args.motionPlan).some(key => !['motion', 'transition', 'lighting'].includes(key))) {
      throw Error('Motion plan must name motion, transition or lighting actions.');
    }
  }
  if (!['http:', 'https:', 'file:'].includes(url.protocol) || url.username || url.password) {
    throw Error('--url must be an HTTP(S) or file URL without credentials.');
  }
  const runs = profiles
    .filter(profile => !args.draft || !profile.reduced)
    .map(profile => ({ ...profile, url: url.href }));
  if (args.draft && (args.scene || args['fallback-url'] || args['fallback-visible'])) {
    throw Error('--draft checks the initial desktop and mobile views. Use the full review for scenes and fallback.');
  }
  if (!!args['fallback-url'] !== !!args['fallback-visible']) {
    throw Error('--fallback-url and --fallback-visible must be provided together.');
  }
  if (args['fallback-url']) {
    const fallback = new URL(args['fallback-url'], url);
    if (fallback.origin !== url.origin || fallback.pathname !== url.pathname || fallback.protocol !== url.protocol) {
      throw Error('Fallback must use the same page URL with a different query or fragment.');
    }
    runs.push({ ...profiles[1], name: 'fallback', url: fallback.href, fallback: true });
  }
  const require = createRequire(resolve('package.json'));
  let browser;
  try {
    const { chromium } = require(args['playwright-module'] || 'playwright');
    browser = await chromium.launch({ timeout: 8000, ...(args.channel ? { channel: args.channel } : {}) });
  } catch (error) {
    return { status: 'unverified', reason: error.message, profiles: [] };
  }
  try {
    const results = [];
    for (const profile of runs) results.push(await review(browser, profile, args, output));
    if (args.motionPlan) {
      const capture = {};
      for (const profile of results) {
        for (const [effect, item] of Object.entries(profile.motion_capture || {})) {
          capture[effect] ||= { trigger: item.trigger };
          capture[effect][profile.profile] = item.frames;
        }
      }
      await writeFile(join(output, 'motion-capture.json'), JSON.stringify(capture, null, 2) + '\n');
    }
    return { status: results.some(profile => profile.issues.length) ? 'fail' : 'pass', profiles: results };
  } finally {
    await browser.close();
  }
}

const { values: args } = parseArgs({ options });
if (args.help) {
  console.log('node review_site.mjs --url URL --out DIR [--draft --primary SELECTOR] [--primary-target SELECTOR]\n  [--full-page] [--motion-plan JSON] [--scene SELECTOR] [--fallback-url URL --fallback-visible SELECTOR]\n  [--playwright-module PATH] [--channel chrome] [--settle-ms 1500]');
} else {
  if (!args.out || !args.url) throw Error('--url and --out are required.');
  args.settleMs = Number(args['settle-ms']);
  if (!/^\d+$/.test(args['settle-ms']) || args.settleMs > 5000) {
    throw Error('--settle-ms must be an integer from 0 to 5000.');
  }
  const output = resolve(args.out);
  await mkdir(output, { recursive: true });
  let report;
  try {
    report = await run(args, output);
  } catch (error) {
    report = { status: 'fail', reason: error.message, profiles: [] };
  }
  report.settle_ms = args.settleMs;
  report.visual_review = 'pending';
  const json = JSON.stringify(report, null, 2) + '\n';
  await writeFile(join(output, 'review.json'), json);
  process.stdout.write(json);
  process.exitCode = { pass: 0, fail: 1, unverified: 2 }[report.status];
}
