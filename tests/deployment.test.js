import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { experimental_readRawConfig } from 'wrangler';
import { copiedFiles, publication, root, templates } from '../scripts/build.js';

const { rawConfig: config } = experimental_readRawConfig({ config: join(root, 'wrangler.jsonc') });

test('a dedicated Worker serves only the built site under the homepage', async () => {
  const { url, base } = await publication();
  const { $schema, compatibility_date: compatibilityDate, build, ...deployment } = config;
  assert.equal($schema, './node_modules/wrangler/config-schema.json');
  assert.match(compatibilityDate, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(build.command, 'node scripts/build.js && node scripts/check.js');
  // Only MP4 requests run Worker code; the presentation and pages stay static.
  assert.deepEqual(deployment, {
    name: 'pyconjp2026-keynote',
    workers_dev: false,
    preview_urls: false,
    // Route matching includes the query, so only a pattern ending in * also takes the bare
    // path with a query string.
    routes: [{ pattern: url.host + base.slice(0, -1) + '*', zone_name: url.host }],
    main: 'src/worker.js',
    assets: {
      directory: './dist',
      binding: 'ASSETS',
      run_worker_first: [base + '*.mp4'],
    },
  });
});

test('wrangler dev rebuilds when a file the build reads changes, but not on its own output', () => {
  const watched = config.build.watch_dir;
  for (const path of watched) assert(existsSync(join(root, path)), `Not found: ${path}`);
  assert(!watched.some((path) => /^dist(\/|$)/.test(path)), 'dist/ must not be watched');
  const covered = (file) => watched.some((path) => file === path || file.startsWith(path + '/'));
  for (const file of [
    'package.json',
    'README.md',
    'slides.md',
    'theme/pyxel.css',
    'demo/web/pyxel-run.html',
    'tools/slides/hl.py',
    'tools/slides/keys.js',
    'scripts/build.js',
    ...copiedFiles,
    'src/_headers',
    ...Object.values(templates).map((template) => `src/${template}`),
  ])
    assert(covered(file), `Not watched: ${file}`);
});

test('video ranges return the exact requested bytes, sizes and validators', async () => {
  const { default: worker } = await import('../src/worker.js');
  const body = '0123456789';
  const env = {
    ASSETS: {
      async fetch(request) {
        assert.equal(request.method, 'GET');
        assert.equal(request.headers.has('Range'), false);
        assert.equal(request.headers.has('If-Range'), false);
        return new Response(body, {
          headers: { 'Content-Type': 'video/mp4', ETag: '"current"' },
        });
      },
    },
  };
  for (const [range, status, expected, contentRange] of [
    [undefined, 200, body, null],
    ['bytes=2-5', 206, '2345', 'bytes 2-5/10'],
    ['bytes=7-', 206, '789', 'bytes 7-9/10'],
    ['bytes=-3', 206, '789', 'bytes 7-9/10'],
    ['bytes=-99', 206, body, 'bytes 0-9/10'],
    ['bytes=7-99', 206, '789', 'bytes 7-9/10'],
    ['bytes=10-', 416, '', 'bytes */10'],
    ['bytes=5-2', 416, '', 'bytes */10'],
    ['bytes=-0', 416, '', 'bytes */10'],
    ['bytes=999999999999999999999-', 416, '', 'bytes */10'],
    ['bytes=0-1,4-5', 200, body, null],
    ['bytes=-', 200, body, null],
    ['invalid', 200, body, null],
  ]) {
    const request = new Request('https://kitao.dev/video.mp4', {
      headers: range ? { Range: range } : {},
    });
    const response = await worker.fetch(request, env);
    assert.equal(response.status, status, range);
    assert.equal(response.headers.get('Content-Range'), contentRange, range);
    assert.equal(response.headers.get('Content-Length'), String(expected.length), range);
    assert.equal(response.headers.get('Accept-Ranges'), 'bytes');
    assert.equal(response.headers.get('Content-Type'), 'video/mp4');
    assert.equal(await response.text(), expected, range);
  }
  for (const [validator, status] of [
    ['"current"', 206],
    ['"old"', 200],
    ['W/"current"', 200],
  ]) {
    const response = await worker.fetch(
      new Request('https://kitao.dev/video.mp4', {
        headers: { Range: 'bytes=2-5', 'If-Range': validator },
      }),
      env,
    );
    assert.equal(response.status, status);
  }
  const head = await worker.fetch(
    new Request('https://kitao.dev/video.mp4', {
      method: 'HEAD',
      headers: { Range: 'bytes=2-5' },
    }),
    env,
  );
  assert.equal(head.status, 200);
  assert.equal(head.headers.get('Content-Length'), '10');
  assert.equal(await head.text(), '');
  for (const status of [304, 404, 405]) {
    const response = await worker.fetch(new Request('https://kitao.dev/video.mp4'), {
      ASSETS: { fetch: async () => new Response(null, { status }) },
    });
    assert.equal(response.status, status);
  }
});
