import assert from 'node:assert/strict';
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { assetPaths, publish } from '../scripts/build.js';

function fixture(t) {
  // macOS tmpdir() sits behind a symlink, which a source root itself may do.
  const work = mkdtempSync(join(tmpdir(), 'keynote-build-'));
  t.after(() => rmSync(work, { recursive: true, force: true }));
  const source = join(work, 'source');
  mkdirSync(join(source, 'assets/pyxel'), { recursive: true });
  writeFileSync(join(source, 'assets/pyxel/logo.png'), 'logo');
  writeFileSync(join(work, 'private.txt'), 'outside the source tree');
  return { source, out: join(work, 'out'), outside: join(work, 'private.txt') };
}

test('referenced assets are collected from attributes and CSS, without queries or fragments', () => {
  const html =
    '<img src="/k/assets/a.png?v=1"><video poster="assets/b.png#t" src="https://x.test/assets/c.mp4">' +
    '<a href="/k/slides/">x</a><div style="background:url( \'/k/assets/d.gif\' )"></div>' +
    '<i style="background:url(assets/e.svg)"></i><link href="/k/style.css">';
  assert.deepEqual(assetPaths(html, '/k/'), [
    'assets/a.png',
    'assets/b.png',
    'assets/d.gif',
    'assets/e.svg',
  ]);
});

test('a regular source file is published unchanged', async (t) => {
  const { source, out } = fixture(t);
  const site = join(out, 'site');
  await publish('assets/pyxel/logo.png', site, source);
  assert.equal(readFileSync(join(site, 'assets/pyxel/logo.png'), 'utf8'), 'logo');
});

test('symlinks, case mismatches and paths leaving the tree are never published', async (t) => {
  const { source, out, outside } = fixture(t);
  symlinkSync(outside, join(source, 'assets/link.txt'));
  symlinkSync(join(source, 'assets/pyxel'), join(source, 'assets/alias'));
  const invalid = /^Invalid public path/;
  const aliased = /^Public files must not be symlinks or differ in letter case/;
  for (const [path, error] of [
    ['assets/link.txt', aliased],
    ['assets/alias/logo.png', aliased],
    // Cloudflare matches paths case-sensitively even where the disk does not; on a
    // case-sensitive disk the misspelt file simply does not exist.
    [
      'assets/Pyxel/logo.png',
      existsSync(join(source, 'assets/Pyxel/logo.png')) ? aliased : /ENOENT/,
    ],
    ['assets/../../private.txt', invalid],
    ['../private.txt', invalid],
    ['..', invalid],
    ['./assets/pyxel/logo.png', invalid],
    ['assets//pyxel/logo.png', invalid],
    [outside, invalid],
  ]) {
    await assert.rejects(publish(path, join(out, 'site'), source), { message: error }, path);
  }
  assert.equal(existsSync(out), false);
});
