// Marp の bespoke テンプレのキー操作を、この講演の進行に合わせて調整する。
// ビルド後に preview.sh が差し込む。
//
//   数字 → Enter   そのページへ移動（画面には何も出さない。1.8秒放置で破棄）
//   L              レーザーポインターの入り切り
//   P              無効にする（発表者ツールを使わないので、誤って別ウィンドウが開くのを防ぐ）
//
// 移動は bespoke のハッシュ機能（location.hash = "#21" で21ページ目）に任せる。
//
// あわせて、スライドの中のリンクと動画に焦点が残らないようにする。
//   ・動画に焦点があると bespoke がキーを止めるので、ページ送りが空振りする
//     （bespoke は AUDIO/BUTTON/INPUT/SELECT/TEXTAREA/VIDEO で stopPropagation する）
//   ・リンクは別タブから戻ったときに、焦点の枠が残って見える
(function () {

  // 入力欄にいるときは、こちらのキー操作を効かせない
  function typing(e) {
    var t = e.target;
    return !!(t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.nodeName) || t.isContentEditable));
  }

  // ── 数字 → Enter でページ移動 ──
  var buf = '';
  var timer = null;

  function reset() {
    buf = '';
    if (timer) { clearTimeout(timer); timer = null; }
  }

  function hold() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(reset, 1800);
  }

  // capture 段で受ける。Marp 側のキー処理（document の bubble 段）より先に取る
  document.addEventListener('keydown', function (e) {
    if (typing(e) || e.metaKey || e.ctrlKey || e.altKey) return;

    // P は発表者ツールを別ウィンドウで開く。使わないので、ここで握り潰す
    if (e.key === 'p' || e.key === 'P') {
      e.preventDefault();
      e.stopImmediatePropagation();
      return;
    }

    if (e.key >= '0' && e.key <= '9') {
      buf += e.key;
      hold();
    } else if (buf && e.key === 'Enter') {
      location.hash = '#' + parseInt(buf, 10);
      reset();
    } else if (buf && e.key === 'Backspace') {
      buf = buf.slice(0, -1);
      hold();
    } else {
      return;   // 関係ないキーは Marp に渡す
    }
    e.preventDefault();
    e.stopPropagation();
  }, true);

  // ── リンクと動画に焦点を残さない ──
  // クリックしたあと、その要素に焦点を残さない。既定の動作（再生・遷移）は
  // そのまま起き、そのあとで焦点だけ外す。キーボードから実行したとき
  // （e.detail === 0）は、利用者の居場所を奪わないよう外さない
  document.addEventListener('click', function (e) {
    if (e.detail === 0 || !e.target || !e.target.closest) return;
    var el = e.target.closest('section a, section video, section audio');
    if (el) setTimeout(function () { el.blur(); }, 0);
  }, true);

  // Tab の巡回からも外す。押しても枠が出ない
  window.addEventListener('load', function () {
    var list = document.querySelectorAll('section a, section video, section audio');
    for (var i = 0; i < list.length; i++) list[i].tabIndex = -1;
  });

  // ── L でレーザーポインター。マウスの位置に光点を出す ──
  var dot = null;
  var on = false;
  // 最後のマウス位置。入れた瞬間からそこに出す。まだ一度も動いていなければ画面の中央
  var mx = window.innerWidth / 2;
  var my = window.innerHeight / 2;

  function make() {
    dot = document.createElement('div');
    // 大きさは vh 基準。窓の大小によらず、投影したときと同じ比率で見える。
    // margin は幅の半分。これで translate の座標が光点の中心になる
    dot.style.cssText = [
      'position:fixed', 'left:0', 'top:0',
      'width:1.7vh', 'height:1.7vh', 'margin:-0.85vh 0 0 -0.85vh',
      'border-radius:50%',
      // 中心を白く飛ばすと、赤一色より光って見える
      'background:radial-gradient(circle,#fff 10%,#ff3b3b 45%,#d40000 100%)',
      'box-shadow:0 0 1.3vh 0.65vh rgba(255,45,45,.42)',
      // 実演のリンク（P.39・P.41）はレーザー中でも押せるままにする
      'pointer-events:none',
      'z-index:2147483647',
      'display:none'
    ].join(';');
    document.body.appendChild(dot);
  }

  function place() {
    dot.style.transform = 'translate(' + mx + 'px,' + my + 'px)';
  }

  // 消えている間も位置は覚えておく。入れたときにマウスのある場所から出る
  document.addEventListener('mousemove', function (e) {
    mx = e.clientX;
    my = e.clientY;
    if (on) place();
  }, true);

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'l' && e.key !== 'L') return;
    // 押しっぱなしの自動リピートで入り切りを繰り返さない
    if (e.repeat || typing(e) || e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault();

    if (!dot) make();
    on = !on;
    if (on) place();
    dot.style.display = on ? 'block' : 'none';
    // 矢印と光点が二重に見えないようにする
    document.documentElement.style.cursor = on ? 'none' : '';
  }, true);
})();
