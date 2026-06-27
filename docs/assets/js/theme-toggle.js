(function () {
  var STORAGE_KEY = 'docs-keeper-theme';
  var btn = document.querySelector('.theme-toggle');
  if (!btn) return;

  var label = btn.querySelector('.theme-toggle-text');

  function getCurrent() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  }

  function update() {
    var current = getCurrent();
    if (label) {
      label.textContent = current === 'dark' ? 'Light mode' : 'Dark mode';
    }
    btn.setAttribute('aria-pressed', current === 'dark' ? 'true' : 'false');
  }

  btn.addEventListener('click', function () {
    var next = getCurrent() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch (e) {
      /* ignore — private mode etc. */
    }
    update();
  });

  if (window.matchMedia) {
    var media = window.matchMedia('(prefers-color-scheme: dark)');
    var listener = function (e) {
      try {
        if (localStorage.getItem(STORAGE_KEY)) return;
      } catch (err) { /* ignore */ }
      document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
      update();
    };
    if (media.addEventListener) media.addEventListener('change', listener);
    else if (media.addListener) media.addListener(listener);
  }

  update();
})();
