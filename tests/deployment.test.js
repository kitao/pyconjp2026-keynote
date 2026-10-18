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
  // An exact match also rejects additions such as "main", which would run Worker code.
  assert.deepEqual(deployment, {
    name: 'pyconjp2026-keynote',
    workers_dev: false,
    preview_urls: false,
    // Route matching includes the query, so only a pattern ending in * also takes the bare
    // path with a query string.
    routes: [{ pattern: url.host + base.slice(0, -1) + '*', zone_name: url.host }],
    assets: { directory: './dist' },
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
