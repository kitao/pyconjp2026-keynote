import { expect } from '@playwright/test';
import project from '../../package.json' with { type: 'json' };

export const base = new URL(project.homepage).pathname;
export const slides = base + 'slides/';
export const active = 'svg.bespoke-marp-active section';

// The badges and Google Fonts are answered with stand-ins, so the tests do not depend on
// those services, and the pages fall back to local fonts. The stand-in stylesheet loads its
// font from fonts.gstatic.com as the real one does, so font-src stays under test.
export async function stubExternal(context) {
  await context.route(/^https:\/\/(img\.shields\.io|ko-fi\.com\/img)\//, (route) =>
    route.fulfill({
      contentType: 'image/svg+xml',
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="20"/>',
    }),
  );
  await context.route(/^https:\/\/fonts\.googleapis\.com\//, (route) =>
    route.fulfill({
      contentType: 'text/css',
      body: "@font-face { font-family: 'Noto Sans JP'; src: url(https://fonts.gstatic.com/s/stand-in.woff2); }",
    }),
  );
  await context.route(/^https:\/\/fonts\.gstatic\.com\//, (route) =>
    route.fulfill({ contentType: 'font/woff2', body: '' }),
  );
}

// Starts a video muted, as phones only start sound on a user gesture, and waits until it
// presents a frame past the start, which shows that it decodes and its clock runs; a decode
// error or a stalled load fails with its reason.
export async function expectToPlay(video) {
  const outcome = await video.evaluate(
    (element) =>
      new Promise((resolve) => {
        const stalled = setTimeout(() => resolve(`stalled at ${element.readyState}`), 10000);
        const finish = (result) => {
          clearTimeout(stalled);
          element.pause();
          resolve(result);
        };
        const onFrame = (now, frame) => {
          if (frame.mediaTime > 0) finish('playing');
          else element.requestVideoFrameCallback(onFrame);
        };
        if (element.error) finish(`error ${element.error.code}`);
        element.addEventListener('error', () => finish(`error ${element.error.code}`));
        element.requestVideoFrameCallback(onFrame);
        element.muted = true;
        element.play().catch((error) => finish(`play() rejected: ${error.name}`));
      }),
  );
  expect(outcome).toBe('playing');
  for (const fraction of [0.75, 0.25]) {
    const target = await video.evaluate((element, fraction) => {
      const target = element.duration * fraction;
      element.currentTime = target;
      return target;
    }, fraction);
    await expect
      .poll(() =>
        video.evaluate(
          (element, target) =>
            !element.seeking &&
            element.readyState >= 2 &&
            Math.abs(element.currentTime - target) < 0.1,
          target,
        ),
      )
      .toBe(true);
  }
}
