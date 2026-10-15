import { defineConfig } from '@playwright/test';

const channel = process.env.KEYNOTE_BROWSER_CHANNEL ?? 'chrome';
export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  timeout: 60000,
  use: {
    baseURL: 'http://127.0.0.1:4173',
    ...(channel === 'chromium' ? {} : { channel }),
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run preview',
    url:
      'http://127.0.0.1:4173' +
      new URL((await import('./package.json', { with: { type: 'json' } })).default.homepage)
        .pathname,
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
});
