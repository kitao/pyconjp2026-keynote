# Build and publication / ビルドと公開

## Build and preview / ビルドと確認

Node.js 24+ and Python 3.9+ are required. / Node.js 24 以降と Python 3.9 以降が必要です。

```sh
npm ci
npm run dev
```

Open <http://127.0.0.1:4173/pyconjp2026-keynote/> for the material overview, then choose Slides to open `/slides/`. The preview uses Cloudflare's local runtime, including redirects, headers, 404s, and video playback. Stop it before running the checks or a deploy, which rebuild the same `dist/`.

上記の URL で README に基づいた資料のトップページを確認できます。スライドは `/slides/` に置いています。プレビューは Cloudflare のローカル環境で動き、リダイレクト・ヘッダー・404・動画再生も確認できます。検査や公開も同じ `dist/` を作り直すため、その前に `npm run dev` を止めてください。

```sh
npm run check          # Formatting, tests, build, public-file checks, and browser tests
npm run test:browser   # Chrome and WebKit: slides, links, PDF, video, and phone layouts
npm run deploy:check   # Validate the Cloudflare configuration without publishing
```

Browser tests use installed Google Chrome, and Playwright's WebKit (`npx playwright install webkit`) for the iPhone emulation. To use Playwright's Chromium instead, run `npx playwright install chromium` and set `KEYNOTE_BROWSER_CHANNEL=chromium`.

ブラウザ検査はインストール済みの Google Chrome を使い、iPhone のエミュレーションには Playwright の WebKit（`npx playwright install webkit`）を使います。Playwright の Chromium を使う場合は `npx playwright install chromium` で準備し、`KEYNOTE_BROWSER_CHANNEL=chromium` を指定してください。

Browser tests start their own server on port 4174, separate from the preview on 4173. Set `KEYNOTE_BROWSER_PORT` if that test port is occupied.

ブラウザ検査は、プレビュー用の 4173 と別に、4174 で専用サーバーを起動します。検査用ポートが使用中の場合は `KEYNOTE_BROWSER_PORT` を指定してください。

| Source / 元資料                           | Purpose / 用途                                                                        |
| ----------------------------------------- | ------------------------------------------------------------------------------------- |
| `slides.md`, `theme/pyxel.css`, `assets/` | Slide content, theme, and media / スライド本文・テーマ・素材                          |
| `index.html`, `pyconjp2026-keynote.pdf`   | Archived presentation and handout / 発表時の HTML と配布 PDF                          |
| `demo/`, `trailer/`, `tools/`             | Demos, trailer, and production tools / デモ・トレーラー・制作ツール                   |
| `src/`, `scripts/`, `tests/`              | Web pages, build/deploy commands, and checks / 公開ページ・ビルドと公開の手順・検査   |
| `dist/pyconjp2026-keynote/`               | Generated Cloudflare assets; ignored by Git / Cloudflare 用の生成物（Git 管理対象外） |

`npm run build` renders the entire README as the top page, and rebuilds the web slides under `slides/` with pinned Marp dependencies and the existing typography and keyboard processing. It updates web links in the generated HTML and copies only referenced assets, licenses, the PDF, the browser demo, and the packaged trailer. The archived HTML and PDF stay intact. Use the existing `tools/slides/build.sh` when deliberately exporting a new handout.

`npm run build` は README 全体からトップページを生成し、`slides/` に Web 版スライドを置きます。固定した Marp の依存関係と既存の組版・キー操作処理を使って Web 版を生成します。生成 HTML のリンクを公開先に合わせ、参照素材・ライセンス・PDF・ブラウザデモ・完成したトレーラーを `dist/` に集めます。発表時の HTML と PDF は保管します。配布 PDF を作り直す場合は既存の `tools/slides/build.sh` を使います。

## Cloudflare publication / Cloudflare への公開

The publication target is **<https://kitao.dev/pyconjp2026-keynote/>**, using a dedicated Worker with Static Assets. Building prepares the files without publishing them. `wrangler.jsonc` limits the routes to that path; `package.json` holds its canonical URL. When changing the target, update both and run the checks.

公開先は **<https://kitao.dev/pyconjp2026-keynote/>** です。専用 Worker の Static Assets で配信します。ビルドは公開ファイルを生成するだけで、公開先には反映しません。`wrangler.jsonc` の配信範囲と `package.json` の公開 URL を揃え、変更後は検査を実行してください。

The root route ends in a wildcard so Cloudflare matches slashless URLs with query strings. Public files remain in the `pyconjp2026-keynote/` subtree. The trailer app loads its packaged file from this site, using the pinned Pyxel runtime on `kitao.dev`.

Cloudflare が末尾スラッシュなし・クエリ付きの URL にも一致するよう、ルートの指定には末尾のワイルドカードを使います。公開ファイルは `pyconjp2026-keynote/` 配下にまとめています。トレーラーアプリはこのサイトのアプリファイルと、`kitao.dev` の固定した Pyxel ランタイムで起動します。

After approving the target and built content, publish locally with:

公開先と生成内容を確認・承認した後、ローカルから公開します。

```sh
npm run deploy
```

The command runs checks and browser tests before deploying. It forces Cloudflare OAuth's OS-keychain-backed storage and refuses API token/key environment variables. An unavailable keychain stops the operation instead of falling back to plaintext. CI only builds and checks; it does not deploy or require Cloudflare credentials.

公開コマンドは検査とブラウザ確認を実行してからデプロイします。Cloudflare OAuth のキーチェーンを使う保存方式を必須とし、API トークン・キーの環境変数は拒否します。キーチェーンを利用できなければ停止し、平文保存へ切り替えません。CI はビルドと検査のみで、Cloudflare の認証情報を必要としません。

After each deployment, verify the live top page, slides, PDF, demo, trailer, redirects, 404s, and video range responses. The local runtime returns a full response for video range requests; partial transfers require a live check. Existing QR codes and the archived PDF link to GitHub Pages, so retain that distribution path for previously shared materials.

公開後は実際のトップページ・スライド・PDF・デモ・トレーラー・リダイレクト・404・動画の部分配信を確認します。ローカル環境は動画の Range 要求に全体を返すため、部分配信は公開後に確認が必要です。既存の QR コードと配布 PDF は GitHub Pages を参照しているため、配布済み資料のリンク先を維持してください。
