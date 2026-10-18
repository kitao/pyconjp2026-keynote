import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { assetPaths, copiedFiles, publication, root, templates } from './build.js';

const { url, base, directory } = await publication();

const dist = join(root, 'dist');
const site = join(dist, directory);
const read = (path) => readFile(join(site, path), 'utf8');
const slides = await read('slides/index.html');
assert.equal([...slides.matchAll(/<section\b/g)].length, 52, 'All 52 slides must be present.');
assert(slides.includes(`<link rel="canonical" href="${url.href}slides/">`));
assert(!slides.includes('kitao.github.io'), 'Slides must not link to the GitHub Pages copy.');
const home = await read('index.html');
assert(home.includes(`<link rel="canonical" href="${url.href}"`));
assert(home.includes(`href="${base}slides/"`));

// Pages as placed in dist/.
const pages = [
  ...['slides/index.html', 'demo/web/pyxel-run.html', ...Object.keys(templates)].map(
    (path) => `${directory}/${path}`,
  ),
];
let html = '';
for (const path of pages) {
  const text = await readFile(join(dist, path), 'utf8');
  assert(!/\{\{[A-Z]+\}\}/.test(text), `Template placeholder left in ${path}`);
  html += text;
}
const published = [...assetPaths(html, base), ...copiedFiles];
const expected = new Set([
  '_headers',
  ...pages,
  ...published.map((path) => `${directory}/${path}`),
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
      assert(expected.delete(relative), `Unexpected public file: ${relative}`);
      const { size } = await stat(join(dist, relative));
      assert(size <= 25 * 1024 * 1024, `Asset exceeds Cloudflare's 25 MiB limit: ${relative}`);
      files++;
      bytes += size;
    }
  }
}
const found = new Set(expected);
await inspect();
assert.equal(expected.size, 0, `Missing public files: ${[...expected].join(', ')}`);
// Every link a page makes into the site must reach a published file.
const links =
  /\b(?:src|href|poster)="([^"]+)"|<meta property="og:(?:image|url)" content="([^"]+)"/g;
for (const path of pages) {
  const page = new URL('/' + path.replace(/(^|\/)index\.html$/, '$1'), url);
  for (const [, attribute, meta] of (await readFile(join(dist, path), 'utf8')).matchAll(links)) {
    const value = attribute ?? meta;
    const target = new URL(value, page);
    if (target.origin !== url.origin || !target.pathname.startsWith(base)) continue;
    let file = decodeURI(target.pathname.slice(base.length));
    if (file === '' || file.endsWith('/')) file += 'index.html';
    assert(found.has(`${directory}/${file}`), `${path} links to a missing file: ${value}`);
  }
}
// License texts travel with the fonts and materials they cover, linked or not.
const fonts = await readdir(join(root, 'assets/font'));
for (const path of [
  'LICENSE',
  'CREDITS.md',
  'trailer/LICENSE-MPLUS.txt',
  ...fonts.filter((name) => /^OFL-.+\.txt$/.test(name)).map((name) => `assets/font/${name}`),
])
  assert(published.includes(path), `License text not published: ${path}`);
// The PDF, the packaged trailer and every asset are published byte for byte.
for (const path of published) {
  assert((await readFile(join(root, path))).equals(await readFile(join(site, path))), path);
}
console.log(`Checked ${files} public files (${(bytes / 1024 / 1024).toFixed(1)} MiB), 52 slides.`);
