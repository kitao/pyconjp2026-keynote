import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { assetPaths, publication, root } from './build.js';

const { url, base, directory } = await publication();
// This config deliberately uses JSON's subset of JSONC so the target is checked without extra tooling.
const config = JSON.parse(await readFile(join(root, 'wrangler.jsonc'), 'utf8'));
assert.equal(config.name, 'pyconjp2026-keynote');
assert.equal(config.workers_dev, false);
assert.equal(config.preview_urls, false);
assert.deepEqual(config.routes, [
  { pattern: url.host + base.slice(0, -1) + '*', zone_name: url.host },
  { pattern: url.host + base + '*', zone_name: url.host },
]);
assert.equal(config.assets.directory, './dist');
assert.equal(config.assets.not_found_handling, '404-page');
assert.equal(config.assets.html_handling, 'auto-trailing-slash');

const dist = join(root, 'dist');
const site = join(dist, directory);
const home = await readFile(join(site, 'index.html'), 'utf8');
const html = await readFile(join(site, 'slides/index.html'), 'utf8');
assert.equal([...html.matchAll(/<section\b/g)].length, 52, 'All 52 slides must be present.');
assert(html.includes(`<link rel="canonical" href="${url.href}slides/">`));
assert(home.includes(`rel="canonical" href="${url.href}"`));
assert(home.includes(`href="${base}slides/"`));
assert(!home.includes('bespoke-marp-slide'));
assert(!home.includes('npm run'));
assert(!html.includes('https://kitao.github.io/pyconjp2026-keynote/'));
assert(!html.includes('https://kitao.github.io/pyxel/web/'));
const allowed = new Set([
  '_headers',
  ...assetPaths(html, base).map((path) => `${directory}/${path}`),
  ...['NotoSans', 'NotoSansJP', 'NotoSansKR', 'NotoSansMono'].map(
    (name) => `${directory}/assets/font/OFL-${name}.txt`,
  ),
  ...[
    'index.html',
    'slides/index.html',
    '404.html',
    'pyconjp2026-keynote.pdf',
    'CREDITS.md',
    'LICENSE',
    'demo/web/pyxel-run.html',
    'trailer/index.html',
    'trailer/app/index.html',
    'trailer/trailer.pyxapp',
    'trailer/trailer.mp4',
    'trailer/poster.jpg',
  ].map((path) => `${directory}/${path}`),
]);
let files = 0;
let bytes = 0;
async function inspect(path = '') {
  for (const entry of await readdir(join(dist, path), { withFileTypes: true })) {
    const relative = path ? `${path}/${entry.name}` : entry.name;
    assert(!entry.isSymbolicLink(), `Symlink in public output: ${relative}`);
    if (entry.isDirectory()) {
      await inspect(relative);
    } else {
      assert(allowed.delete(relative), `Unexpected public file: ${relative}`);
      const info = await stat(join(dist, relative));
      assert(info.size <= 25 * 1024 * 1024, `Asset exceeds Cloudflare's 25 MiB limit: ${relative}`);
      files++;
      bytes += info.size;
    }
  }
}
await inspect();
assert.equal(allowed.size, 0, `Missing public files: ${[...allowed].join(', ')}`);
assert(files <= 20000);
// The PDF and packaged trailer remain the delivered artifacts, byte for byte.
for (const path of ['pyconjp2026-keynote.pdf', 'trailer/trailer.pyxapp', 'trailer/trailer.mp4']) {
  assert((await readFile(join(root, path))).equals(await readFile(join(site, path))), path);
}
console.log(`Checked ${files} public files (${(bytes / 1024 / 1024).toFixed(1)} MiB), 52 slides.`);
