// Dump the computed styles of every slide. Injected into the HTML by probe.sh.
// Four kinds of record come out: text, rule, link and box (position in the
// type area).
window.addEventListener('load', function () {
  var out = [];

  // Name an element as tag.class, prefixed by up to two ancestors so it is
  // clear which one it is.
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

  // Does it hold a text node directly, i.e. is it setting type rather than
  // just containing something that does?
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
    // Convert to coordinates with the section as origin, undoing the scale
    // the svg may have applied.
    var k = sr.width ? 1920 / sr.width : 1;
    function box(el) {
      var r = el.getBoundingClientRect();
      return { x: Math.round((r.left - sr.left) * k * 10) / 10,
               y: Math.round((r.top - sr.top) * k * 10) / 10,
               w: Math.round(r.width * k * 10) / 10,
               h: Math.round(r.height * k * 10) / 10 };
    }

    // The residents in the footer are a background GIF on the section's own
    // ::before, so walking descendants alone would miss them; the section
    // itself is included in the scan.
    var all = [sec].concat(Array.prototype.slice.call(sec.querySelectorAll('*')));
    all.forEach(function (el) {
      var cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') return;
      var b = box(el);
      var sel = cpath(el);

      // -- Text --
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

      // -- Links --
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

      // -- Natural size against displayed size --
      // An image far larger than it is shown at bloats both the repository
      // and the PDF.
      if (el.tagName.toLowerCase() === 'img' && el.naturalWidth) {
        out.push({ t: 'img', p: page, src: el.getAttribute('src') || '',
                   nw: el.naturalWidth, nh: el.naturalHeight,
                   w: b.w, h: b.h });
      }

      // -- Where the moving elements are (GIFs and videos) --
      // Their frame differs on every capture, so these rectangles are excluded
      // when diffing. Both img/video and CSS backgrounds are collected (the
      // residents are a background GIF on section::before).
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
        // getBoundingClientRect is unavailable for a pseudo-element, so the
        // rectangle is assembled from the declared position and size (the
        // parent is position:relative).
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

      // -- Rules drawn as borders --
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

      // -- Rules drawn as thin boxes, pseudo-elements or gradients --
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

    // -- Type area: direct children of the section only, looking at the
    //    outer edges of the content --
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
