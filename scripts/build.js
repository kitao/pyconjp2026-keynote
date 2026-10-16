import { spawnSync } from 'node:child_process';
import { cp, mkdir, mkdtemp, readFile, realpath, rename, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from 'marked';

export const root = fileURLToPath(new URL('..', import.meta.url));
const require = createRequire(import.meta.url);

export async function publication() {
  const project = JSON.parse(await readFile(join(root, 'package.json'), 'utf8'));
  const url = new URL(project.homepage);
  if (url.origin !== 'https://kitao.dev' || !/^\/[a-z0-9-]+\/$/.test(url.pathname)) {
    throw new Error('The homepage must be a single directory under https://kitao.dev/.');
  }
  return { url, base: url.pathname, directory: url.pathname.slice(1, -1) };
}

export function run(command, args, options = {}) {
  const result = spawnSync(command, args, { cwd: root, stdio: 'inherit', ...options });
  if (result.error) throw result.error;
  if (result.status !== 0)
    throw new Error(`${command} failed (${result.status ?? result.signal}).`);
}

export function relocate(html, url) {
  return html.replaceAll('https://kitao.github.io/pyconjp2026-keynote/', url.href);
}

function addFavicon(html, base) {
  return html.replace(
    '</head>',
    `<link rel="icon" href="${base}assets/favicon.ico" sizes="48x48">` +
      `<link rel="icon" href="${base}assets/favicon.svg" type="image/svg+xml" sizes="any">` +
      '</head>',
  );
}

// Only referenced presentation assets and their font licenses enter the public build.
export function assetPaths(html, base = '') {
  const paths = new Set();
  function collect(path) {
    if (base && path.startsWith(base)) path = path.slice(base.length);
    path = path.replace(/^(?:\.\.\/)+/, '');
    if (path.startsWith('assets/')) paths.add(path);
  }
  for (const match of html.matchAll(/\b(?:src|href|poster)="([^"?#]+)"/g)) {
    collect(match[1]);
  }
  for (const match of html.matchAll(/url\(\s*["']?([^"')?#]+)["']?\s*\)/g)) {
    collect(match[1]);
  }
  return [...paths].sort();
}

async function copyAsset(path, destination) {
  const source = await realpath(join(root, path));
  const assets = await realpath(join(root, 'assets'));
  if (!source.startsWith(assets + sep)) throw new Error(`Asset escapes assets/: ${path}`);
  const target = resolve(destination, path);
  if (!target.startsWith(destination + sep)) throw new Error(`Invalid asset path: ${path}`);
  await mkdir(dirname(target), { recursive: true });
  await cp(source, target);
}

export async function buildSite() {
  const { url, base, directory } = await publication();
  const stage = await mkdtemp(join(root, '.keynote-build-'));
  const site = join(stage, directory);
  try {
    await mkdir(site);
    const slidesURL = new URL('slides/', url);
    await mkdir(join(site, 'slides'));
    const htmlPath = join(site, 'slides/index.html');
    const marp = require.resolve('@marp-team/marp-cli/marp-cli.js');
    run(process.execPath, [
      marp,
      'slides.md',
      '--no-stdin',
      '--html',
      '--allow-local-files',
      '--theme-set',
      'theme/pyxel.css',
      '--template',
      'bespoke',
      '--bespoke.osc=false',
      '-o',
      htmlPath,
    ]);
    run(process.env.PYTHON || 'python3', ['tools/slides/hl.py', htmlPath]);
    const keys = await readFile(join(root, 'tools/slides/keys.js'), 'utf8');
    let html = addFavicon(relocate(await readFile(htmlPath, 'utf8'), url), base);
    html = html.replace('</body>', `<script>\n${keys}</script></body>`);
    html = html.replace(
      '</head>',
      `<link rel="canonical" href="${slidesURL.href}">` +
        `<meta property="og:url" content="${slidesURL.href}">` +
        '<meta name="description" content="PyCon JP 2026 基調講演『Pyxelで、プログラミングを遊ぼう！──「楽しく作る」をデザインする』北尾 崇 / Takashi Kitao">' +
        `<meta property="og:image" content="${url.href}assets/pyxel/logo.png">` +
        `<link rel="alternate" type="application/pdf" href="${base}pyconjp2026-keynote.pdf">` +
        '</head>',
    );
    const assets = assetPaths(html, base);
    // The viewer lives under slides/; presentation media stay at the site root.
    html = html
      .replace(
        /\b(src|href|poster)="(assets\/[^\"]+)"/g,
        (_, attribute, path) => `${attribute}="${base}${path}"`,
      )
      .replace(
        /url\(\s*(["']?)(assets\/[^"')]+)\1\s*\)/g,
        (_, quote, path) => `url(${quote}${base}${path}${quote})`,
      );
    await writeFile(htmlPath, html);
    for (const path of assets) await copyAsset(path, site);
    for (const name of ['NotoSans', 'NotoSansJP', 'NotoSansKR', 'NotoSansMono']) {
      await copyAsset(`assets/font/OFL-${name}.txt`, site);
    }
    for (const path of [
      'pyconjp2026-keynote.pdf',
      'CREDITS.md',
      'LICENSE',
      'demo/web/pyxel-run.html',
      'trailer/trailer.pyxapp',
      'trailer/trailer.mp4',
      'trailer/poster.jpg',
    ]) {
      const target = join(site, path);
      await mkdir(dirname(target), { recursive: true });
      await cp(join(root, path), target);
    }
    // A real document shell gives the embedded browser demo a title and viewport.
    const demoPath = join(site, 'demo/web/pyxel-run.html');
    const demo = await readFile(demoPath, 'utf8');
    await writeFile(
      demoPath,
      addFavicon(
        '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">' +
          '<meta name="viewport" content="width=device-width,initial-scale=1">' +
          '<title>Pyxel Web Demo — PyCon JP 2026</title></head><body>\n' +
          demo +
          '\n</body></html>\n',
        base,
      ),
    );
    for (const [template, output] of [
      ['404.html', '404.html'],
      ['trailer.html', 'trailer/index.html'],
      ['trailer-app.html', 'trailer/app/index.html'],
    ]) {
      const text = addFavicon(
        (await readFile(join(root, 'src', template), 'utf8')).replaceAll('{{BASE}}', base),
        base,
      );
      await mkdir(dirname(join(site, output)), { recursive: true });
      await writeFile(join(site, output), text);
    }
    const readme = await readFile(join(root, 'README.md'), 'utf8');
    if (!readme.includes('\n## Credits and license /'))
      throw new Error('Missing README credits section.');
    const content = marked
      .parse(readme)
      .replaceAll(url.href, base)
      .replaceAll(
        'https://kitao.github.io/pyconjp2026-keynote/pyconjp2026-keynote.pdf',
        `${base}pyconjp2026-keynote.pdf`,
      )
      .replaceAll('https://kitao.github.io/pyconjp2026-keynote/', `${base}slides/`)
      .replaceAll(
        'https://github.com/user-attachments/assets/0f094c22-4ecd-49bb-a604-561b4fcd7505',
        `${base}trailer/`,
      )
      .replaceAll('（現在の公開版）', '');
    const home = addFavicon(
      (await readFile(join(root, 'src/index.html'), 'utf8'))
        .replaceAll('{{HOME_URL}}', url.href)
        .replace('{{README}}', content),
      base,
    );
    await writeFile(join(site, 'index.html'), home);
    await writeFile(
      join(stage, '_headers'),
      `${base}*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Cache-Control: public, max-age=0, must-revalidate\n\n` +
        `${base}CREDITS.md\n  Content-Type: text/plain; charset=utf-8\n\n` +
        `${base}LICENSE\n  Content-Type: text/plain; charset=utf-8\n`,
    );
    const output = join(root, 'dist');
    const backup = stage + '-previous';
    let previous = false;
    try {
      await rename(output, backup);
      previous = true;
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
    try {
      await rename(stage, output);
    } catch (error) {
      if (previous) await rename(backup, output);
      throw error;
    }
    if (previous) await rm(backup, { recursive: true, force: true });
    console.log(`Built dist/${directory}/ (${assets.length} referenced assets).`);
  } finally {
    await rm(stage, { recursive: true, force: true });
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await buildSite();
