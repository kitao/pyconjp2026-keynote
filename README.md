# Let's Play Programming with Pyxel!

### Designing the Fun of Making / 「楽しく作る」をデザインする

Keynote slides for PyCon JP 2026.
PyCon JP 2026 基調講演の発表資料です。

|  |  |
|---|---|
| Date / 日時 | 22 Aug 2026, 17:05–17:50 |
| Venue / 会場 | Hiroshima International Conference Center, Phoenix Hall |
| Speaker / 発表者 | Takashi Kitao / 北尾 崇（[@kitao](https://x.com/kitao)） |
| Slides / 発表資料 | https://kitao.github.io/pyconjp2026-keynote/ |

> A speaker's personal repository, not an official PyCon JP publication.
> 発表者個人の資料であり、PyCon JP 2026 運営の公式資料ではありません。

Pyxel itself → **https://github.com/kitao/pyxel**

## View / 見る

- **[Slides](https://kitao.github.io/pyconjp2026-keynote/)** — arrow keys to move, `F` for full screen
  矢印キーでページ送り、`F` で全画面
- **[PDF](https://kitao.github.io/pyconjp2026-keynote/pyconjp2026-keynote.pdf)** — video pages appear as stills
  動画の面は静止画になります

## Run / 動かす

The `pyxel` commands need `pip install -U pyxel`. The browser link needs nothing.
`pyxel` コマンドには `pip install -U pyxel` が要ります。ブラウザのリンクは何も要りません。

### The trailer / 予告

The 60-second trailer for the talk.
講演の予告動画（60秒）です。

**[Open it in a browser](https://kitao.github.io/pyxel/web/launcher/?play=kitao/pyconjp2026-keynote/main/trailer/trailer)**

```sh
pyxel run trailer/trailer.py
```

### The game / ゲーム

The game built in the talk, the same code as the slides.
本編で作るゲーム。スライドのコードと同じものです。

```sh
pyxel run demo/game/game.py
```

## Credits and license / 権利とライセンス

Includes **images owned by third parties**, used for citation. Reuse follows each rights holder's terms — see [`CREDITS.md`](CREDITS.md).
第三者が権利を持つ画像を含みます。再利用は各権利者の条件に従ってください。一覧は [`CREDITS.md`](CREDITS.md) にあります。

`demo/`, `tools/`, and `trailer/` are MIT licensed; the presentation materials are all rights reserved. See [`LICENSE`](LICENSE).
`demo/`・`tools/`・`trailer/` は MIT ライセンス、発表資料そのものは著作権を保持しています。
