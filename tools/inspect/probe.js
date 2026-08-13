// 全ページの computed style を吸い出す。tools/probe.sh から HTML に注入して使う。
// 出す種類は text（文字）／rule（線）／link（リンク）／box（版面の中の位置）の4つ。
window.addEventListener('load', function () {
  var out = [];

  // 要素を「タグ.クラス」で表す。親を2つまで足して、どこの何かが分かるようにする
  function cpath(el) {
    var parts = [];
    var e = el;
    for (var i = 0; i < 3 && e && e.tagName && e.tagName.toLowerCase() !== 'section'; i++) {
      var t = e.tagName.toLowerCase();
      var c = (e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className) || '';
      c = String(c).trim().split(/\s+/).filter(Boolean).join('.');
      parts.unshift(c ? t + '.' + c : t);
      e = e.parentElement;
    }
    return parts.join(' > ');
  }

  // 直接の text node を持つか（親の入れ物ではなく、字を出している要素か）
  function hasOwnText(el) {
    for (var i = 0; i < el.childNodes.length; i++) {
      var n = el.childNodes[i];
      if (n.nodeType === 3 && n.textContent.trim().length) return true;
    }
    return false;
  }

  var secs = document.querySelectorAll('section');
  secs.forEach(function (sec, si) {
    var page = si + 1;
    var sc = String(sec.className || '').trim();
    var sr = sec.getBoundingClientRect();
    // section を原点にした座標に直す。svg で拡大されている場合の倍率も戻す
    var k = sr.width ? 1920 / sr.width : 1;
    function box(el) {
      var r = el.getBoundingClientRect();
      return { x: Math.round((r.left - sr.left) * k * 10) / 10,
               y: Math.round((r.top - sr.top) * k * 10) / 10,
               w: Math.round(r.width * k * 10) / 10,
               h: Math.round(r.height * k * 10) / 10 };
    }

    // 住人（フッターのキャラ）は section 自身の ::before に背景GIFで置かれている。
    // 子孫だけ見ると取りこぼすので、section も走査に入れる
    var all = [sec].concat(Array.prototype.slice.call(sec.querySelectorAll('*')));
    all.forEach(function (el) {
      var cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') return;
      var b = box(el);
      var sel = cpath(el);

      // ── 文字 ──
      if (hasOwnText(el)) {
        out.push({
          t: 'text', p: page, sc: sc, sel: sel,
          txt: el.textContent.trim().slice(0, 24),
          fs: Math.round(parseFloat(cs.fontSize) * k * 10) / 10,
          fw: cs.fontWeight,
          lh: cs.lineHeight === 'normal' ? 'normal'
              : Math.round(parseFloat(cs.lineHeight) * k * 10) / 10,
          col: cs.color,
          ls: cs.letterSpacing === 'normal' ? '0'
              : Math.round(parseFloat(cs.letterSpacing) * k * 100) / 100 + '',
          ff: cs.fontFamily.split(',')[0].replace(/["']/g, ''),
          ta: cs.textAlign,
          x: b.x, y: b.y, w: b.w, h: b.h
        });
      }

      // ── リンク ──
      if (el.tagName.toLowerCase() === 'a') {
        out.push({
          t: 'link', p: page, sc: sc, sel: sel,
          txt: el.textContent.trim().slice(0, 40),
          col: cs.color, td: cs.textDecorationLine, tdc: cs.textDecorationColor,
          fw: cs.fontWeight,
          fs: Math.round(parseFloat(cs.fontSize) * k * 10) / 10,
          href: el.getAttribute('href') || '',
          x: b.x, y: b.y, w: b.w, h: b.h
        });
      }

      // ── 画像の実寸と表示寸法 ──
      // 表示より大きすぎる画像は、リポジトリと PDF を無駄に太らせる
      if (el.tagName.toLowerCase() === 'img' && el.naturalWidth) {
        out.push({ t: 'img', p: page, src: el.getAttribute('src') || '',
                   nw: el.naturalWidth, nh: el.naturalHeight,
                   w: b.w, h: b.h });
      }

      // ── 動く要素（GIF・動画）の居場所 ──
      // 撮るたびにコマが変わるので、差分を見るときはこの矩形の中を除く。
      // img/video だけでなく、CSS の背景（住人は section::before の背景GIF）も拾う
      var tag = el.tagName.toLowerCase();
      var moving = false;
      if (tag === 'video') moving = true;
      if (tag === 'img' && /\.gif(\?|$)/i.test(el.getAttribute('src') || '')) moving = true;
      if (/\.gif(\?|"|\))/i.test(cs.backgroundImage || '')) moving = true;
      if (moving) {
        out.push({ t: 'motion', p: page, sel: sel, src: (el.getAttribute('src') || cs.backgroundImage).slice(0, 60),
                   x: b.x, y: b.y, w: b.w, h: b.h });
      }
      ['::before', '::after'].forEach(function (pe) {
        var ps = getComputedStyle(el, pe);
        if (ps.content === 'none') return;
        if (!/\.gif(\?|"|\))/i.test(ps.backgroundImage || '')) return;
        // 疑似要素は getBoundingClientRect が取れないので、
        // 指定された位置と大きさから矩形を組み立てる（親は position:relative）
        var pw = parseFloat(ps.width), ph = parseFloat(ps.height);
        if (isNaN(pw) || isNaN(ph)) { pw = b.w; ph = b.h; }
        var px2 = b.x, py2 = b.y;
        var L = parseFloat(ps.left), R = parseFloat(ps.right);
        var T = parseFloat(ps.top), B = parseFloat(ps.bottom);
        if (!isNaN(L)) px2 = b.x + L;
        else if (!isNaN(R)) px2 = b.x + b.w - R - pw;
        if (!isNaN(T)) py2 = b.y + T;
        else if (!isNaN(B)) py2 = b.y + b.h - B - ph;
        out.push({ t: 'motion', p: page, sel: sel + pe, src: ps.backgroundImage.slice(0, 60),
                   x: Math.round(px2 * 10) / 10, y: Math.round(py2 * 10) / 10,
                   w: Math.round(pw * 10) / 10, h: Math.round(ph * 10) / 10 });
      });

      // ── 線（枠線）──
      ['top', 'right', 'bottom', 'left'].forEach(function (side) {
        var w = parseFloat(cs['border' + side[0].toUpperCase() + side.slice(1) + 'Width']);
        var st = cs['border' + side[0].toUpperCase() + side.slice(1) + 'Style'];
        if (!w || st === 'none' || st === 'hidden') return;
        var len = (side === 'top' || side === 'bottom') ? b.w : b.h;
        if (len < 2) return;
        out.push({
          t: 'rule', p: page, sc: sc, sel: sel, kind: 'border-' + side,
          w: Math.round(w * k * 100) / 100, style: st,
          col: cs['border' + side[0].toUpperCase() + side.slice(1) + 'Color'],
          len: Math.round(len * 10) / 10, x: b.x, y: b.y
        });
      });

      // ── 線（細い箱・疑似要素・グラデーション）──
      if ((b.w <= 8 || b.h <= 8) && b.w > 0 && b.h > 0) {
        var bg = cs.backgroundColor;
        if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
          out.push({ t: 'rule', p: page, sc: sc, sel: sel, kind: 'thin-box',
                     w: Math.round(Math.min(b.w, b.h) * 100) / 100, style: 'solid',
                     col: bg, len: Math.round(Math.max(b.w, b.h) * 10) / 10, x: b.x, y: b.y });
        }
      }
      ['::before', '::after'].forEach(function (pe) {
        var ps = getComputedStyle(el, pe);
        if (ps.content === 'none') return;
        var pw = parseFloat(ps.width), ph = parseFloat(ps.height);
        var bg = ps.backgroundColor;
        if (isNaN(pw) || isNaN(ph) || pw <= 0 || ph <= 0) return;
        if (!(pw * k <= 8 || ph * k <= 8)) return;
        if (!bg || bg === 'rgba(0, 0, 0, 0)') return;
        out.push({ t: 'rule', p: page, sc: sc, sel: sel + pe, kind: 'pseudo',
                   w: Math.round(Math.min(pw, ph) * k * 100) / 100, style: 'solid', col: bg,
                   len: Math.round(Math.max(pw, ph) * k * 10) / 10, x: b.x, y: b.y });
      });
      var bgi = cs.backgroundImage, bsz = cs.backgroundSize;
      if (bgi && bgi.indexOf('gradient') >= 0 && bsz && bsz !== 'auto') {
        var pt = bsz.split(' ');
        var bw = parseFloat(pt[0]), bh = parseFloat(pt[1]);
        var thin = (!isNaN(bw) && bw * k <= 8) || (!isNaN(bh) && bh * k <= 8);
        if (thin) {
          var m = bgi.match(/rgba?\([^)]*\)/);
          out.push({ t: 'rule', p: page, sc: sc, sel: sel, kind: 'bg-grad',
                     w: Math.round(Math.min(isNaN(bw) ? 99 : bw, isNaN(bh) ? 99 : bh) * k * 100) / 100,
                     style: 'grad', col: m ? m[0] : '?', len: 0, x: b.x, y: b.y, bsz: bsz });
        }
      }
    });

    // ── 版面（section 直下の子だけ。中身の左右上下端を見る）──
    Array.prototype.forEach.call(sec.children, function (el) {
      var cs = getComputedStyle(el);
      if (cs.display === 'none') return;
      var b = box(el);
      if (b.w <= 0 || b.h <= 0) return;
      out.push({ t: 'box', p: page, sc: sc, sel: cpath(el),
                 x: b.x, y: b.y, w: b.w, h: b.h,
                 ta: cs.textAlign, ml: cs.marginLeft, mr: cs.marginRight,
                 mt: cs.marginTop, mb: cs.marginBottom });
    });
  });

  var pre = document.createElement('pre');
  pre.id = 'PROBE_RESULT';
  pre.textContent = JSON.stringify(out);
  document.body.appendChild(pre);
});
