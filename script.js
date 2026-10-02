(() => {
  'use strict';

  /* ---- Opening intro + hero reveal ---- */
  window.addEventListener('DOMContentLoaded', () => {
    const intro = document.getElementById('introOverlay');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const startHero = () => {
      setTimeout(() => document.body.classList.add('hero-in'), 20);
    };

    if (!intro || reduceMotion) {
      if (intro) intro.remove();
      startHero();
      return;
    }

    document.body.classList.add('intro-active');

    const photos = intro.querySelectorAll('.intro-photos img');
    let photoIndex = 0;
    photos[0].classList.add('active');
    const flicker = setInterval(() => {
      photos.forEach((p) => p.classList.remove('active'));
      photoIndex = (photoIndex + 1) % photos.length;
      photos[photoIndex].classList.add('active');
    }, 190);

    const progress = document.getElementById('introProgress');
    const MARK_BEAT = 2500;
    const INTRO_DURATION = 5600;
    setTimeout(() => {
      intro.classList.add('run');
      if (progress) {
        progress.style.transition = `width ${INTRO_DURATION}ms linear`;
        setTimeout(() => { progress.style.width = '100%'; }, 20);
      }
    }, 20);
    const markTimer = setTimeout(() => intro.classList.add('text-in'), MARK_BEAT);

    let finished = false;
    const finishIntro = () => {
      if (finished) return;
      finished = true;
      clearInterval(flicker);
      clearTimeout(markTimer);
      clearTimeout(timer);
      intro.classList.add('closing');
      document.body.classList.remove('intro-active');
      startHero();
      setTimeout(() => intro.remove(), 850);
    };

    const timer = setTimeout(finishIntro, INTRO_DURATION);
    const skipBtn = document.getElementById('introSkip');
    if (skipBtn) skipBtn.addEventListener('click', finishIntro);
  });

  /* ---- Header scroll state + scroll progress ---- */
  const header = document.getElementById('siteHeader');
  const progressFill = document.getElementById('progressFill');

  const onScroll = () => {
    const y = window.scrollY;
    header.classList.toggle('scrolled', y > 40);

    const doc = document.documentElement;
    const max = doc.scrollHeight - doc.clientHeight;
    const pct = max > 0 ? (y / max) * 100 : 0;
    progressFill.style.width = pct + '%';
  };
  document.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---- Nav overlay toggle ---- */
  const menuBtn = document.getElementById('menuBtn');
  const navOverlay = document.getElementById('navOverlay');

  const closeNav = () => {
    navOverlay.classList.remove('open');
    menuBtn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  };
  const openNav = () => {
    navOverlay.classList.add('open');
    menuBtn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  };

  menuBtn.addEventListener('click', () => {
    const isOpen = navOverlay.classList.contains('open');
    isOpen ? closeNav() : openNav();
  });

  navOverlay.querySelectorAll('[data-nav-close]').forEach((el) => {
    el.addEventListener('click', closeNav);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeNav();
  });

  /* ---- Scroll reveal ---- */
  const revealTargets = document.querySelectorAll('.reveal, .concept-title');
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -8% 0px' }
  );
  revealTargets.forEach((el) => io.observe(el));

  /* stagger program cards slightly */
  document.querySelectorAll('.program-card.reveal').forEach((el, i) => {
    el.style.transitionDelay = (i % 3) * 0.08 + 's';
  });

  /* ---- Concept graph: philosophy × data fusion visual ---- */
  (() => {
    const canvas = document.getElementById('conceptGraph');
    const section = canvas && canvas.closest('.concept');
    if (!canvas || !section) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const ctx = canvas.getContext('2d');
    const hexToRgb = (hex) => {
      const n = parseInt(hex.trim().replace('#', ''), 16);
      return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
    };
    const rootStyle = getComputedStyle(document.documentElement);
    const PHILO = hexToRgb(rootStyle.getPropertyValue('--dark-fg') || '#f6efdc');
    const DATA = hexToRgb(rootStyle.getPropertyValue('--accent') || '#3f6fd1');
    const LINK_DIST = 130;

    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0, h = 0, nodes = [];

    const makeNodes = () => {
      const count = Math.max(18, Math.min(46, Math.round((w * h) / 26000)));
      nodes = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.28,
        vy: (Math.random() - 0.5) * 0.28,
        r: Math.random() * 1.6 + 1.2,
        type: Math.random() < 0.5 ? 'philo' : 'data',
      }));
    };

    const resize = () => {
      w = section.clientWidth;
      h = section.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      makeNodes();
    };

    let running = false;
    let raf = null;

    const tick = () => {
      if (!running) return;
      ctx.clearRect(0, 0, w, h);

      nodes.forEach((n) => {
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
        n.x = Math.min(Math.max(n.x, 0), w);
        n.y = Math.min(Math.max(n.y, 0), h);
      });

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = a.x - b.x, dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist >= LINK_DIST) continue;
          const t = 1 - dist / LINK_DIST;
          const fusion = a.type !== b.type;
          ctx.strokeStyle = fusion
            ? `rgba(${DATA},${(t * 0.55).toFixed(3)})`
            : `rgba(${a.type === 'philo' ? PHILO : DATA},${(t * 0.14).toFixed(3)})`;
          ctx.lineWidth = fusion ? 1 : 0.6;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      nodes.forEach((n) => {
        ctx.fillStyle = `rgba(${n.type === 'philo' ? PHILO : DATA},.85)`;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fill();
      });

      raf = requestAnimationFrame(tick);
    };

    const start = () => { if (!running) { running = true; raf = requestAnimationFrame(tick); } };
    const stop = () => { running = false; if (raf) cancelAnimationFrame(raf); };

    resize();
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => (e.isIntersecting ? start() : stop())),
      { threshold: 0.05 }
    );
    io.observe(section);

    let resizeTimer = null;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resize, 200);
    });
  })();

  /* ---- Custom cursor dot (desktop, fine pointer only) ---- */
  if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    const dot = document.getElementById('cursorDot');
    let raf = null;
    window.addEventListener('mousemove', (e) => {
      dot.classList.add('active');
      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        dot.style.left = e.clientX + 'px';
        dot.style.top = e.clientY + 'px';
      });
    });
    document.querySelectorAll('a, button').forEach((el) => {
      el.addEventListener('mouseenter', () => dot.classList.add('grow'));
      el.addEventListener('mouseleave', () => dot.classList.remove('grow'));
    });
    window.addEventListener('mouseleave', () => dot.classList.remove('active'));
  }
})();
