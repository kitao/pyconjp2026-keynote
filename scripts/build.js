import { spawnSync } from 'node:child_process';
import { realpathSync } from 'node:fs';
import { cp, mkdir, mkdtemp, readFile, realpath, rename, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from 'marked';

export const root = fileURLToPath(new URL('..', import.meta.url));
const talk =
  'PyCon JP 2026 基調講演『Pyxelで、プログラミングを遊ぼう！──「楽しく作る」をデザインする』';

// Published as they are, next to the slides' referenced assets.
export const copiedFiles = [
  'pyconjp2026-keynote.pdf',
  'CREDITS.md',
  'LICENSE',
  'assets/font/OFL-NotoSans.txt',
  'assets/font/OFL-NotoSansJP.txt',
  'assets/font/OFL-NotoSansKR.txt',
  'assets/font/OFL-NotoSansMono.txt',
  'trailer/trailer.pyxapp',
  'trailer/LICENSE-MPLUS.txt',
  'trailer/trailer.mp4',
  'trailer/poster.jpg',
];

// Published file -> template in src/.
export const templates = {
  'index.html': 'index.html',
  'style.css': 'style.css',
  'trailer/index.html': 'trailer.html',
  'trailer/app/index.html': 'trailer-app.html',
};

export async function publication() {
  const project = JSON.parse(await readFile(join(root, 'package.json'), 'utf8'));
  const url = new URL(project.homepage);
  if (url.origin !== 'https://kitao.dev' || !/^\/[a-z0-9-]+\/$/.test(url.pathname)) {
    throw new Error('The homepage must be a single directory under https://kitao.dev/.');
  }
  return { url, base: url.pathname, directory: url.pathname.slice(1, -1) };
}

function run(command, args) {
  const result = spawnSync(command, args, { cwd: root, stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0)
    throw new Error(`${command} failed (${result.status ?? result.signal}).`);
}

function addFavicon(html, base) {
  return html.replace(
    '</head>',
    `<link rel="icon" href="${base}assets/favicon.ico" sizes="48x48">` +
      `<link rel="icon" href="${base}assets/favicon.svg" type="image/svg+xml" sizes="any">` +
      '</head>',
  );
}

// Only the presentation assets the slides and pages reference enter the public build.
export function assetPaths(html, base) {
  const paths = new Set();
  for (const [, reference] of [
    ...html.matchAll(/\b(?:src|href|poster)="([^"]+)"/g),
    ...html.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/g),
  ]) {
    const path = reference.replace(/[?#].*/, '');
    const relative = path.startsWith(base) ? path.slice(base.length) : path;
    if (relative.startsWith('assets/')) paths.add(relative);
  }
  return [...paths].sort();
}

// Cloudflare follows symlinks and matches paths case-sensitively, so a source
// must be a regular path spelled exactly as it is on disk.
export async function publish(path, site, source = root) {
  if (path.split('/').some((part) => ['', '.', '..'].includes(part)))
    throw new Error(`Invalid public path: ${path}`);
  if ((await realpath(join(source, path))) !== join(await realpath(source), path))
    throw new Error(`Public files must not be symlinks or differ in letter case: ${path}`);
  const target = join(site, path);
  await mkdir(dirname(target), { recursive: true });
  await cp(join(source, path), target);
}

async function buildSlides(url, base, site) {
  const htmlPath = join(site, 'slides/index.html');
  run(process.execPath, [
    createRequire(import.meta.url).resolve('@marp-team/marp-cli/marp-cli.js'),
    'slides.md',
    '--no-stdin',
    '--html',
    '--theme-set',
    'theme/pyxel.css',
    '--template',
    'bespoke',
    '--bespoke.osc=false',
    '-o',
    htmlPath,
  ]);
  run('python3', ['tools/slides/hl.py', htmlPath]);
  const keys = await readFile(join(root, 'tools/slides/keys.js'), 'utf8');
  const slidesURL = new URL('slides/', url);
  const html = addFavicon(await readFile(htmlPath, 'utf8'), base)
    .replace(
      '<meta name="twitter:card" content="summary">',
      '<meta name="twitter:card" content="summary_large_image">',
    )
    // The slide links into this repository's GitHub Pages copy stay on the current host.
    .replaceAll('href="https://kitao.github.io/pyconjp2026-keynote/', `href="${base}`)
    .replace('</body>', () => `<script>\n${keys}</script></body>`)
    .replace(
      '</head>',
      `<link rel="canonical" href="${slidesURL.href}">` +
        `<meta property="og:url" content="${slidesURL.href}">` +
        `<meta name="description" content="${talk}北尾 崇 / Takashi Kitao">` +
        `<meta property="og:description" content="${talk}北尾 崇 / Takashi Kitao">` +
        `<meta property="og:image" content="${url.href}trailer/poster.jpg">` +
        '<meta property="og:image:width" content="1280">' +
        '<meta property="og:image:height" content="720">' +
        '<meta property="og:image:alt" content="The talk title over a pixel-art night sea">' +
        `<link rel="alternate" type="application/pdf" href="${base}pyconjp2026-keynote.pdf">` +
        '</head>',
    )
    // The viewer lives under slides/; presentation media stay at the site root.
    .replace(/\b(src|href|poster)="(assets\/[^"]+)"/g, `$1="${base}$2"`)
    .replace(/url\(\s*(["']?)(assets\/[^"')]+)\1\s*\)/g, `url($1${base}$2$1)`);
  await writeFile(htmlPath, html);
  return html;
}

async function buildPages(url, base, site) {
  const readme = marked
    .parse(await readFile(join(root, 'README.md'), 'utf8'))
    .replaceAll(url.href, base);
  const rendered = [];
  for (const [output, template] of Object.entries(templates)) {
    let text = (await readFile(join(root, 'src', template), 'utf8'))
      .replaceAll('{{TALK}}', talk)
      .replaceAll('{{URL}}', url.href)
      .replaceAll('{{BASE}}', base)
      .replace('{{README}}', () => readme);
    if (output.endsWith('.html')) text = addFavicon(text, base);
    await mkdir(dirname(join(site, output)), { recursive: true });
    await writeFile(join(site, output), text);
    rendered.push(text);
  }
  // The slides link to this fragment, which GitHub Pages serves as it is; a real document
  // shell gives the kitao.dev copy a title and viewport, unchanged since it was first published.
  const demo = await readFile(join(root, 'demo/web/pyxel-run.html'), 'utf8');
  const shell = addFavicon(
    '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">' +
      '<meta name="viewport" content="width=device-width,initial-scale=1">' +
      '<title>Pyxel Web Demo — PyCon JP 2026</title></head><body>\n' +
      demo +
      '\n</body></html>\n',
    base,
  );
  await mkdir(join(site, 'demo/web'), { recursive: true });
  await writeFile(join(site, 'demo/web/pyxel-run.html'), shell);
  rendered.push(shell);
  return rendered.join('\n');
}

async function buildSite() {
  const { url, base, directory } = await publication();
  const stage = await mkdtemp(join(root, '.keynote-build-'));
  const site = join(stage, directory);
  try {
    await mkdir(join(site, 'slides'), { recursive: true });
    const slides = await buildSlides(url, base, site);
    const pages = await buildPages(url, base, site);
    await cp(join(root, 'src/_headers'), join(stage, '_headers'));
    const assets = assetPaths(slides + pages, base);
    for (const path of [...assets, ...copiedFiles]) await publish(path, site);
    // Swap the finished build into place so a failed build leaves the previous dist/ intact.
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
      // Put the previous build back; if that fails as well, the first error is still the one reported.
      if (previous) await rename(backup, output).catch(() => {});
      throw error;
    }
    if (previous) await rm(backup, { recursive: true, force: true });
    console.log(`Built dist/${directory}/ (${assets.length} referenced assets).`);
  } finally {
    await rm(stage, { recursive: true, force: true });
  }
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url))
  await buildSite();
