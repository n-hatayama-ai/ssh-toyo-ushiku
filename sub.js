// 下層ページ共通：メニュー、スクロールで現れる、数字のカウントアップ、記事の絞り込み
(() => {
  const menu = document.getElementById('menu'), btn = document.getElementById('menuBtn');
  const setMenu = on => { menu.classList.toggle('open', on); btn.setAttribute('aria-expanded', on); btn.textContent = on ? 'CLOSE' : 'MENU'; };
  btn.addEventListener('click', () => setMenu(!menu.classList.contains('open')));
  addEventListener('keydown', e => { if (e.key === 'Escape') setMenu(false); });

  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return; io.unobserve(e.target); e.target.classList.add('in-view');
    const b = e.target.matches('.num') && e.target.querySelector('b'); if (!b) return;
    const node = b.firstChild, to = parseInt(node.textContent, 10); if (!to) return;
    const t0 = performance.now();
    const tick = now => { const k = Math.min(1, (now - t0) / 1300); node.textContent = Math.round(to * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }), { threshold: .12 });
  document.querySelectorAll('.rv').forEach(el => io.observe(el));

  const filter = document.getElementById('filter');
  if (filter) filter.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    [...filter.children].forEach(x => x.setAttribute('aria-pressed', x === b));
    document.querySelectorAll('.card[data-cat]').forEach(c => { c.classList.toggle('hide', b.dataset.c !== 'all' && c.dataset.cat !== b.dataset.c); c.classList.add('in-view'); });
  });
  // 記事へ直接来たときは、その記事を開いて見せる
  const t = location.hash && document.getElementById(location.hash.slice(1));
  if (t && t.matches('.card')) { t.classList.add('in-view'); const d = t.querySelector('details'); if (d) d.open = true; }
})();
