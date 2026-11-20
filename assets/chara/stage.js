// 東洋大牛久SSHキャラクターの掛け合い（characters.html の舞台）
import * as THREE from 'three';
import { createChara } from './chara3d.js';

// セリフと動き。dur は秒、step は 0=問う 1=確かめる 2=伝える
const SCENES = [
  { act: 'intro', step: -1, dur: 2.4 },
  { act: 'ask', step: 0, dur: 4.2, philo: '牛久沼の水って、季節で変わるのかな？' },
  { act: 'why', step: 0, dur: 3.4, philo: 'なぜ、なぜ、なぜ？' },
  { act: 'measure', step: 1, dur: 3.8, numa: 'まずは測ってみるっぱ！' },
  { act: 'data', step: 1, dur: 4.4, numa: '毎月のデータがそろったっぱ！' },
  { act: 'think', step: 1, dur: 4.4, philo: 'おもしろい！ じゃあ、なぜそうなるんだろう？' },
  { act: 'tell', step: 2, dur: 4.8, philo: 'わかったことを、みんなに伝えよう！', numa: '伝えるっぱ！' },
  { act: 'end', step: 2, dur: 2.4 },
];
const TOTAL = SCENES.reduce((s, c) => s + c.dur, 0);
const $ = id => document.getElementById(id);
const stage = $('stage'), canvas = $('charaCanvas'), bP = $('bPhilo'), bN = $('bNuma'), bar = $('cBar'), btnPlay = $('cPlay');
const stepEls = [...stage.querySelectorAll('.steps li')];

// セリフを文字でも読めるように
$('scriptList').innerHTML = SCENES.flatMap(s => [s.philo && `<li><b>フィロ</b>${s.philo}</li>`, s.numa && `<li><b>ぬまっぱ博士</b>${s.numa}</li>`]).filter(Boolean).join('');

const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
let renderer;
try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true }); }
catch (e) { $('stageFallback').hidden = false; stage.querySelector('.ctrl').hidden = true; document.querySelector('.script').open = true; throw e; }
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));

const scene = new THREE.Scene();
const cam = new THREE.PerspectiveCamera(30, 1, 0.1, 60);
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8fa8, 0.8 * Math.PI));
const sun = new THREE.DirectionalLight(0xffffff, 0.75 * Math.PI); sun.position.set(3, 5, 5); scene.add(sun);

const { BUILD, addOutlines } = createChara(THREE);
const holder = (model, x) => { const h = new THREE.Group(); addOutlines(model); h.add(model); h.position.x = x; scene.add(h); return h; };
const P = holder(BUILD.sophy('tu'), -1.3), N = holder(BUILD.numappa('name'), 1.3);
const find = (root, role) => { const out = []; root.traverse(o => { if (o.userData.role === role) out.push(o); }); return out; };
const wingR = find(P, 'wingR')[0], orbit = find(P, 'orbit')[0], holo = find(N, 'holo')[0], tablet = find(N, 'tablet')[0], bars = find(N, 'bar');
const wingBase = wingR.rotation.z, tabBase = tablet.scale.clone();
[P, N].forEach(h => h.traverse(o => { if (o.userData.spin) o.userData.spin = false; }));   // 回転はこのファイルで動かす

// 足もとの影
const shadow = x => { const m = new THREE.Mesh(new THREE.CircleGeometry(0.85, 40), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.28 })); m.rotation.x = -Math.PI / 2; m.position.set(x, 0.01, 0); m.scale.y = 0.55; scene.add(m); return m; };
const sP = shadow(-1.3), sN = shadow(1.3);

// フィロの頭の上の「？」
const qTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');
  x.font = '900 210px "Zen Kaku Gothic New", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.lineWidth = 18; x.strokeStyle = '#172443'; x.strokeText('?', 128, 140); x.fillStyle = '#f0b93e'; x.fillText('?', 128, 140);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
const qMark = new THREE.Sprite(new THREE.SpriteMaterial({ map: qTex, transparent: true })); qMark.position.set(-2.25, 2.35, 0.3); qMark.scale.setScalar(0); scene.add(qMark);

// データの粒（お皿 → タブレット）と紙吹雪
const dots = Array.from({ length: 16 }, () => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 10), new THREE.MeshBasicMaterial({ color: 0x7dffd8, transparent: true })); m.visible = false; scene.add(m); return m; });
const COLORS = [0xf0b93e, 0xef5b6b, 0x2fd0a8, 0x5b9df0, 0xffffff];
const confetti = Array.from({ length: 70 }, (_, i) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(0.09, 0.05), new THREE.MeshBasicMaterial({ color: COLORS[i % COLORS.length], side: THREE.DoubleSide, transparent: true })); m.visible = false; m.userData.v = new THREE.Vector3(); scene.add(m); return m; });
const resetConfetti = () => confetti.forEach(m => { m.visible = true; m.position.set((Math.random() - 0.5) * 6, 3.2 + Math.random() * 2.5, (Math.random() - 0.5) * 2); m.userData.v.set((Math.random() - 0.5) * 0.4, -0.6 - Math.random() * 0.8, 0); m.material.opacity = 1; m.userData.r = Math.random() * 6; });

// 大きさに合わせてカメラを引く（スマホの縦長でも2人が収まる）
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h, false);
  cam.aspect = w / h; const dist = Math.max(9.4, 5.6 / (0.536 * cam.aspect));
  cam.position.set(0, 1.9, dist); cam.lookAt(0, 1.45, 0); cam.updateProjectionMatrix();
}
addEventListener('resize', resize); resize();

// ---------- 再生 ----------
let idx = 0, t = 0, playing = !reduce, visible = true, last = performance.now(), clock = 0;
const yaw = { P: 0.25, N: -0.25 }, orbitSpeed = { v: 1 };
const ease = k => 1 - Math.pow(1 - Math.min(1, Math.max(0, k)), 3);
const back = k => { k = Math.min(1, Math.max(0, k)); const c = 1.7; return 1 + (c + 1) * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); };
const hop = (tt, n, dur) => tt < dur ? Math.abs(Math.sin(tt / dur * Math.PI * n)) * 0.35 : 0;

function say(el, text, tt) {
  if (!text) { el.classList.remove('on'); return; }
  const n = Math.min(text.length, Math.floor(tt * 20) + 1);
  if (el.dataset.full !== text) { el.dataset.full = text; }
  el.textContent = text.slice(0, n); el.classList.add('on');
}
function place(el, x, y) {
  const v = new THREE.Vector3(x, y, 0).project(cam), w = stage.clientWidth, h = stage.clientHeight, bw = el.offsetWidth, bh = el.offsetHeight;
  el.style.left = Math.min(w - bw / 2 - 10, Math.max(bw / 2 + 10, (v.x + 1) / 2 * w)) + 'px';
  el.style.top = Math.max(bh + 58, (1 - v.y) / 2 * h) + 'px';
}
// ぬまっぱ博士の吹き出しは、ホログラムのグラフを隠さないよう左側に出す（右端を x に合わせる）
function placeLeftOf(el, x, y) {
  const v = new THREE.Vector3(x, y, 0).project(cam), w = stage.clientWidth, h = stage.clientHeight, bw = el.offsetWidth, bh = el.offsetHeight;
  el.style.left = Math.max(bw / 2 + 10, (v.x + 1) / 2 * w - bw / 2) + 'px';
  el.style.top = Math.max(bh + 58, (1 - v.y) / 2 * h) + 'px';
}

function update(dt) {
  const s = SCENES[idx], k = t / s.dur, a = s.act;
  stepEls.forEach(li => li.classList.toggle('on', +li.dataset.s === s.step));
  let tP = 0.25, tN = -0.25, jP = 0, jN = 0, q = 0, tilt = 0, wave = 0, barMode = 'low';
  orbitSpeed.v = 1;
  if (a === 'intro') { P.scale.setScalar(back(k * 2)); N.scale.setScalar(back(k * 2 - 0.6)); }
  else { P.scale.setScalar(1); N.scale.setScalar(1); }
  if (a === 'ask') { tP = 0.65; tN = -0.4; wave = 1; q = ease(k * 4 - 0.4); }
  if (a === 'why') { tP = 0.5; tN = -0.45; jP = hop(t, 3, 1.8); q = 1; orbitSpeed.v = 7; }
  if (a === 'measure') { tP = 0.45; tN = -0.65; jN = hop(t, 1, 0.6); barMode = 'grow'; }
  if (a === 'data') { tP = 0.35; tN = -0.25; barMode = 'wave'; }
  if (a === 'think') { tP = 0.55; tN = -0.5; tilt = Math.sin(t * 2.4) * 0.12; orbitSpeed.v = 4; q = 0.7 * ease(k * 3); barMode = 'wave'; }
  if (a === 'tell') { tP = 0; tN = 0; jP = hop(t, 2, 1.4); jN = hop(Math.max(0, t - 0.12), 2, 1.4); wave = 2; barMode = 'wave'; }
  if (a === 'end') { tP = 0.12; tN = -0.12; barMode = 'wave'; }

  // 向き・ジャンプ・ゆれ
  const f = Math.min(1, dt * 5);
  yaw.P += (tP - yaw.P) * f; yaw.N += (tN - yaw.N) * f;
  const breathe = Math.sin(clock * 2.2) * 0.015;
  P.rotation.set(0, yaw.P, tilt); N.rotation.set(0, yaw.N, 0);
  P.position.y = jP; N.position.y = jN;
  P.children[0].scale.set(1 - breathe, 1 + breathe, 1 - breathe); N.children[0].scale.set(1 + breathe, 1 - breathe, 1 + breathe);
  sP.scale.set(1 - jP * 0.6, 0.55 * (1 - jP * 0.6), 1); sN.scale.set(1 - jN * 0.6, 0.55 * (1 - jN * 0.6), 1);
  wingR.rotation.z = wingBase + (wave ? Math.sin(clock * (wave > 1 ? 16 : 10)) * 0.28 : Math.sin(clock * 1.5) * 0.05);
  orbit.rotation.y += dt * orbitSpeed.v; holo.rotation.y += dt * (barMode === 'grow' ? 3 : 0.8);
  qMark.scale.setScalar(qMark.scale.x + (q * 0.75 - qMark.scale.x) * f);
  qMark.position.y = 2.35 + jP + Math.sin(clock * 3) * 0.05; qMark.material.rotation = Math.sin(clock * 2.5) * 0.15;

  // ホログラムのグラフ
  bars.forEach((b, i) => {
    let lv = 0.18;
    if (barMode === 'grow') lv = 0.18 + 0.82 * ease((k - 0.15 - i * 0.08) * 2);
    if (barMode === 'wave') lv = 0.75 + 0.25 * Math.sin(clock * 3.2 + i * 1.3);
    b.scale.y = lv; b.position.y = b.userData.h * lv / 2;
  });
  // データの粒
  const plate = N.localToWorld(new THREE.Vector3(0, 2.4, 0)), tab = tablet.getWorldPosition(new THREE.Vector3());
  dots.forEach((d, i) => {
    d.visible = a === 'data';
    if (!d.visible) return;
    const p = ((t * 0.9 + i / dots.length) % 1);
    d.position.lerpVectors(plate, tab, p); d.position.x += Math.sin(p * Math.PI) * 0.95; d.position.y += Math.sin(p * Math.PI) * 0.35; d.position.z += 0.3 * Math.sin(p * Math.PI);
    d.material.opacity = Math.sin(p * Math.PI);
  });
  const pulse = a === 'data' ? 1 + Math.max(0, Math.sin(clock * 9)) * 0.05 : 1;
  tablet.scale.copy(tabBase).multiplyScalar(pulse);
  // 紙吹雪
  confetti.forEach(m => { if (!m.visible) return;
    m.position.addScaledVector(m.userData.v, dt); m.userData.r += dt * 6; m.rotation.set(m.userData.r, m.userData.r * 0.7, 0);
    if (m.position.y < 0) m.material.opacity = Math.max(0, m.material.opacity - dt * 2); if (m.material.opacity <= 0) m.visible = false; });

  // 吹き出し
  say(bP, s.philo, t); say(bN, s.numa, t);
  place(bP, -1.3, 2.75 + jP);
  if (s.philo && s.numa) { bP.style.left = Math.min(parseFloat(bP.style.left), stage.clientWidth / 2 - bP.offsetWidth / 2 - 6) + 'px'; }
  const side = !s.philo; bN.classList.toggle('side', side);
  if (side) placeLeftOf(bN, 0.75, 2.75 + jN); else { place(bN, 1.3, 3.0 + jN); if (s.philo) bN.style.left = Math.max(parseFloat(bN.style.left), stage.clientWidth / 2 + bN.offsetWidth / 2 + 6) + 'px'; }
  bar.style.width = ((SCENES.slice(0, idx).reduce((x, c) => x + c.dur, 0) + t) / TOTAL * 100) + '%';
}

function next() {
  idx = (idx + 1) % SCENES.length; t = 0;
  if (SCENES[idx].act === 'tell') resetConfetti();
  if (SCENES[idx].act === 'intro') confetti.forEach(m => m.visible = false);
}
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (playing && visible) { t += dt; clock += dt; if (t >= SCENES[idx].dur) next(); }
  if (visible) { update(playing ? dt : 0); renderer.render(scene, cam); }
  requestAnimationFrame(frame);
}

btnPlay.addEventListener('click', () => { playing = !playing; btnPlay.textContent = playing ? '❚❚' : '▶'; btnPlay.setAttribute('aria-label', playing ? '一時停止' : '再生'); });
$('cAgain').addEventListener('click', () => { idx = 0; t = 0; confetti.forEach(m => m.visible = false); if (!playing) btnPlay.click(); });
new IntersectionObserver(es => { visible = es[0].isIntersecting; last = performance.now(); }).observe(stage);

// 確認用：?scene=data などで、その場面から始める（&pause を付けると t 秒で止める）
const qs = new URLSearchParams(location.search), qScene = SCENES.findIndex(s => s.act === qs.get('scene'));
if (qScene >= 0) { idx = qScene; t = +(qs.get('t') || 0); clock = t; if (SCENES[idx].act === 'tell') resetConfetti(); if (qs.has('pause')) btnPlay.click(); }
if (reduce) {   // 動きを減らす設定：最後の場面で止め、セリフは文字で見せる
  idx = SCENES.findIndex(s => s.act === 'tell'); t = 3; btnPlay.textContent = '▶'; btnPlay.setAttribute('aria-label', '再生');
  document.querySelector('.script').open = true;
}
requestAnimationFrame(frame);
