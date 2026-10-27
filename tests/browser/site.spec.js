import { expect, test } from '@playwright/test';
import { active, base, expectToPlay, slides, stubExternal } from './helpers.js';

test.beforeEach(async ({ context }) => {
  await stubExternal(context);
});

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

test('all slides, images and keyboard navigation work', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(slides);
  await expect(page.locator('section')).toHaveCount(52);
  await expect(page.locator(active + ' h1')).toContainText('Pyxelで、プログラミングを遊ぼう！');
  await page.keyboard.press('ArrowRight');
  await expect(page.locator(active + ' h1')).toContainText('今日は、Pyxelの話をします');
  await page.keyboard.type('34');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(new RegExp('#34$'));
  await expect(page.locator(active)).toHaveAttribute('id', '34');
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
  for (const number of ['36', '52']) {
    // A fresh page each time, so the hash is read on load rather than on a hash change.
    await page.goto('about:blank');
    await page.goto(slides + '#' + number);
    await expect(page.locator(active)).toHaveAttribute('id', number);
  }
  await page.goto('about:blank');
  await page.goto(slides + '#36');
  await expect(page.locator(active + ' a')).toHaveAttribute(
    'href',
    base + 'demo/web/pyxel-run.html',
  );
});

test('every slide uses the bundled fonts without OS-dependent glyph fallbacks', async ({
  page,
}) => {
  await page.goto(slides);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('DOM.enable');
  await cdp.send('CSS.enable');
  const { root } = await cdp.send('DOM.getDocument');
  for (let number = 1; number <= 52; number++) {
    await page.evaluate((number) => (location.hash = '#' + number), number);
    await expect(page.locator(active)).toHaveAttribute('id', String(number));
    await page.evaluate(() => document.fonts.ready);
    // Mark every element that sets text of its own, in document order.
    const texts = await page.locator(active).evaluate((section) =>
      [...section.querySelectorAll('*')]
        .filter((node) =>
          [...node.childNodes].some((child) => child.nodeType === 3 && child.textContent.trim()),
        )
        .map((node) => {
          node.setAttribute('data-font-check', '');
          return node.textContent.trim().slice(0, 30);
        }),
    );
    const { nodeIds } = await cdp.send('DOM.querySelectorAll', {
      nodeId: root.nodeId,
      selector: `${active} [data-font-check]`,
    });
    expect(nodeIds.length, `Slide ${number}`).toBe(texts.length);
    const results = await Promise.all(
      nodeIds.map((nodeId) => cdp.send('CSS.getPlatformFontsForNode', { nodeId })),
    );
    results.forEach(({ fonts }, index) => {
      const label = `Slide ${number}, "${texts[index]}": ${JSON.stringify(fonts)}`;
      expect(fonts.length, label).toBeGreaterThan(0);
      expect(
        fonts.every((font) => font.isCustomFont && font.familyName.startsWith('Noto')),
        label,
      ).toBe(true);
    });
  }
});

test('Tab and Enter reach slide links and video controls', async ({ page }) => {
  await page.goto(slides + '#52');
  await expect(page.locator(active)).toHaveAttribute('id', '52');
  const links = page.locator(active + ' a');
  await expect(links).toHaveCount(2);
  await page.keyboard.press('Tab');
  await expect(links.nth(0)).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(links.nth(1)).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(links.nth(0)).toBeFocused();

  await page.goto(slides + '#36');
  await expect(page.locator(active)).toHaveAttribute('id', '36');
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
  await expect(page.locator(active)).toHaveAttribute('id', '26');
  await page.keyboard.press('Tab');
  await expect(page.locator(active + ' video').first()).toBeFocused();
});

test('HTML canonicalization preserves queries and unknown/source paths return 404', async ({
  request,
  baseURL,
}) => {
  for (const path of [
    base.slice(0, -1),
    base + 'index.html',
    slides.slice(0, -1),
    slides + 'index.html',
  ]) {
    const response = await request.get(path + '?from=test', { maxRedirects: 0 });
    expect(response.status()).toBe(307);
    const location = new URL(response.headers().location, baseURL);
    expect(location.pathname).toBe(path.includes('slides') ? slides : base);
    expect(location.search).toBe('?from=test');
    // The redirects carry the security headers as well.
    expect(response.headers()['x-content-type-options'], path).toBe('nosniff');
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

test('the top and trailer retain their own page styles', async ({ page }) => {
  for (const path of ['', 'trailer/']) {
    await page.goto(base + path);
    const style = await page.evaluate(() => {
      const { backgroundColor, fontFamily } = getComputedStyle(document.body);
      return { backgroundColor, fontFamily };
    });
    expect(style, path).toEqual({
      backgroundColor: path ? 'rgb(16, 24, 32)' : 'rgb(13, 17, 23)',
      fontFamily: path ? 'system-ui, sans-serif' : '"Noto Sans JP", sans-serif',
    });
  }
});

test('the pages made for the site run under the security policy without violations', async ({
  page,
}) => {
  await page.addInitScript(() => {
    window.violations = [];
    document.addEventListener('securitypolicyviolation', (event) =>
      window.violations.push(`${event.violatedDirective} ${event.blockedURI}`),
    );
  });
  for (const path of ['', 'trailer/']) {
    const headers = (await page.goto(base + path)).headers();
    expect(headers['x-content-type-options'], path).toBe('nosniff');
    expect(headers['referrer-policy'], path).toBe('strict-origin-when-cross-origin');
    expect(headers['content-security-policy'], path).toBeDefined();
    const policy = Object.fromEntries(
      headers['content-security-policy'].split(';').map((directive) => {
        const [name, ...values] = directive.trim().split(/\s+/);
        return [name, values];
      }),
    );
    expect(policy['default-src'], path).toEqual(["'none'"]);
    // Local runs neither add the analytics script nor frame the page, so these are checked
    // by value.
    expect(policy['script-src'], path).toContain('https://static.cloudflareinsights.com');
    expect(policy['connect-src'], path).toContain('https://cloudflareinsights.com');
    for (const name of ['base-uri', 'form-action', 'frame-ancestors'])
      expect(policy[name], `${path} ${name}`).toEqual(["'none'"]);
    // Let the fonts, images and video metadata load, so any blocked request has been reported.
    await page.evaluate(() => document.fonts.ready);
    await page
      .locator('img')
      .evaluateAll((images) => Promise.all(images.map((image) => image.decode().catch(() => {}))));
    for (const video of await page.locator('video').all())
      await expect.poll(() => video.evaluate((element) => element.readyState)).toBeGreaterThan(0);
    expect(await page.evaluate(() => window.violations), path).toEqual([]);
  }
});

test('the presentation pages, and images, text or the PDF opened alone, carry no policy', async ({
  request,
}) => {
  for (const path of [
    'slides/',
    'demo/web/pyxel-run',
    'trailer/app/',
    'assets/apps/code_maker_lg.png',
    'assets/quote/book_cover.jpg',
    'assets/chr/flower.gif',
    'assets/favicon.ico',
    'pyconjp2026-keynote.pdf',
    'CREDITS.md',
    'LICENSE',
    'assets/font/OFL-NotoSansJP.txt',
  ]) {
    const headers = (await request.get(base + path)).headers();
    expect(headers['content-security-policy'], path).toBeUndefined();
    expect(headers['x-content-type-options'], path).toBe('nosniff');
    expect(headers['referrer-policy'], path).toBe('strict-origin-when-cross-origin');
  }
});

test('the share cards name a published image of the stated size', async ({ page }) => {
  for (const path of ['', 'slides/', 'trailer/', 'trailer/app/']) {
    await page.goto(base + path);
    const meta = async (name) => {
      const tag = page.locator(`meta[property="${name}"], meta[name="${name}"]`);
      await expect(tag, `${path} ${name}`).toHaveCount(1);
      return tag.getAttribute('content');
    };
    for (const name of ['og:title', 'og:description', 'og:image:alt'])
      expect(await meta(name), `${path} ${name}`).toBeTruthy();
    expect(await meta('og:type')).toBe('website');
    expect(await meta('twitter:card')).toBe('summary_large_image');
    const pageURL = new URL(await meta('og:url'));
    expect(pageURL.pathname).toBe(base + path);
    const image = new URL(await meta('og:image'));
    expect(image.origin).toBe(pageURL.origin);
    const size = [Number(await meta('og:image:width')), Number(await meta('og:image:height'))];
    await page.goto(image.pathname);
    expect(
      await page
        .locator('img')
        .evaluate((element) => [element.naturalWidth, element.naturalHeight]),
    ).toEqual(size);
  }
});

test('the PDF, licenses, trailer app and browser demo are served with fitting headers', async ({
  request,
}) => {
  const pdf = await request.get(base + 'pyconjp2026-keynote.pdf');
  expect(pdf.status()).toBe(200);
  expect(pdf.headers()['content-type']).toContain('application/pdf');
  expect(pdf.headers()['x-content-type-options']).toBe('nosniff');
  expect(pdf.headers()['referrer-policy']).toBe('strict-origin-when-cross-origin');
  expect((await pdf.body()).subarray(0, 5).toString()).toBe('%PDF-');
  // The texts are UTF-8, so their Japanese shows correctly when opened, and the packaged
  // trailer app is a ZIP archive, so it is not shown as text.
  for (const [path, type] of [
    ['CREDITS.md', 'text/markdown; charset=utf-8'],
    ['LICENSE', 'text/plain; charset=utf-8'],
    ['trailer/trailer.pyxapp', 'application/zip'],
  ]) {
    const response = await request.get(base + path);
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toBe(type);
  }
  const demo = await request.get(base + 'demo/web/pyxel-run');
  expect(demo.status()).toBe(200);
  expect(await demo.text()).toContain('<pyxel-run');
});

test('every slide video and the trailer decode, play and seek', async ({ page }) => {
  await page.goto(slides);
  const numbers = await page
    .locator('section:has(video)')
    .evaluateAll((sections) => sections.map((section) => section.id));
  expect(numbers.length).toBeGreaterThan(0);
  for (const number of numbers) {
    await page.evaluate((number) => (location.hash = '#' + number), number);
    await expect(page.locator(active)).toHaveAttribute('id', number);
    for (const video of await page.locator(active + ' video').all()) await expectToPlay(video);
  }
  await page.goto(base + 'trailer/');
  await expectToPlay(page.locator('video'));
});
