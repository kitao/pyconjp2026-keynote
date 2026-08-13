// Marp の bespoke テンプレのキー操作を、この講演の進行に合わせて調整する。
// ビルド後に preview.sh が差し込む。
//
//   数字 → Enter   そのページへ移動（画面には何も出さない。1.8秒放置で破棄）
//   P              無効にする（発表者ツールを使わないので、誤って別ウィンドウが開くのを防ぐ）
//
// 移動は bespoke のハッシュ機能（location.hash = "#21" で21ページ目）に任せる。
(function () {
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
    var t = e.target;
    if (t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.nodeName) || t.isContentEditable)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;

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
})();
