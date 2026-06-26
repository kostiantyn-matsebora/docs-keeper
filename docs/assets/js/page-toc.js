(function () {
  // Build an "On this page" navigation block from H2 headings inside the
  // main content area, appended to <aside.page-toc[data-auto-toc]>.
  // H2-only: H3s clutter the sidebar on long pages.
  var aside = document.querySelector('aside.page-toc[data-auto-toc]');
  if (!aside) return;

  var content = document.querySelector('.main-content');
  if (!content) return;

  var headings = [].slice.call(content.querySelectorAll('h2[id]')).filter(function (h) {
    return !aside.contains(h);
  });

  if (headings.length < 2) {
    aside.style.display = 'none';
    return;
  }

  var rootList = document.createElement('ul');
  headings.forEach(function (h) {
    var li = document.createElement('li');
    var a = document.createElement('a');
    a.href = '#' + h.id;
    a.textContent = h.textContent.trim();
    li.appendChild(a);
    rootList.appendChild(li);
  });

  var heading = document.createElement('h4');
  heading.textContent = 'On this page';

  aside.appendChild(heading);
  aside.appendChild(rootList);
})();
