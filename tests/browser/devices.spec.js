import { expect, test } from '@playwright/test';
import { active, base, expectToPlay, slides, stubExternal } from './helpers.js';

test.beforeEach(async ({ context }) => {
  await stubExternal(context);
});

async function expectNoSideScroll(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    page.viewportSize().width,
  );
}

// Playwright can tap but not drag a finger, so the swipe is dispatched as touch events,
// which Playwright builds as real TouchEvents in each browser. Marp reads page coordinates.
async function swipeLeft(page) {
  const viewer = page.locator('svg.bespoke-marp-active');
  const { left, right, pageY } = await viewer.evaluate((svg) => {
    const box = svg.getBoundingClientRect();
    return {
      left: box.left + scrollX,
      right: box.right + scrollX,
      pageY: (box.top + box.bottom) / 2 + scrollY,
    };
  });
  for (const [type, pageX] of [
    ['touchstart', right - 40],
    ['touchmove', (left + right) / 2],
    ['touchmove', left + 40],
    ['touchend', left + 40],
  ]) {
    const touches = [{ identifier: 0, pageX, pageY }];
    await viewer.dispatchEvent(type, {
      touches: type === 'touchend' ? [] : touches,
      changedTouches: touches,
    });
  }
}

// WebKit reports pre-transform boxes for slide content, which Marp scales with a
// transform there, so the tap goes where hit testing actually finds the element.
async function tapInSlide(page, selector) {
  const point = await page.locator(selector).evaluate((target) => {
    const hits = [];
    for (let y = 0; y < innerHeight; y += 2)
      for (let x = 0; x < innerWidth; x += 2)
        if (target.contains(document.elementFromPoint(x, y))) hits.push([x, y]);
    return hits[Math.floor(hits.length / 2)];
  });
  expect(point, `${selector} must be reachable by a tap`).toBeDefined();
  await page.touchscreen.tap(...point);
}

test('the top page fits the phone and its links open with a tap', async ({ page }) => {
  await page.goto(base);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expectNoSideScroll(page);
  for (const link of await page.locator('main a').all()) {
    const box = await link.boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize().width);
  }
  await page.getByRole('link', { name: 'Slides / 講演スライド', exact: true }).tap();
  await expect(page).toHaveURL(new RegExp('/slides/$'));
});

test('slides fit the phone, load the bundled fonts and change with a swipe', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(slides + '#1');
  await expect(page.locator(active + ' h1')).toContainText('Pyxelで、プログラミングを遊ぼう！');
  await expectNoSideScroll(page);
  const viewer = await page.locator('svg.bespoke-marp-active').boundingBox();
  expect(viewer.width).toBeCloseTo(page.viewportSize().width, 0);
  // The hidden priming line in tools/slides/hl.py makes every bundled face load up front.
  await page.evaluate(() => document.fonts.ready);
  const faces = await page.evaluate(() =>
    [...document.fonts].map((face) => `${face.family} ${face.weight} ${face.status}`),
  );
  expect(faces.length).toBeGreaterThan(0);
  for (const face of faces) expect(face).toMatch(/^"?Noto Sans .+ loaded$/);
  await swipeLeft(page);
  await expect(page.locator(active + ' h1')).toContainText('今日は、Pyxelの話をします');
  await expect(page).toHaveURL(new RegExp('#2$'));
  expect(errors).toEqual([]);
});

test('a demo link on a slide opens with a tap', async ({ page }) => {
  await page.goto(slides + '#36');
  const opened = page.waitForEvent('popup');
  await tapInSlide(page, active + ' a');
  const popup = await opened;
  await expect(popup).toHaveURL(new RegExp(base + 'demo/web/pyxel-run$'));
  // pyxel.js builds its screen only after loading, so check the layout once it is there.
  await expect(popup.locator('#pyxel-screen')).toBeVisible();
  await expectNoSideScroll(popup);
  await popup.close();
});

test('slide and trailer videos fit the phone, decode and seek', async ({ page }) => {
  for (const [path, selector] of [
    [slides + '#27', active + ' video'],
    [base + 'trailer/', 'video'],
  ]) {
    await page.goto(path);
    const video = page.locator(selector).first();
    await expect(video).toBeVisible();
    await expectNoSideScroll(page);
    await expectToPlay(video);
  }
});

test('the trailer app fits the phone', async ({ page }) => {
  await page.goto(base + 'trailer/app/');
  await expect(page.locator('#pyxel-screen')).toBeVisible();
  await expectNoSideScroll(page);
});
