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
const cam = new THREE.PerspectiveCamera(30, 1, 0.1, 120);
const hemi = new THREE.HemisphereLight(0xffffff, 0x8a8fa8, 0.8 * Math.PI); scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffffff, 0.75 * Math.PI); sun.position.set(3, 5, 5); scene.add(sun);

// ---------- 背景：牛久沼の一日（問う＝夜、確かめる＝朝〜昼、伝える＝夕焼け） ----------
// 色の組。0 夜 → 1 朝 → 2 昼 → 3 夕焼け → 4 夜（くり返しで夜へ戻る用）
const PAL = [
  { top: '#0a1530', hor: '#2d4479', water: '#152b51', far: '#25385f', near: '#0f1d38', ground: '#22403b', reed: '#1c3d31', plume: '#6d7684', hemi: '#cdd6ff', hemiI: 0.66, sunC: '#b8c6ff', sunI: 0.52, glint: '#e6eeff', glintA: 0.75, stars: 1, moon: 1, sun: 0, disc: '#ffe9b0', sx: 15, sy: -3 },
  { top: '#4b6ba9', hor: '#f6c2a2', water: '#7d90b6', far: '#7b86a3', near: '#3f5069', ground: '#527758', reed: '#3f6342', plume: '#cfae8c', hemi: '#ffe8da', hemiI: 0.74, sunC: '#ffd3ad', sunI: 0.66, glint: '#ffe2c4', glintA: 0.6, stars: 0.05, moon: 0.15, sun: 1, disc: '#ffd9a0', sx: 14, sy: 2.3 },
  { top: '#4f9be0', hor: '#d6edf7', water: '#5ba7cf', far: '#93b6b2', near: '#4d8a5b', ground: '#7aae63', reed: '#4f8b3f', plume: '#cdb67e', hemi: '#ffffff', hemiI: 0.8, sunC: '#ffffff', sunI: 0.75, glint: '#ffffff', glintA: 0.4, stars: 0, moon: 0, sun: 1, disc: '#fff6d6', sx: 12.5, sy: 8.4 },
  { top: '#2f3672', hor: '#f59b54', water: '#b6735f', far: '#8c5d6c', near: '#4b3651', ground: '#5f5b3f', reed: '#4b4a2d', plume: '#e2a262', hemi: '#ffe1c9', hemiI: 0.74, sunC: '#ffb47e', sunI: 0.8, glint: '#ffc271', glintA: 0.85, stars: 0.12, moon: 0, sun: 1, disc: '#ff8f3e', sx: 11, sy: 2.6 },
];
PAL.push(PAL[0]);
// 案2：季節がめぐる牛久沼（?bg=season のとき）。0 春 → 1 夏 → 2 秋 → 3 冬 → 4 春
const SEASON = [
  { top: '#6aaee6', hor: '#e3f1f8', water: '#6fb2d3', far: '#b9c9c4', near: '#e7a6bc', ground: '#8cbf6c', reed: '#6a9c4a', plume: '#d8c88e', hemi: '#ffffff', hemiI: 0.8, sunC: '#fff8f0', sunI: 0.75, glint: '#ffffff', glintA: 0.4, stars: 0, moon: 0, sun: 1, disc: '#fff6d6', sx: 12.5, sy: 8.4 },
  { top: '#2f86e0', hor: '#bfe4f7', water: '#3f97c9', far: '#6f9f86', near: '#2f7a45', ground: '#5aa04a', reed: '#3f8a35', plume: '#a9b56a', hemi: '#ffffff', hemiI: 0.82, sunC: '#fffbe8', sunI: 0.8, glint: '#ffffff', glintA: 0.55, stars: 0, moon: 0, sun: 1, disc: '#fffbe0', sx: 12.5, sy: 8.8 },
  { top: '#7aa6d6', hor: '#f3e1c4', water: '#6a95b5', far: '#b59a7e', near: '#cf6a32', ground: '#a59a52', reed: '#b08a42', plume: '#e8c27a', hemi: '#fff0dc', hemiI: 0.78, sunC: '#ffe2b8', sunI: 0.75, glint: '#ffe6c0', glintA: 0.45, stars: 0, moon: 0, sun: 1, disc: '#ffe8b8', sx: 12.5, sy: 7.6 },
  { top: '#9bb3cc', hor: '#e9eef3', water: '#7f98ad', far: '#e2e8ee', near: '#8d9aa8', ground: '#e3eaee', reed: '#9a8a6a', plume: '#cfc6b0', hemi: '#eef3ff', hemiI: 0.85, sunC: '#e8eeff', sunI: 0.6, glint: '#ffffff', glintA: 0.35, stars: 0, moon: 0, sun: 1, disc: '#f4f6ff', sx: 12.5, sy: 6.4 },
];
SEASON.push(SEASON[0]);
const BG = ({ season: 'season', note: 'note' })[new URLSearchParams(location.search).get('bg')] || 'day';
const PALS = BG === 'season' ? SEASON : PAL;
// 牛久大仏の色（夜・朝・昼・夕／春・夏・秋・冬）
['#0e1736', '#7a6f8c', '#7f8fa1', '#5e3f58'].forEach((c, i) => { PAL[i].statue = c; });
['#97a3ae', '#7f8f9a', '#9a8f88', '#a9b4bf'].forEach((c, i) => { SEASON[i].statue = c; });
const COLOR_KEYS = ['top', 'hor', 'water', 'far', 'near', 'ground', 'reed', 'plume', 'hemi', 'sunC', 'glint', 'disc', 'statue'];
[PAL.slice(0, 4), SEASON.slice(0, 4)].flat().forEach(p => COLOR_KEYS.forEach(k => { p[k] = new THREE.Color(p[k]); }));
const cur = Object.fromEntries(COLOR_KEYS.map(k => [k, new THREE.Color()]));

scene.fog = new THREE.Fog(0x2d4479, 16, 48);
const bg = new THREE.Group(); scene.add(bg);
const basic = (o = {}) => new THREE.MeshBasicMaterial(o);

// 空（下は地平線の色、上は空の色。太陽のまわりを明るく）
const skyMat = new THREE.ShaderMaterial({
  uniforms: { top: { value: new THREE.Color() }, hor: { value: new THREE.Color() }, sunPos: { value: new THREE.Vector2() }, sunCol: { value: new THREE.Color() }, glow: { value: 0 } },
  vertexShader: 'varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
  fragmentShader: `uniform vec3 top, hor, sunCol; uniform vec2 sunPos; uniform float glow; varying vec3 vW;
    void main(){ float h = clamp(vW.y / 16.0, 0.0, 1.0); vec3 c = mix(hor, top, pow(h, 0.55));
      float d = distance(vW.xy, sunPos); c += sunCol * glow * (exp(-d * 0.16) * 0.55 + exp(-d * 0.6) * 0.5);
      gl_FragColor = vec4(c, 1.0);
      #include <colorspace_fragment>
    }`,
  depthWrite: false,
});
const sky = new THREE.Mesh(new THREE.PlaneGeometry(260, 90), skyMat); sky.position.set(0, 30, -30); bg.add(sky);

// 星（2組に分けて、交互にまたたかせる）
const starSets = [0, 1].map(() => {
  const pos = []; for (let i = 0; i < 110; i++) pos.push((Math.random() - 0.5) * 90, 3 + Math.random() * 20, -29.5);
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const m = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 2.2, sizeAttenuation: false, transparent: true, fog: false, depthWrite: false }));
  bg.add(m); return m;
});

// ふわっと光る円（月・太陽のまわり）
const glowTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d');
  const g = x.createRadialGradient(64, 64, 0, 64, 64, 64); g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.25, 'rgba(255,255,255,.45)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g; x.fillRect(0, 0, 128, 128); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
const glowSprite = (col, s) => { const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: col, transparent: true, depthWrite: false, fog: false })); m.scale.setScalar(s); return m; };

// 月（右上。左上はフィロの吹き出しと「？」が出るので空けておく）
const moon = new THREE.Group(); moon.position.set(15.5, 8.6, -29);
const moonTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');   // 三日月（欠けた所は透明）
  x.fillStyle = '#fff4d6'; x.beginPath(); x.arc(128, 128, 120, 0, Math.PI * 2); x.fill();
  x.globalCompositeOperation = 'destination-out'; x.beginPath(); x.arc(70, 100, 108, 0, Math.PI * 2); x.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
const moonDisc = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 2.6), basic({ map: moonTex, transparent: true, fog: false, depthWrite: false }));
const moonGlow = glowSprite(0xdfe6ff, 7); moonGlow.position.z = -0.05;
moon.add(moonGlow, moonDisc); bg.add(moon);

// 太陽
const sunG = new THREE.Group();
const sunDisc = new THREE.Mesh(new THREE.CircleGeometry(1.5, 48), basic({ color: 0xffffff, transparent: true, fog: false }));
const sunGlow = glowSprite(0xffffff, 9); sunGlow.position.z = -0.05;
sunG.add(sunGlow, sunDisc); bg.add(sunG);

// 向こう岸（遠くの丘と、手前の林）
const ridge = (z, base, f) => {
  const s = new THREE.Shape(); s.moveTo(-70, -1);
  for (let x = -70; x <= 70; x += 0.4) s.lineTo(x, base + f(x));
  s.lineTo(70, -1); s.closePath();
  const m = new THREE.Mesh(new THREE.ShapeGeometry(s), basic({ color: 0xffffff })); m.position.z = z; bg.add(m); return m;
};
const farHill = ridge(-27, 1.3, x => 0.9 * Math.sin(x * 0.11 + 1) + 0.5 * Math.sin(x * 0.27 + 2) + 0.25 * Math.sin(x * 0.7));
const nearWood = ridge(-19, 0.35, x => 0.22 * Math.abs(Math.sin(x * 1.9)) + 0.18 * Math.abs(Math.sin(x * 3.1 + 1)) + 0.28 * Math.sin(x * 0.35) + (Math.abs(x + 2) < 5 ? -0.4 : 0));

// 牛久大仏（向こう岸の奥にかすんで立つ影。左のヨシとフィロのあいだに見える位置）
// 阿弥陀如来の立像：右手（見る側の左）は胸の前に上げて手のひらを前へ、左手（見る側の右）は下ろして手のひらを前へ。袖は両腕から長く垂れる
const daibutsu = new THREE.Group(), statueMat = basic({ color: 0xffffff, fog: false }), handMat = basic({ color: 0xffffff, fog: false }), foldMat = basic({ color: 0xffffff, fog: false });   // もやは色の方で表すので fog は切る
{ const poly = (pts, mat, z = 0) => { const sh = new THREE.Shape(); sh.moveTo(...pts[0]); pts.slice(1).forEach(p => sh.lineTo(...p)); sh.closePath();
    const m = new THREE.Mesh(new THREE.ShapeGeometry(sh), mat); m.position.z = z; daibutsu.add(m); return m; };
  const oval = (x, y, rx, ry, mat, z = 0) => { const m = new THREE.Mesh(new THREE.CircleGeometry(1, 32), mat); m.position.set(x, y, z); m.scale.set(rx, ry, 1); daibutsu.add(m); return m; };
  // 台座（基壇と蓮の花の台）
  poly([[-0.62, 0], [0.62, 0], [0.62, 0.13], [-0.62, 0.13]], statueMat);
  poly([[-0.5, 0.13], [0.5, 0.13], [0.6, 0.22], [0.46, 0.27], [0.5, 0.31], [0.34, 0.37], [-0.34, 0.37], [-0.5, 0.31], [-0.46, 0.27], [-0.6, 0.22]], statueMat);
  // 体（衣のすそ → 腰 → 肩。肩はなで肩で広め）
  poly([[-0.3, 0.37], [0.3, 0.37], [0.29, 0.9], [0.31, 1.5], [0.36, 2.05], [0.36, 2.25], [0.3, 2.4], [0.15, 2.48], [0.12, 2.56], [-0.12, 2.56], [-0.15, 2.48], [-0.3, 2.4], [-0.36, 2.25], [-0.36, 2.05], [-0.31, 1.5], [-0.29, 0.9]], statueMat);
  // 袖：右腕（見る側の左）は肘から曲げて上げるので、袖は肘の下から長く垂れる
  poly([[-0.36, 2.15], [-0.42, 1.95], [-0.47, 1.45], [-0.46, 1.0], [-0.4, 0.92], [-0.33, 1.05], [-0.3, 1.55]], statueMat);
  // 左腕（見る側の右）は下ろしているので、袖は手首の外側に沿って垂れる
  poly([[0.36, 2.15], [0.43, 1.85], [0.47, 1.35], [0.46, 0.98], [0.4, 0.9], [0.33, 1.02], [0.3, 1.5]], statueMat);
  // 頭（螺髪の丸い頭と肉髻）
  oval(0, 2.76, 0.205, 0.245, statueMat); oval(0, 2.98, 0.135, 0.085, statueMat);
  // 右手：前腕を立てて胸の高さへ、手のひらを前に向け指は上
  poly([[-0.27, 1.98], [-0.17, 1.98], [-0.17, 2.1], [-0.27, 2.1]], handMat, 0.01);   // 袖口から出た手首
  oval(-0.215, 2.19, 0.085, 0.11, handMat, 0.012); oval(-0.12, 2.14, 0.03, 0.05, handMat, 0.013);   // 手のひらと親指（手のひらが前向きなので親指は体の中心側）
  // 左手：腰の横に下ろし、手のひらを前に向け指は下
  poly([[0.23, 1.6], [0.33, 1.6], [0.33, 1.5], [0.23, 1.5]], handMat, 0.01);
  oval(0.28, 1.4, 0.08, 0.11, handMat, 0.012); oval(0.19, 1.45, 0.03, 0.05, handMat, 0.013);
  // 衣のひだ（胸から足もとへ U 字に垂れる線）と、前の合わせ目
  const strip = (pts, w) => { const v = [], idx = []; pts.forEach(([x, y], i) => { const [px, py] = pts[Math.max(0, i - 1)], [nx, ny] = pts[Math.min(pts.length - 1, i + 1)];
      const dx = nx - px, dy = ny - py, l = Math.hypot(dx, dy) || 1; v.push(x - dy / l * w, y + dx / l * w, 0.005, x + dy / l * w, y - dx / l * w, 0.005);
      if (i) idx.push(2 * i - 2, 2 * i - 1, 2 * i, 2 * i - 1, 2 * i + 1, 2 * i); });
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3)); g.setIndex(idx); daibutsu.add(new THREE.Mesh(g, foldMat)); };
  const sag = (x0, x1, y, d) => Array.from({ length: 13 }, (_, i) => { const f = i / 12; return [x0 + (x1 - x0) * f, y - Math.sin(f * Math.PI) * d]; });
  strip(sag(-0.12, 0.3, 2.36, 0.16), 0.018); strip(sag(-0.1, 0.3, 2.12, 0.2), 0.018);
  strip(sag(-0.27, 0.27, 1.68, 0.22), 0.02); strip(sag(-0.27, 0.27, 1.25, 0.2), 0.02); strip(sag(-0.26, 0.26, 0.85, 0.16), 0.02);
  strip([[0.02, 1.62], [0.0, 1.1], [0.02, 0.4]], 0.016); }
daibutsu.position.set(-10.5, 0.25, -22); daibutsu.scale.setScalar(1.75); bg.add(daibutsu);   // x は resize() で画面の幅に合わせる
// 台座の下の小さな丘
const knoll = new THREE.Mesh(new THREE.CircleGeometry(2.3, 32, 0, Math.PI), basic({ color: 0xffffff })); knoll.scale.y = 0.26; knoll.position.set(-10.5, 0, -21.9); bg.add(knoll);

// 沼の水面
const water = new THREE.Mesh(new THREE.PlaneGeometry(200, 28), basic({ color: 0xffffff })); water.rotation.x = -Math.PI / 2; water.position.set(0, -0.02, -15.5); bg.add(water);
// 月や太陽の光が水面に映る筋
const glints = Array.from({ length: 18 }, (_, i) => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 0.06), basic({ color: 0xffffff, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  m.rotation.x = -Math.PI / 2; m.userData.z = -18 + i * 0.9; m.userData.w = 0.6 + Math.random() * 0.9; m.userData.ph = Math.random() * 6; bg.add(m); return m;
});
// 水面のさざ波
const ripples = Array.from({ length: 22 }, () => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(0.9 + Math.random() * 1.2, 0.035), basic({ color: 0xffffff, transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2; m.position.set((Math.random() - 0.5) * 30, 0, -3 - Math.random() * 14); m.userData.ph = Math.random() * 6; m.userData.v = 0.15 + Math.random() * 0.2; bg.add(m); return m;
});

// 手前の岸（2人が立つ草地と、水ぎわ）
const ground = new THREE.Mesh(new THREE.PlaneGeometry(90, 14), basic({ color: 0xffffff })); ground.rotation.x = -Math.PI / 2; ground.position.set(0, -0.005, 5.5); bg.add(ground);
const bank = new THREE.Mesh(new THREE.PlaneGeometry(90, 0.22), basic({ color: 0xffffff })); bank.rotation.x = -Math.PI / 2; bank.position.set(0, -0.003, -1.45); bg.add(bank);

// ヨシ（両はしの水ぎわ。風でゆれる）
const reedMat = basic({ color: 0xffffff }), plumeMat = basic({ color: 0xffffff });
const reedGeo = new THREE.CylinderGeometry(0.012, 0.028, 1, 5); reedGeo.translate(0, 0.5, 0);
const plumeGeo = new THREE.SphereGeometry(1, 8, 6);
const reeds = [];
[[-1, 3.7, 6.2], [1, 3.9, 6.4]].forEach(([side, x0, x1]) => {
  for (let i = 0; i < 26; i++) {
    const g = new THREE.Group(), h = 1.0 + Math.random() * 1.1;
    const st = new THREE.Mesh(reedGeo, reedMat); st.scale.y = h; g.add(st);
    if (Math.random() < 0.7) { const pl = new THREE.Mesh(plumeGeo, plumeMat); pl.scale.set(0.05, 0.16, 0.05); pl.position.y = h + 0.1; g.add(pl); }
    g.position.set(side * (x0 + Math.random() * (x1 - x0)), 0, -1.6 + Math.random() * 1.9);
    g.rotation.z = side * -0.06 + (Math.random() - 0.5) * 0.12; g.userData.base = g.rotation.z; g.userData.ph = Math.random() * 6;
    bg.add(g); reeds.push(g);
  }
});

// 案2の飾り：夏の入道雲、春の花びら・秋の落ち葉・冬の雪、季節の札
const cloud = new THREE.Group(); cloud.position.set(-11, 3.2, -28.5);
[[0, 0, 2.2], [2.2, -0.4, 1.7], [-2.1, -0.5, 1.6], [0.9, 1.6, 1.6], [-1.0, 1.3, 1.4], [3.6, -0.9, 1.1], [-3.5, -0.9, 1.0]].forEach(([x, y, r]) => {
  const m = new THREE.Mesh(new THREE.CircleGeometry(r, 40), basic({ color: 0xffffff, transparent: true, fog: false, depthWrite: false })); m.position.set(x, y, 0); cloud.add(m); });
cloud.visible = false; bg.add(cloud);
const flakes = Array.from({ length: 80 }, () => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(0.09, 0.06), basic({ color: 0xffffff, side: THREE.DoubleSide, transparent: true, depthWrite: false }));
  m.position.set((Math.random() - 0.5) * 13, Math.random() * 5.5, (Math.random() - 0.5) * 4 - 0.5); m.userData.ph = Math.random() * 6; m.userData.v = 0.35 + Math.random() * 0.35; m.visible = false; bg.add(m); return m;
});
const FLAKE_COL = [new THREE.Color('#f7b3c6'), new THREE.Color('#ffffff'), new THREE.Color('#e27b34'), new THREE.Color('#ffffff')];
const chip = document.createElement('div'); chip.className = 'season-chip'; chip.hidden = BG !== 'season'; stage.appendChild(chip);
const SEASON_NAME = ['春　4月', '夏　7月', '秋　10月', '冬　1月'];
function paintSeason(p, clock, dt, a) {
  const w = i => Math.max(0, 1 - Math.abs(p - i)) + (i === 0 ? Math.max(0, 1 - Math.abs(p - 4)) : 0);   // 各季節の強さ
  cloud.visible = w(1) > 0.01; cloud.children.forEach(c => { c.material.opacity = w(1) * 0.95; });
  cloud.position.y = 3.2 + w(1) * 0.6;
  const fall = 1 - w(1), col = new THREE.Color(0, 0, 0);
  [0, 2, 3].forEach(i => col.add(FLAKE_COL[i].clone().multiplyScalar(w(i) / Math.max(0.001, fall))));
  flakes.forEach(m => {
    m.visible = fall > 0.02; if (!m.visible) return;
    const snow = w(3) / Math.max(0.001, fall);
    m.position.y -= m.userData.v * dt * (1 - snow * 0.35); m.position.x += Math.sin(clock * 1.6 + m.userData.ph) * dt * 0.35 * (1 - snow * 0.6);
    if (m.position.y < 0) { m.position.y = 5.5; m.position.x = (Math.random() - 0.5) * 13; }
    m.rotation.set(clock * 2 * (1 - snow) + m.userData.ph, clock * 1.4 * (1 - snow), 0);
    m.material.color.copy(col); m.material.opacity = fall * 0.9;
  });
  const sIdx = Math.round(p) % 4, show = a === 'data' || a === 'think';
  chip.textContent = SEASON_NAME[sIdx]; chip.classList.toggle('on', show);
}

// 時刻（0〜4）に合わせて色と明るさを変える
const lerpPal = (p) => {
  const i = Math.min(3, Math.floor(p)), f = p - i, A = PALS[i], B = PALS[i + 1];
  COLOR_KEYS.forEach(k => cur[k].lerpColors(A[k], B[k], f));
  const n = k => A[k] + (B[k] - A[k]) * f;
  return { hemiI: n('hemiI'), sunI: n('sunI'), glintA: n('glintA'), stars: n('stars'), moon: n('moon'), sun: n('sun'), sx: n('sx'), sy: n('sy') };
};
let tod = 0;
function paintSky(p, clock, dt) {
  tod = p; const v = lerpPal(p);
  skyMat.uniforms.top.value.copy(cur.top); skyMat.uniforms.hor.value.copy(cur.hor);
  scene.fog.color.copy(cur.hor);
  water.material.color.copy(cur.water); farHill.material.color.copy(cur.far); statueMat.color.copy(cur.statue); handMat.color.copy(cur.statue).lerp(cur.hor, 0.3); foldMat.color.copy(cur.statue).lerp(cur.hor, 0.18); knoll.material.color.copy(cur.near); nearWood.material.color.copy(cur.near);
  ground.material.color.copy(cur.ground); bank.material.color.copy(cur.ground).multiplyScalar(0.7);
  reedMat.color.copy(cur.reed); plumeMat.color.copy(cur.plume);
  hemi.color.copy(cur.hemi); hemi.intensity = v.hemiI * Math.PI; sun.color.copy(cur.sunC); sun.intensity = v.sunI * Math.PI;
  starSets.forEach((s, i) => { s.material.opacity = v.stars * (0.65 + 0.35 * Math.sin(clock * 2.3 + i * 3)); s.visible = v.stars > 0.01; });
  moon.visible = v.moon > 0.01; moonDisc.material.opacity = v.moon; moonGlow.material.opacity = v.moon * 0.55;
  sunG.visible = v.sun > 0.01; sunG.position.set(v.sx, v.sy, -28.8); sunDisc.material.color.copy(cur.disc); sunDisc.material.opacity = v.sun; sunGlow.material.color.copy(cur.disc); sunGlow.material.opacity = v.sun * 0.7;
  skyMat.uniforms.sunPos.value.set(v.sx, v.sy); skyMat.uniforms.sunCol.value.copy(cur.disc); skyMat.uniforms.glow.value = v.sun * (p > 2.4 || p < 1.6 ? 0.9 : 0.35);
  // 光の筋：夜は月の下、昼と夕方は太陽の下に並べる
  const lx = v.moon > v.sun ? moon.position.x : v.sx, ly = v.moon > v.sun ? moon.position.y : v.sy, dz = cam.position.z;
  const high = Math.min(1, Math.max(0, (ly - 1) / 14));   // 高い太陽ほど筋は手前に短く
  glints.forEach(g => {
    const z = g.userData.z; g.position.set(lx * (dz - z) / (dz + 28.8), 0.001, z);
    const flick = 0.55 + 0.45 * Math.sin(clock * 3 + g.userData.ph);
    g.scale.x = g.userData.w * (1.4 - (z + 18) / 18 * 0.8) * (1 + high);
    g.material.color.copy(cur.glint); g.material.opacity = v.glintA * flick * (1 - high * 0.5);
  });
  ripples.forEach(r => { r.position.x += r.userData.v * dt; if (r.position.x > 15) r.position.x = -15;
    r.material.color.copy(cur.hor); r.material.opacity = 0.25 * (0.5 + 0.5 * Math.sin(clock * 1.2 + r.userData.ph)); });
  reeds.forEach(r => { r.rotation.z = r.userData.base + Math.sin(clock * 1.3 + r.userData.ph + r.position.x * 0.3) * 0.045; });
}
const smooth = (e0, e1, x) => { x = Math.min(1, Math.max(0, (x - e0) / (e1 - e0))); return x * x * (3 - 2 * x); };
let looped = false;   // 2周目以降は、夕焼けから夜に戻してから始める
function timeOfDay(a, t) {
  if (BG === 'season') {   // 測るまでは春、データの場面で春→夏→秋→冬、考える場面は冬、伝える場面でまた春
    if (a === 'data') { const seg = t / 1.1, i = Math.floor(seg); return Math.min(3, i + smooth(0.5, 1, seg - i)); }
    if (a === 'think') return 3;
    if (a === 'tell') return 3 + smooth(0, 1.8, t);
    return 0;
  }
  if (a === 'intro') return looped ? 3 + smooth(0, 1.6, t) : 0;
  if (a === 'ask' || a === 'why') return 0;
  if (a === 'measure') return 2 * smooth(0, 2.6, t);
  if (a === 'tell') return 2 + smooth(0, 1.8, t);
  if (a === 'end') return 3;
  return 2;
}

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
  if (scene.fog) { scene.fog.near = dist + 6; scene.fog.far = dist + 40; }
  // 大仏は、画面の左はしから約2割の所（左のヨシとフィロのあいだ）に来るように
  daibutsu.position.x = knoll.position.x = -(dist + 22) * Math.tan(cam.fov * Math.PI / 360) * cam.aspect * 0.62;   // 2人にはかからない距離から
}
addEventListener('resize', resize); resize();

// ---------- 案3：研究ノートの世界（?bg=note のとき） ----------
// 方眼ノートが床から壁へ曲がって立ち上がる紙の舞台。問う＝「？」の落書き、確かめる＝表とグラフ、伝える＝ページをめくって発表ポスター
const note = new THREE.Group(); note.visible = BG === 'note'; scene.add(note);
const ORDER = SCENES.map(s => s.act);
const PEN = '#3b4c70', RED = '#e5484d', FONT = '"Zen Kaku Gothic New", "Hiragino Sans", sans-serif';
const TEMPS = [6, 7, 10, 15, 20, 24, 28, 29, 25, 19, 13, 8];
let paintNote = () => {};
if (BG === 'note') {
  bg.visible = false; scene.fog = null;
  hemi.color.set(0xffffff); hemi.intensity = 0.8 * Math.PI; sun.color.set(0xffffff); sun.intensity = 0.75 * Math.PI;
  // 方眼の紙（1マス0.25）
  const gridTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');
    x.fillStyle = '#fbf7ec'; x.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 8; i++) { x.strokeStyle = i ? '#d5e3ee' : '#a9c8e2'; x.lineWidth = i ? 2 : 3; x.beginPath(); x.moveTo(i * 32 + 0.5, 0); x.lineTo(i * 32 + 0.5, 256); x.moveTo(0, i * 32 + 0.5); x.lineTo(256, i * 32 + 0.5); x.stroke(); }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; return t; })();
  // 床（z=12→-5）→ 半径1の曲面 → 壁（z=-6）
  const L = 17 + Math.PI / 2 + 10, paperGeo = new THREE.PlaneGeometry(44, L, 1, 90), pa = paperGeo.attributes.position;
  for (let i = 0; i < pa.count; i++) { const sv = pa.getY(i) + L / 2; let Y, Z;
    if (sv < 17) { Y = 0; Z = 12 - sv; } else if (sv < 17 + Math.PI / 2) { const th = sv - 17; Y = 1 - Math.cos(th); Z = -5 - Math.sin(th); } else { Y = 1 + (sv - 17 - Math.PI / 2); Z = -6; }
    pa.setXYZ(i, pa.getX(i), Y, Z); }
  paperGeo.computeVertexNormals(); gridTex.repeat.set(22, L / 2);
  note.add(new THREE.Mesh(paperGeo, new THREE.MeshLambertMaterial({ map: gridTex })));

  // 壁に描く絵（x -8.5〜8.5、y 1.25〜5.75 を 1単位120pxのキャンバスに。中の座標は 0.75 上にずらして書いている）
  const S = 120, W = 17, H = 4.5, cw = W * S, ch = H * S;
  const mkCanvas = () => { const c = document.createElement('canvas'); c.width = cw; c.height = ch; return c; };
  const ink = mkCanvas(), ix = ink.getContext('2d'), inkTex = new THREE.CanvasTexture(ink); inkTex.colorSpace = THREE.SRGBColorSpace; inkTex.anisotropy = 8;
  const inkPlane = new THREE.Mesh(new THREE.PlaneGeometry(W, H), new THREE.MeshBasicMaterial({ map: inkTex, transparent: true, depthWrite: false }));
  inkPlane.position.set(0, 2 + H / 2 - 0.75, -5.97); note.add(inkPlane);
  const P = (x, y) => [(x + 8.5) * S, (6.5 - y) * S];
  const clamp = k => Math.min(1, Math.max(0, k));

  // 描く道具
  const line = (x, pts, k, col = PEN, w = 6) => { if (k <= 0) return; const n = pts.length - 1, upto = k * n, m = Math.floor(upto);
    x.strokeStyle = col; x.lineWidth = w; x.lineCap = x.lineJoin = 'round'; x.beginPath(); x.moveTo(...P(...pts[0]));
    for (let i = 1; i <= Math.min(n, m); i++) x.lineTo(...P(...pts[i]));
    if (m < n) { const a = pts[m], b = pts[m + 1], f = upto - m; x.lineTo(...P(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)); }
    x.stroke(); };
  const text = (x, str, px, py, size, k, { col = PEN, align = 'left', rot = 0, weight = 700, type = false } = {}) => { if (k <= 0) return;
    const shown = type ? str.slice(0, Math.ceil(str.length * k)) : str, pop = type ? 1 : 0.6 + 0.4 * Math.min(1, k * 1.6) + Math.sin(Math.min(1, k) * Math.PI) * 0.12;
    x.save(); x.translate(...P(px, py)); x.rotate(rot); x.scale(pop, pop); x.globalAlpha = type ? 1 : Math.min(1, k * 2);
    x.font = `${weight} ${size * S}px ${FONT}`; x.textAlign = align; x.textBaseline = 'middle'; x.fillStyle = col; x.fillText(shown, 0, 0); x.restore(); };
  const ring = (x, cx, cy, rx, ry, k, col = RED, w = 7) => { const pts = []; for (let i = 0; i <= 40; i++) { const a = -0.6 + i / 40 * Math.PI * 2.15; pts.push([cx + Math.cos(a) * rx * (1 + i * 0.002), cy + Math.sin(a) * ry]); } line(x, pts, k, col, w); };
  const gx = i => 4.75 + i * (3.1 / 11), gy = v => 2.45 + (v - 4) / 27 * 1.55;
  const wave = (x0, x1, y, amp = 0.05) => { const pts = []; for (let v = x0; v <= x1 + 1e-6; v += 0.1) pts.push([v, y + Math.sin(v * 9) * amp]); return pts; };
  const rrect = (x, x0, y0, x1, y1, fill, stroke) => { const [a, b] = P(x0, y1), [c, d] = P(x1, y0); x.fillStyle = fill; x.strokeStyle = stroke; x.lineWidth = 8;
    x.beginPath(); x.roundRect(a, b, c - a, d - b, 28); x.fill(); x.stroke(); };
  const sticky = (x, cx, cy, rot, fill, lines) => { x.save(); const [a, b] = P(cx, cy); x.translate(a, b); x.rotate(rot);
    x.shadowColor = 'rgba(0,0,0,.18)'; x.shadowBlur = 14; x.shadowOffsetY = 6; x.fillStyle = fill; x.fillRect(-0.72 * S, -0.62 * S, 1.44 * S, 1.24 * S); x.shadowColor = 'transparent';
    x.fillStyle = '#172443'; x.font = `800 ${0.27 * S}px ${FONT}`; x.textAlign = 'center'; x.textBaseline = 'middle';
    lines.forEach((l, i) => x.fillText(l, 0, (i - (lines.length - 1) / 2) * 0.36 * S)); x.restore(); };
  const star = (x, cx, cy, r, col) => { const [a, b] = P(cx, cy); x.fillStyle = col; x.beginPath();
    for (let i = 0; i < 10; i++) { const rr = i % 2 ? r * 0.45 : r, an = -Math.PI / 2 + i * Math.PI / 5; x.lineTo(a + Math.cos(an) * rr * S, b + Math.sin(an) * rr * S); } x.fill(); };

  // ノートの中身（cur＝今の場面の番号、tt＝その場面の経過秒）
  function notebook(x, cur, tt) {
    const pr = (act, t0, dur) => { const ai = ORDER.indexOf(act); return cur > ai ? 1 : cur < ai ? 0 : clamp((tt - t0) / dur); };
    // 問う：「？」と問いを書く
    text(x, '？', -7.55, 4.62, 1.05, pr('ask', 0.2, 0.5), { weight: 900, rot: -0.12 });
    text(x, '季節で変わる？', -6.75, 4.72, 0.4, pr('ask', 0.8, 1.2), { type: true });
    line(x, wave(-6.75, -4.2, 4.38), pr('ask', 2.1, 0.6), PEN, 5);
    ['なぜ？', 'なぜ？', 'なぜ？'].forEach((w, i) => text(x, w, [4.9, 6.35, 7.6][i], [4.95, 4.6, 5.0][i], 0.36, pr('why', 0.15 + i * 0.6, 0.35), { align: 'center', rot: [-0.14, 0.1, -0.06][i] }));
    // 確かめる：表を書く
    line(x, [[-8.1, 3.82], [-5.4, 3.82]], pr('measure', 0.3, 0.4)); line(x, [[-6.85, 4.1], [-6.85, 2.2]], pr('measure', 0.5, 0.4));
    text(x, '月', -7.5, 3.98, 0.27, pr('measure', 0.4, 0.3), { align: 'center' }); text(x, '水温', -6.15, 3.98, 0.27, pr('measure', 0.5, 0.3), { align: 'center' });
    [['4月', '15℃'], ['7月', '28℃'], ['10月', '19℃'], ['1月', '6℃']].forEach(([m, v], i) => { const k = pr('measure', 1.0 + i * 0.55, 0.35), y = 3.55 - i * 0.4;
      text(x, m, -7.5, y, 0.27, k, { align: 'center', weight: 500 }); text(x, v, -6.15, y, 0.27, k, { align: 'center', weight: 500 }); });
    // データ：グラフを書く
    line(x, [[4.6, 4.15], [4.6, 2.35], [8.05, 2.35]], pr('data', 0, 0.45));
    text(x, '水温', 4.62, 4.32, 0.22, pr('data', 0.2, 0.3), { align: 'center' }); text(x, '月', 8.12, 2.2, 0.22, pr('data', 0.3, 0.3), { align: 'center' });
    const kd = pr('data', 0.4, 3.4), pts = TEMPS.map((v, i) => [gx(i), gy(v)]);
    line(x, pts, kd, '#1fa583', 7);
    pts.forEach(([px, py], i) => { if (kd * 11 >= i - 0.01) { const [a, b] = P(px, py); x.fillStyle = '#1fa583'; x.beginPath(); x.arc(a, b, 10, 0, Math.PI * 2); x.fill(); } });
    // 考える：赤ペンで山に丸と「！」、問いに二重線
    ring(x, gx(7), gy(29), 0.42, 0.3, pr('think', 0.3, 0.8));
    text(x, '！', gx(7) + 0.62, gy(29) + 0.32, 0.55, pr('think', 1.0, 0.4), { col: RED, weight: 900, rot: 0.15 });
    line(x, wave(-6.75, -4.2, 4.28, 0.03), pr('think', 1.6, 0.6), RED, 5);
  }
  // 伝える：発表ポスター
  function poster(x) {
    rrect(x, -8.25, 2.15, -4.25, 5.25, '#fff3c4', '#f0b93e');
    text(x, 'わかったこと', -6.25, 4.8, 0.36, 1, { align: 'center', weight: 900, col: '#172443' });
    sticky(x, -7.15, 3.25, -0.07, '#ffd1dc', ['夏は', '水温が高い']); sticky(x, -5.35, 3.15, 0.06, '#cfe6ff', ['冬は', '水温が低い']);
    rrect(x, 4.25, 2.15, 8.25, 5.25, '#e1f5ee', '#2fd0a8');
    text(x, '牛久沼の水温', 6.25, 4.8, 0.36, 1, { align: 'center', weight: 900, col: '#172443' });
    line(x, [[4.6, 4.15], [4.6, 2.35], [8.05, 2.35]], 1, '#172443', 5);
    line(x, TEMPS.map((v, i) => [gx(i), gy(v) - 0.12]), 1, '#ef5b6b', 9);
    star(x, -4.05, 5.05, 0.28, '#f0b93e'); star(x, 4.45, 5.1, 0.24, '#ef5b6b'); star(x, 8.05, 2.55, 0.2, '#5b9df0');
  }
  const grid = (x) => { x.fillStyle = '#fbf7ec'; x.fillRect(0, 0, cw, ch); for (let v = 0; v <= W * 4; v++) { const major = v % 8 === 0; x.strokeStyle = major ? '#a9c8e2' : '#d5e3ee'; x.lineWidth = major ? 2.5 : 1.6;
      x.beginPath(); x.moveTo(v * S / 4, 0); x.lineTo(v * S / 4, ch); x.stroke(); if (v <= H * 4) { x.beginPath(); x.moveTo(0, ch - v * S / 4); x.lineTo(cw, ch - v * S / 4); x.stroke(); } } };
  // めくれるページ（上の辺を軸に、手前へめくり上がる）
  const snap = draw => { const c = mkCanvas(), x = c.getContext('2d'); grid(x); draw(x); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
  let texThink, texPoster;
  const flipPivot = new THREE.Group(); flipPivot.position.set(0, 2 + H - 0.75, -5.95); note.add(flipPivot);
  const flipSheet = new THREE.Mesh(new THREE.PlaneGeometry(W, H), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide })); flipSheet.position.y = -H / 2; flipPivot.add(flipSheet);
  // 机の上の鉛筆と消しゴム
  const pencil = new THREE.Group();
  const pm = (geo, col, pos, rot) => { const m = new THREE.Mesh(geo, new THREE.MeshToonMaterial({ color: col })); m.position.set(...pos); if (rot) m.rotation.set(...rot); pencil.add(m); return m; };
  pm(new THREE.CylinderGeometry(0.12, 0.12, 1.6, 6), 0xf2c230, [0, 0, 0], [0, 0, Math.PI / 2]);
  pm(new THREE.ConeGeometry(0.12, 0.34, 6), 0xf0d2a6, [-0.97, 0, 0], [0, 0, Math.PI / 2]);
  pm(new THREE.ConeGeometry(0.045, 0.12, 6), 0x333a48, [-1.1, 0, 0], [0, 0, Math.PI / 2]);
  pm(new THREE.CylinderGeometry(0.125, 0.125, 0.16, 12), 0xc7ccd6, [0.88, 0, 0], [0, 0, Math.PI / 2]);
  pm(new THREE.CylinderGeometry(0.12, 0.12, 0.2, 12), 0xef8fa0, [1.05, 0, 0], [0, 0, Math.PI / 2]);
  pencil.position.set(3.75, 0.13, 1.9); pencil.rotation.y = 0.5; addOutlines(pencil); note.add(pencil);
  const eraser = new THREE.Group();
  const e1 = new THREE.Mesh(new THREE.BoxGeometry(0.75, 0.28, 0.4), new THREE.MeshToonMaterial({ color: 0xffffff })); eraser.add(e1);
  const e2 = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.3, 0.42), new THREE.MeshToonMaterial({ color: 0x3f6fd1 })); e2.position.x = 0.12; eraser.add(e2);
  eraser.position.set(-3.85, 0.14, 1.7); eraser.rotation.y = -0.35; addOutlines(eraser); note.add(eraser);

  let lastKey = '';
  paintNote = (a, t, looped) => {
    const cur = ORDER.indexOf(a), showPoster = cur >= ORDER.indexOf('tell');
    const key = showPoster ? 'poster' : (cur === 0 ? 'blank' : cur + ':' + t.toFixed(3));
    if (key !== lastKey) { lastKey = key; ix.clearRect(0, 0, cw, ch); if (showPoster) poster(ix); else notebook(ix, cur, t); inkTex.needsUpdate = true; }
    let f = 1, tex = null;
    if (a === 'tell') { f = clamp(t / 0.9); tex = texThink || (texThink = snap(x => notebook(x, ORDER.indexOf('think'), 99))); }
    if (a === 'intro' && looped) { f = clamp(t / 0.9); tex = texPoster || (texPoster = snap(poster)); }
    flipSheet.visible = f < 1 && !!tex;
    if (tex && flipSheet.material.map !== tex) { flipSheet.material.map = tex; flipSheet.material.needsUpdate = true; }
    flipPivot.rotation.x = -(f * f * (3 - 2 * f)) * Math.PI * 0.85;
  };
}

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
  if (BG === 'note') paintNote(a, t, looped);
  else { const tp = timeOfDay(a, t); paintSky(tp, clock, dt); if (BG === 'season') paintSeason(tp, clock, dt, a); }
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
  bP.classList.toggle('one', a === 'tell');   // 「伝えよう！」は1行で（スマホでは折り返す）
  place(bP, -1.3, 2.75 + jP);
  if (s.philo && s.numa) { bP.style.left = Math.min(parseFloat(bP.style.left), stage.clientWidth / 2 - bP.offsetWidth / 2 - 6) + 'px'; }
  const side = !s.philo; bN.classList.toggle('side', side);
  if (side) placeLeftOf(bN, 0.75, 2.75 + jN); else { place(bN, 1.3, 3.0 + jN); if (s.philo) bN.style.left = Math.max(parseFloat(bN.style.left), stage.clientWidth / 2 + bN.offsetWidth / 2 + 6) + 'px'; }
  bar.style.width = ((SCENES.slice(0, idx).reduce((x, c) => x + c.dur, 0) + t) / TOTAL * 100) + '%';
}

function next() {
  idx = (idx + 1) % SCENES.length; t = 0;
  if (idx === 0) looped = true;
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
$('cAgain').addEventListener('click', () => { looped = BG === 'note' ? idx >= ORDER.indexOf('tell') : tod > 2.5; idx = 0; t = 0; confetti.forEach(m => m.visible = false); if (!playing) btnPlay.click(); });
new IntersectionObserver(es => { visible = es[0].isIntersecting; last = performance.now(); }).observe(stage);

// 確認用：?scene=data などで、その場面から始める（&pause を付けると t 秒で止める）
const qs = new URLSearchParams(location.search), qScene = SCENES.findIndex(s => s.act === qs.get('scene'));
if (qScene >= 0) { idx = qScene; t = +(qs.get('t') || 0); clock = t; if (SCENES[idx].act === 'tell') resetConfetti(); if (qs.has('pause')) btnPlay.click(); }
if (reduce) {   // 動きを減らす設定：最後の場面で止め、セリフは文字で見せる
  idx = SCENES.findIndex(s => s.act === 'tell'); t = 3; btnPlay.textContent = '▶'; btnPlay.setAttribute('aria-label', '再生');
  document.querySelector('.script').open = true;
}
requestAnimationFrame(frame);
