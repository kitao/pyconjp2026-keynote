import { expect, test } from '@playwright/test';
import project from '../../package.json' with { type: 'json' };

const base = new URL(project.homepage).pathname;
const slides = base + 'slides/';
const active = 'svg.bespoke-marp-active section';

test('the README top page opens first and links to the slides and materials', async ({
  page,
  request,
}) => {
  await page.goto(base);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(
    'PyCon JP 2026 Keynote / 基調講演',
  );
  await expect(page.locator('main')).toContainText('広島国際会議場 フェニックスホール');
  await expect(page.locator('svg.bespoke-marp-slide')).toHaveCount(0);
  await expect(page.locator('main')).not.toContainText('npm run');
  for (const path of [
    'pyconjp2026-keynote.pdf',
    'trailer/',
    'trailer/app/',
    'CREDITS.md',
    'LICENSE',
  ]) {
    await expect(page.locator(`a[href="${path}"], a[href="${base}${path}"]`).first()).toBeVisible();
    expect((await request.get(base + path)).status()).toBe(200);
  }
  await page.getByRole('link', { name: 'Slides / 講演スライド', exact: true }).click();
  await expect(page).toHaveURL(new RegExp('/slides/$'));
  await expect(page.locator('section')).toHaveCount(52);
});

test('all slides, bundled fonts, images and keyboard navigation work', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(slides);
  await page.evaluate(() => document.fonts.ready);
  await expect(page.locator('section')).toHaveCount(52);
  await expect(page.locator(active + ' h1')).toContainText('Pyxelで、プログラミングを遊ぼう！');
  await page.keyboard.press('ArrowRight');
  await expect(page.locator(active + ' h1')).toContainText('今日は、Pyxelの話をします');
  await page.keyboard.type('34');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(new RegExp('#34$'));
  await expect(page.locator(active)).toBeVisible();
  await page.keyboard.press('l');
  expect(await page.evaluate(() => document.documentElement.style.cursor)).toBe('none');
  await page.keyboard.press('l');
  expect(await page.evaluate(() => document.documentElement.style.cursor)).toBe('');
  const missing = await page
    .locator('section img')
    .evaluateAll((images) =>
      images
        .filter((image) => !image.complete || image.naturalWidth === 0)
        .map((image) => image.src),
    );
  expect(missing).toEqual([]);
  expect(errors).toEqual([]);
});

test('direct slide URLs and the relocated web-demo link work', async ({ page }) => {
  await page.goto(slides + '#36');
  await expect(page.locator(active)).toBeVisible();
  await expect(page.locator(active + ' a')).toHaveAttribute(
    'href',
    base + 'demo/web/pyxel-run.html',
  );
  await page.goto(slides + '#52');
  await expect(page.locator(active)).toContainText('Pyxel');
});

test('every slide uses the bundled fonts without OS-dependent glyph fallbacks', async ({
  page,
}) => {
  await page.goto(slides);
  await page.evaluate(() => document.fonts.ready);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('DOM.enable');
  await cdp.send('CSS.enable');
  const { root } = await cdp.send('DOM.getDocument');
  for (let number = 1; number <= 52; number++) {
    await page.evaluate((number) => (location.hash = '#' + number), number);
    await expect(page.locator(active)).toHaveAttribute('id', String(number));
    await page.evaluate(() => document.fonts.ready);
    const count = await page.locator(active).evaluate((section, number) => {
      const nodes = [...section.querySelectorAll('*')].filter((node) =>
        [...node.childNodes].some((child) => child.nodeType === 3 && child.textContent.trim()),
      );
      nodes.forEach((node, index) => node.setAttribute('data-font-check', `${number}-${index}`));
      return nodes.length;
    }, number);
    for (let index = 0; index < count; index++) {
      const { nodeId } = await cdp.send('DOM.querySelector', {
        nodeId: root.nodeId,
        selector: `[data-font-check="${number}-${index}"]`,
      });
      const { fonts } = await cdp.send('CSS.getPlatformFontsForNode', { nodeId });
      expect(fonts.length, `Slide ${number}, text ${index}`).toBeGreaterThan(0);
      expect(
        fonts.every((font) => font.isCustomFont && font.familyName.startsWith('Noto')),
        `Slide ${number}, text ${index}: ${JSON.stringify(fonts)}`,
      ).toBe(true);
    }
  }
});

test('Tab and Enter reach slide links and video controls', async ({ page }) => {
  await page.goto(slides + '#52');
  const links = page.locator(active + ' a');
  await expect(links).toHaveCount(2);
  await page.keyboard.press('Tab');
  await expect(links.nth(0)).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(links.nth(1)).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(links.nth(0)).toBeFocused();

  await page.goto(slides + '#36');
  const demo = page.locator(active + ' a');
  await page.keyboard.press('Tab');
  await expect(demo).toBeFocused();
  const opened = page.waitForEvent('popup');
  await page.keyboard.press('Enter');
  const popup = await opened;
  await popup.waitForURL(new RegExp(base + 'demo/web/pyxel-run$'), {
    waitUntil: 'domcontentloaded',
  });
  await popup.close();

  await page.goto(slides + '#26');
  await page.keyboard.press('Tab');
  await expect(page.locator(active + ' video').first()).toBeFocused();
});

test('HTML canonicalization preserves queries and unknown/source paths return 404', async ({
  request,
}) => {
  for (const path of [
    base.slice(0, -1),
    base + 'index.html',
    slides.slice(0, -1),
    slides + 'index.html',
  ]) {
    const response = await request.get(path + '?from=test', { maxRedirects: 0 });
    expect(response.status()).toBe(307);
    const location = new URL(response.headers().location, 'http://127.0.0.1:4173');
    expect(location.pathname).toBe(path.includes('slides') ? slides : base);
    expect(location.search).toBe('?from=test');
  }
  for (const path of [
    'missing',
    'slides.md',
    'theme/pyxel.css',
    'tools/slides/build.sh',
    'package.json',
    '.git/config',
  ]) {
    expect((await request.get(base + path)).status()).toBe(404);
  }
  for (const path of ['/pyxel/', '/playload/', '/']) {
    expect((await request.get(path)).status()).toBe(404);
  }
});

test('PDF, licenses and browser demo are served with appropriate types', async ({ request }) => {
  const pdf = await request.get(base + 'pyconjp2026-keynote.pdf');
  expect(pdf.status()).toBe(200);
  expect(pdf.headers()['content-type']).toContain('application/pdf');
  expect((await pdf.body()).subarray(0, 5).toString()).toBe('%PDF-');
  for (const path of ['CREDITS.md', 'LICENSE']) {
    const response = await request.get(base + path);
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('text/plain');
  }
  const demo = await request.get(base + 'demo/web/pyxel-run');
  expect(demo.status()).toBe(200);
  expect(await demo.text()).toContain('<pyxel-run');
  expect(pdf.headers()['x-content-type-options']).toBe('nosniff');
});

test('slide videos and the trailer decode and play', async ({ page }) => {
  await page.goto(slides + '#27');
  const video = page.locator(active + ' video').first();
  await expect(video).toBeVisible();
  await video.evaluate((element) => element.play());
  await expect.poll(() => video.evaluate((element) => element.currentTime)).toBeGreaterThan(0);
  await video.evaluate((element) => element.pause());
  await page.goto(base + 'trailer/');
  const trailer = page.locator('video');
  await expect(trailer).toBeVisible();
  await trailer.evaluate((element) => element.play());
  await expect.poll(() => trailer.evaluate((element) => element.currentTime)).toBeGreaterThan(0);
  await trailer.evaluate((element) => element.pause());
  expect(await trailer.evaluate((element) => element.error)).toBeNull();
});

test('slides and trailer work at a phone width', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(slides + '#1');
  await expect(page.locator(active)).toBeVisible();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator(active + ' h1')).toContainText('今日は、Pyxelの話をします');
  await page.goto(base + 'trailer/');
  await expect(page.locator('video')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
