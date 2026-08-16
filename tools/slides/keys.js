// Adjusts the key handling of Marp's bespoke template to suit this talk.
// preview.sh injects this file after the build.
//
//   digits then Enter   jump to that slide (nothing is shown on screen; the
//                       buffer is dropped after 1.8 s of no typing)
//   L                   laser pointer on / off
//   P                   disabled; the presenter tools are not used, and this
//                       stops a stray window from opening
//
// Jumping is left to bespoke's hash support (location.hash = "#21" is slide 21).
//
// It also keeps focus off the links and videos inside the slides:
//   - a focused video makes bespoke swallow the keys, so paging does nothing
//     (bespoke calls stopPropagation for AUDIO/BUTTON/INPUT/SELECT/TEXTAREA/VIDEO)
//   - a focused link keeps its focus ring visible after returning from a tab
//
// And it rewinds the videos on every slide change, so a video that was played
// part way through is back at its poster the next time the slide comes up.
(function () {

  // Never take over the keys while the caret is in an input
  function typing(e) {
    var t = e.target;
    return !!(t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.nodeName) || t.isContentEditable));
  }

  // -- Digits then Enter to jump to a slide --
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

  // Listen in the capture phase, ahead of Marp's own handler on document
  document.addEventListener('keydown', function (e) {
    if (typing(e) || e.metaKey || e.ctrlKey || e.altKey) return;

    // P opens the presenter tools in another window. Unused, so swallow it.
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
      return;   // Anything else goes through to Marp
    }
    e.preventDefault();
    e.stopPropagation();
  }, true);

  // -- Keep focus off the links and videos --
  // Drop focus after a click. The default action (play, follow the link) still
  // happens; only the focus is cleared afterwards. When the click came from the
  // keyboard (e.detail === 0) focus is left alone, so the user keeps their place.
  document.addEventListener('click', function (e) {
    if (e.detail === 0 || !e.target || !e.target.closest) return;
    var el = e.target.closest('section a, section video, section audio');
    if (el) setTimeout(function () { el.blur(); }, 0);
  }, true);

  // Take them out of the tab order as well, so Tab shows no focus ring
  window.addEventListener('load', function () {
    var list = document.querySelectorAll('section a, section video, section audio');
    for (var i = 0; i < list.length; i++) list[i].tabIndex = -1;
  });

  // -- Rewind the videos whenever the slide changes --
  // A video that was stopped part way keeps its position, so the slide comes
  // back up showing the frame it stopped on instead of its poster. load() is
  // used rather than currentTime = 0, which leaves the first frame on screen.
  // Only the videos that are played by hand are touched. The autoplaying loops
  // (slides 30 and 31) run on their own and have no position worth keeping.
  function rewind() {
    var list = document.querySelectorAll('section video');
    for (var i = 0; i < list.length; i++) {
      var v = list[i];
      if (v.autoplay) continue;
      if (v.paused && !v.currentTime) continue;   // already at the start
      v.pause();
      v.load();
    }
  }

  // One slide change flips the class on several elements, so the calls are
  // collapsed into one.
  var pending = null;

  function schedule() {
    if (pending) return;
    pending = setTimeout(function () { pending = null; rewind(); }, 50);
  }

  window.addEventListener('load', function () {
    // Watching the class is more reliable than the hash, which bespoke only
    // reads on the way in.
    new MutationObserver(schedule).observe(document.body, {
      subtree: true, attributes: true, attributeFilter: ['class']
    });
  });

  // -- L for a laser pointer: a dot of light at the mouse position --
  var dot = null;
  var on = false;
  // Last mouse position, so the dot appears there the moment it is switched
  // on. Before the mouse has moved at all, that is the centre of the screen.
  var mx = window.innerWidth / 2;
  var my = window.innerHeight / 2;

  function make() {
    dot = document.createElement('div');
    // Sized in vh, so a small window looks the same as the projected screen.
    // The margin is half the width, which puts the translate coordinate at
    // the centre of the dot.
    dot.style.cssText = [
      'position:fixed', 'left:0', 'top:0',
      'width:1.7vh', 'height:1.7vh', 'margin:-0.85vh 0 0 -0.85vh',
      'border-radius:50%',
      // Blowing the centre out to white reads as light, where flat red does not
      'background:radial-gradient(circle,#fff 10%,#ff3b3b 45%,#d40000 100%)',
      'box-shadow:0 0 1.3vh 0.65vh rgba(255,45,45,.42)',
      // Keep the demo links (slides 39 and 41) clickable while the laser is on
      'pointer-events:none',
      'z-index:2147483647',
      'display:none'
    ].join(';');
    document.body.appendChild(dot);
  }

  function place() {
    dot.style.transform = 'translate(' + mx + 'px,' + my + 'px)';
  }

  // Track the position even while hidden, so it lights up where the mouse is
  document.addEventListener('mousemove', function (e) {
    mx = e.clientX;
    my = e.clientY;
    if (on) place();
  }, true);

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'l' && e.key !== 'L') return;
    // Do not toggle over and over on auto-repeat
    if (e.repeat || typing(e) || e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault();

    if (!dot) make();
    on = !on;
    if (on) place();
    dot.style.display = on ? 'block' : 'none';
    // Hide the arrow so it is not seen alongside the dot
    document.documentElement.style.cursor = on ? 'none' : '';
  }, true);
})();
