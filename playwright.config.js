import { defineConfig } from '@playwright/test';

const channel = process.env.KEYNOTE_BROWSER_CHANNEL ?? 'chrome';
const port = Number(process.env.KEYNOTE_BROWSER_PORT ?? 4174);
if (!Number.isInteger(port) || port < 1 || port > 65535)
  throw new Error('KEYNOTE_BROWSER_PORT must be an integer from 1 to 65535.');
const baseURL = `http://127.0.0.1:${port}`;
export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  timeout: 60000,
  use: {
    baseURL,
    ...(channel === 'chromium' ? {} : { channel }),
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `node scripts/cloudflare.js dev --local --ip 127.0.0.1 --port ${port}`,
    url:
      baseURL +
      new URL((await import('./package.json', { with: { type: 'json' } })).default.homepage)
        .pathname,
    reuseExistingServer: false,
    timeout: 60000,
  },
});
