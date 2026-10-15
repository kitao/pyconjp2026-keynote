# PyCon JP 2026 Keynote / 基調講演

Slides and materials for the PyCon JP 2026 keynote "Let’s Play Programming with Pyxel! — Designing the Fun of Making", given by [Takashi Kitao](https://x.com/kitao) on 22 August 2026 at the Hiroshima International Conference Center, Phoenix Hall.

PyCon JP 2026 基調講演『Pyxelで、プログラミングを遊ぼう！──「楽しく作る」をデザインする』（[北尾 崇](https://x.com/kitao)、2026年8月22日、広島国際会議場 フェニックスホール）の発表資料です。

- **[Pyxel](https://kitao.dev/pyxel/)** — Retro game engine for Python / Python向けレトロゲームエンジン
- **[Slides / 講演スライド](https://kitao.dev/pyconjp2026-keynote/slides/)**
- **[PDF / スライドのPDF版](https://kitao.dev/pyconjp2026-keynote/pyconjp2026-keynote.pdf)**
- **[Trailer app / トレーラーアプリ](https://kitao.dev/pyxel/launcher/?play=kitao/pyconjp2026-keynote/main/trailer/trailer)** — Runs in your browser / ブラウザで動きます
- **[Trailer video / トレーラー動画](https://kitao.dev/pyconjp2026-keynote/trailer/)**

## Build and preview / ビルドと確認

Node.js 24+ and Python 3 are required. / Node.js 24 以降と Python 3 が必要です。

```sh
npm ci
npm run dev
```

Open <http://127.0.0.1:4173/pyconjp2026-keynote/> for the material overview, then choose Slides to open `/slides/`. The preview uses Cloudflare's local runtime, including redirects, headers, 404s, and video playback.

上記の URL で README に基づいた資料のトップページを確認できます。スライドは `/slides/` に置いています。プレビューは Cloudflare のローカル環境で動き、リダイレクト・ヘッダー・404・動画再生も確認できます。

```sh
npm run check          # Formatting, tests, build, and public-file checks
npm run test:browser   # Chrome: slides, links, PDF, video, and phone-width layout
npm run deploy:check   # Validate the Cloudflare configuration without publishing
```

Browser tests use installed Google Chrome. To use Playwright's Chromium instead, run `npx playwright install chromium` and set `KEYNOTE_BROWSER_CHANNEL=chromium`.

ブラウザ検査はインストール済みの Google Chrome を使います。Playwright の Chromium を使う場合は `npx playwright install chromium` で準備し、`KEYNOTE_BROWSER_CHANNEL=chromium` を指定してください。

| Source / 元資料                           | Purpose / 用途                                                                        |
| ----------------------------------------- | ------------------------------------------------------------------------------------- |
| `slides.md`, `theme/pyxel.css`, `assets/` | Slide content, theme, and media / スライド本文・テーマ・素材                          |
| `index.html`, `pyconjp2026-keynote.pdf`   | Archived presentation and handout / 発表時の HTML と配布 PDF                          |
| `demo/`, `trailer/`, `tools/`             | Demos, trailer, and production tools / デモ・トレーラー・制作ツール                   |
| `src/`, `scripts/`, `tests/`              | Web pages, build/deploy commands, and checks / 公開ページ・ビルドと公開の手順・検査   |
| `dist/pyconjp2026-keynote/`               | Generated Cloudflare assets; ignored by Git / Cloudflare 用の生成物（Git 管理対象外） |

`npm run build` renders the README introduction and credits as the top page, and rebuilds the web slides under `slides/` with pinned Marp dependencies and the existing typography and keyboard processing. It updates web links in the generated HTML and copies only referenced assets, licenses, the PDF, the browser demo, and the packaged trailer. The archived HTML and PDF stay intact. Use the existing `tools/slides/build.sh` when deliberately exporting a new handout.

`npm run build` は README の講演紹介・資料リンク・権利表示からトップページを生成し、`slides/` に Web 版スライドを置きます。固定した Marp の依存関係と既存の組版・キー操作処理を使って Web 版を生成します。生成 HTML のリンクを公開先に合わせ、参照素材・ライセンス・PDF・ブラウザデモ・完成したトレーラーを `dist/` に集めます。発表時の HTML と PDF は保管します。配布 PDF を作り直す場合は既存の `tools/slides/build.sh` を使います。

## Cloudflare publication / Cloudflare への公開

The publication target is **<https://kitao.dev/pyconjp2026-keynote/>**, using a dedicated Worker with Static Assets. Building prepares the files without publishing them. `wrangler.jsonc` limits the routes to that path; `package.json` holds its canonical URL. When changing the target, update both and run the checks.

公開先は **<https://kitao.dev/pyconjp2026-keynote/>** です。専用 Worker の Static Assets で配信します。ビルドは公開ファイルを生成するだけで、公開先には反映しません。`wrangler.jsonc` の配信範囲と `package.json` の公開 URL を揃え、変更後は検査を実行してください。

After approving the target and built content, publish locally with:

公開先と生成内容を確認・承認した後、ローカルから公開します。

```sh
npm run deploy
```

The command runs checks and browser tests before deploying. It forces Cloudflare OAuth's OS-keychain-backed storage and refuses API token/key environment variables. If authentication is needed, use `node scripts/cloudflare.js login --use-keyring`; an unavailable keychain stops the operation instead of falling back to plaintext. CI only builds and checks; it does not deploy or require Cloudflare credentials.

公開コマンドは検査とブラウザ確認を実行してからデプロイします。Cloudflare OAuth のキーチェーンを使う保存方式を必須とし、API トークン・キーの環境変数は拒否します。認証が必要な場合は `node scripts/cloudflare.js login --use-keyring` を使います。キーチェーンを利用できなければ停止し、平文保存へ切り替えません。CI はビルドと検査のみで、Cloudflare の認証情報を必要としません。

After each deployment, verify the live top page, slides, PDF, demo, trailer, redirects, 404s, and video range responses. The local runtime returns a full response for video range requests; partial transfers require a live check. Existing QR codes and the archived PDF link to GitHub Pages, so retain that distribution path for previously shared materials.

公開後は実際のトップページ・スライド・PDF・デモ・トレーラー・リダイレクト・404・動画の部分配信を確認します。ローカル環境は動画の Range 要求に全体を返すため、部分配信は公開後に確認が必要です。既存の QR コードと配布 PDF は GitHub Pages を参照しているため、配布済み資料のリンク先を維持してください。

## Credits and license / 権利とライセンス

Includes **images owned by third parties**, used for citation. Reuse follows each rights holder's terms — see [`CREDITS.md`](CREDITS.md). `demo/`, `tools/`, `trailer/`, `scripts/`, `src/`, and `tests/` are MIT licensed; the presentation materials are all rights reserved. See [`LICENSE`](LICENSE).

第三者が権利を持つ画像を含みます。再利用は各権利者の条件に従ってください。一覧は [`CREDITS.md`](CREDITS.md) にあります。`demo/`・`tools/`・`trailer/`・`scripts/`・`src/`・`tests/` は MIT ライセンス、発表資料そのものは著作権を保持しています。
