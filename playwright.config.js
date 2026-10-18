import { defineConfig, devices } from '@playwright/test';
import project from './package.json' with { type: 'json' };

const port = Number(process.env.KEYNOTE_BROWSER_PORT ?? 4174);
if (!Number.isInteger(port) || port < 1 || port > 65535)
  throw new Error('KEYNOTE_BROWSER_PORT must be an integer from 1 to 65535.');
const baseURL = `http://127.0.0.1:${port}`;
// A fake audio output keeps video playback independent of the machine's sound device.
const chromium = { launchOptions: { args: ['--disable-audio-output'] } };

export default defineConfig({
  testDir: './tests/browser',
  fullyParallel: true,
  // A stray test.only must never let the pre-deploy check pass with skipped tests.
  forbidOnly: true,
  workers: 2,
  use: { baseURL, trace: 'retain-on-failure' },
  // wrangler dev builds and checks dist/ (see wrangler.jsonc) and serves it as Cloudflare
  // would, with _headers, so the tests cover the files a deploy publishes.
  webServer: {
    command: `node scripts/wrangler.mjs dev --port ${port}`,
    url: baseURL + new URL(project.homepage).pathname,
    timeout: 120_000,
    // SIGTERM lets Wrangler stop workerd and remove its temporary files.
    gracefulShutdown: { signal: 'SIGTERM', timeout: 10_000 },
  },
  projects: [
    {
      name: 'desktop',
      testIgnore: 'devices.spec.js',
      use: { ...chromium, viewport: { width: 1440, height: 900 } },
    },
    // Phone profiles: mobile user agent, touch input, small viewport and high pixel density.
    { name: 'iphone', testMatch: 'devices.spec.js', use: devices['iPhone 17'] },
    { name: 'android', testMatch: 'devices.spec.js', use: { ...devices['Pixel 9'], ...chromium } },
  ],
});
