// 東洋大牛久SSHキャラクター（フィロ・ぬまっぱ博士）の3Dモデル。
// 元ファイル: 非公開リポジトリ ssh-characters の chara.js（そちらを直して tools/sync_to_site.py で作り直す）
export function createChara(THREE) {
// ---------- 共通の部品 ----------
const OUTLINE = new THREE.MeshBasicMaterial({color:0x172443, side:THREE.BackSide});
const grad = (()=>{const d=new Uint8Array([90,90,90,255, 175,175,175,255, 255,255,255,255]);
  const t=new THREE.DataTexture(d,3,1,THREE.RGBAFormat);t.minFilter=t.magFilter=THREE.NearestFilter;t.generateMipmaps=false;t.needsUpdate=true;return t;})();
const M = (c,o={}) => new THREE.MeshToonMaterial(Object.assign({color:c, gradientMap:grad}, o));
const GLOW = (c,op=1) => new THREE.MeshBasicMaterial({color:c, transparent:op<1, opacity:op});

function mesh(geo, mat, p=[0,0,0], s=[1,1,1], r=[0,0,0], noOutline=false){
  const m=new THREE.Mesh(geo,mat); m.position.set(...p); m.scale.set(...s); m.rotation.set(...r);
  m.userData.noOutline = noOutline || mat.type==='MeshBasicMaterial'; return m;
}
const S = (r,seg=32)=>new THREE.SphereGeometry(r,seg,Math.round(seg*0.75));
function eye(g, x,y,z, s, iris=0x172443){
  g.add(mesh(S(s),M(0xffffff),[x,y,z],[1,1.15,0.55]));
  g.add(mesh(S(s*0.62),M(iris),[x,y-s*0.08,z+s*0.32],[1,1.15,0.5],[0,0,0],true));
  g.add(mesh(S(s*0.2),GLOW(0xffffff),[x+s*0.2,y+s*0.22,z+s*0.58]));
}
function cheeks(g, y,z, x){
  [-1,1].forEach(k=>g.add(mesh(S(0.09),GLOW(0xef5b6b,0.55),[k*x,y,z],[1.3,0.7,0.3],[0,k*0.5,0])));
}
function addOutlines(root){
  const list=[]; root.traverse(o=>{ if(o.isMesh && !o.userData.noOutline && !o.userData.isOutline) list.push(o); });
  list.forEach(o=>{ const ol=new THREE.Mesh(o.geometry,OUTLINE); ol.scale.setScalar(1.045); ol.userData.isOutline=true; o.add(ol); });
}

// 立体の「TU」（丸い線で組む）。h = 文字の高さ
function TU(mat, h, noOutline=true){
  const g=new THREE.Group(), r=h*0.12;
  const C=len=>new THREE.CylinderGeometry(r,r,len,16), B=()=>S(r,16);
  const add=(geo,p,rot=[0,0,0])=>g.add(mesh(geo,mat,p,[1,1,1],rot,noOutline));
  const tx=-0.42*h, tw=0.78*h;
  add(C(tw-2*r),[tx,h/2-r,0],[0,0,Math.PI/2]); add(B(),[tx-tw/2+r,h/2-r,0]); add(B(),[tx+tw/2-r,h/2-r,0]);
  add(C(h-2*r),[tx,0,0]); add(B(),[tx,-h/2+r,0]);
  const ux=0.44*h, R=0.34*h-r, L=h-2*r-R;
  [-1,1].forEach(k=>{ add(C(L),[ux+k*R,h/2-r-L/2,0]); add(B(),[ux+k*R,h/2-r,0]); });
  add(new THREE.TorusGeometry(R,r,12,24,Math.PI),[ux,-h/2+r+R,0],[0,0,Math.PI]);
  return g;
}
// 文字を描いたテクスチャ
function textTex(draw, w=512, h=340){
  const c=document.createElement('canvas'); c.width=w; c.height=h; const x=c.getContext('2d');
  draw(x,w,h); const t=new THREE.CanvasTexture(c); t.anisotropy=4; if(THREE.SRGBColorSpace) t.colorSpace=THREE.SRGBColorSpace; return t;
}
const FONT='"Avenir Next","Helvetica Neue",Arial,sans-serif';

// ---------- キャラ ----------
const BUILD = {
  sophy(opt){
    const g=new THREE.Group();
    const navy=M(0x2f4a8a), navyD=M(0x223867), ruff=M(0x4a68b0), cream=M(0xf6efdc), gold=M(0xf0b93e), orange=M(0xf0a03e), orangeD=M(0xd9822b);
    // 体の表面上の点（背中の模様・おなかの模様用）
    const onBody=(x,y,back)=>{ const t=1-(x/0.88)**2-((y-1.05)/0.986)**2; return (back?-1:1)*0.836*Math.sqrt(Math.max(0,t))+(back?-0.01:0.01); };
    const onBelly=(x,y)=>0.46+0.319*Math.sqrt(Math.max(0,1-(x/0.58)**2-((y-0.72)/0.58)**2))+0.008;

    // --- 体・おなか ---
    g.add(mesh(S(0.88),navy,[0,1.02,0],[1.04,1.06,0.95]));
    g.add(mesh(S(0.58),cream,[0,0.72,0.46],[1,1,0.55]));
    [[-0.2,0.84],[0,0.8],[0.2,0.84],[-0.3,0.58],[-0.1,0.55],[0.1,0.55],[0.3,0.58],[-0.18,0.34],[0.02,0.31],[0.2,0.34]].forEach(([x,y])=>
      g.add(mesh(new THREE.TorusGeometry(0.06,0.014,6,14,Math.PI),GLOW(0xb9c3db),[x,y,onBelly(x,y)],[1,1,1],[-0.3*(y-0.6),x*0.9,Math.PI])));

    // --- 顔：ハート形の顔盤（紺の縁どり＋クリーム） ---
    [-1,1].forEach(k=>{
      g.add(mesh(S(0.45),ruff,[k*0.3,1.42,0.5],[1,1.05,0.45]));
      g.add(mesh(S(0.4),cream,[k*0.3,1.42,0.58],[1,1.02,0.45]));
    });
    // 目：琥珀色のひとみ・ハイライト2つ
    [-1,1].forEach(k=>{
      const x=k*0.3, y=1.42, z=0.72;
      g.add(mesh(S(0.23),M(0xffffff),[x,y,z],[1,1.1,0.5]));
      g.add(mesh(S(0.18),M(0xc97a2a),[x-k*0.015,y-0.03,z+0.05],[1,1.12,0.5],[0,0,0],true));
      g.add(mesh(S(0.145),M(0x1b1b2e),[x-k*0.015,y-0.035,z+0.09],[1,1.12,0.45],[0,0,0],true));
      g.add(mesh(S(0.065),GLOW(0xffffff),[x+0.05,y+0.06,z+0.14]));
      g.add(mesh(S(0.03),GLOW(0xffffff),[x-0.06,y-0.09,z+0.14]));
    });
    // 丸メガネ（つる付き）
    [-1,1].forEach(k=>{
      g.add(mesh(new THREE.TorusGeometry(0.27,0.03,10,36),gold,[k*0.3,1.42,0.84]));
      g.add(mesh(new THREE.CylinderGeometry(0.02,0.02,0.5,8),gold,[k*0.66,1.47,0.56],[1,1,1],[Math.PI/2,0,k*0.15]));
    });
    g.add(mesh(new THREE.TorusGeometry(0.06,0.02,8,16,Math.PI),gold,[0,1.45,0.86]));
    // くちばし（小さく丸い）とほっぺ
    g.add(mesh(S(0.085),orange,[0,1.2,0.88],[1,0.9,0.8]));
    g.add(mesh(S(0.05),orangeD,[0,1.14,0.86],[1,0.7,0.7]));
    cheeks(g,1.18,0.8,0.42);
    // 耳羽：丸く短いふさ
    [-1,1].forEach(k=>{
      g.add(mesh(S(0.15),navy,[k*0.45,1.98,0.05],[0.85,1.35,0.6],[0,0,-k*0.45]));
      g.add(mesh(S(0.09),navyD,[k*0.6,2.0,0.08],[0.8,1.2,0.6],[0,0,-k*0.8]));
      g.add(mesh(S(0.05,12),GLOW(0xf0b93e),[k*0.55,2.16,0.08]));   // 先の金の羽
    });

    // --- 翼（3枚の風切り羽つき）---
    const wing=(pos,rz,ry)=>{
      const w=new THREE.Group();
      w.add(mesh(S(1),navyD,[0,-0.28,0],[0.14,0.36,0.25]));
      w.add(mesh(S(1),M(0x3d5ba3),[0.02,-0.22,0.12],[0.08,0.22,0.12]));
      [-1,0,1].forEach(i=>w.add(mesh(S(1),M(0x1a2b55),[i*0.065,-0.6+Math.abs(i)*0.04,0.02],[0.06,0.15,0.09],[0,0,i*0.25])));
      w.position.set(...pos); w.rotation.set(0,ry||0,rz); g.add(w); return w;
    };

    // --- 足（3本指）・しっぽ ---
    [-1,1].forEach(k=>[-1,0,1].forEach(t=>g.add(mesh(S(0.07,12),orange,[k*0.3+t*0.085,0.05,0.34-Math.abs(t)*0.04],[0.9,0.55,1.5],[0,t*0.3,0]))));
    [-1,0,1].forEach(i=>g.add(mesh(S(1),navyD,[i*0.13,0.32,-0.78],[0.1,0.07,0.17],[0.6,i*0.35,0])));

    // --- 背中：金の星座もよう（ぬまっぱ博士の回路と対になる） ---
    const stars=[[-0.3,1.35],[0,1.5],[0.28,1.3],[0.1,1.0],[-0.22,0.85],[0.32,0.75]];
    stars.forEach(([x,y],i)=>g.add(mesh(S(i===1?0.05:0.035,12),GLOW(0xf0b93e),[x,y,onBody(x,y,true)])));
    [[0,1],[1,2],[1,3],[3,4],[3,5]].forEach(([a,b])=>{
      const [x1,y1]=stars[a],[x2,y2]=stars[b], len=Math.hypot(x2-x1,y2-y1), mx=(x1+x2)/2, my=(y1+y2)/2;
      g.add(mesh(new THREE.BoxGeometry(len,0.014,0.01),GLOW(0xf0b93e,0.7),[mx,my,onBody(mx,my,true)],[1,1,1],[0,0,Math.atan2(y2-y1,x2-x1)]));
    });

    if(opt==='tu'){
      wing([-0.8,1.2,0.12],-0.22);                 // 左の翼はおろす
      wing([0.78,1.28,0.2],Math.PI-0.4,-0.3).userData.role='wingR';      // 右の翼をあげて「はい！なぜ？」
      // 胸の金メダル（バッジ）
      const medal=new THREE.Group();
      medal.add(mesh(new THREE.CylinderGeometry(0.22,0.22,0.06,40),gold,[0,0,0],[1,1,1],[Math.PI/2,0,0]));
      medal.add(mesh(new THREE.TorusGeometry(0.2,0.022,8,40),M(0xc9921b),[0,0,0.035],[1,1,1],[0,0,0],true));
      const t=TU(M(0x172443),0.2); t.position.z=0.05; medal.add(t);
      medal.position.set(0,0.86,0.86); medal.rotation.x=-0.08; g.add(medal);
    } else {
      wing([-0.62,1.05,0.42],-0.9,0.5); wing([0.62,1.05,0.42],0.9,-0.5);
      const book=new THREE.Group();
      book.add(mesh(new THREE.BoxGeometry(0.98,0.68,0.1),M(0xb8324a),[0,0,0]));
      book.add(mesh(new THREE.BoxGeometry(0.92,0.62,0.1),M(0xffffff),[0,0,-0.04]));
      const tex=textTex((x,w,h)=>{
        x.fillStyle='#b8324a'; x.fillRect(0,0,w,h);
        x.strokeStyle='#f0b93e'; x.lineWidth=6; x.strokeRect(18,18,w-36,h-36);
        x.fillStyle='#f6d27a'; x.textAlign='center'; x.textBaseline='middle';
        x.font=`800 112px ${FONT}`; x.fillText('TOYO',w/2,h*0.36);
        x.font=`800 96px ${FONT}`;  x.fillText('USHIKU',w/2,h*0.68);
      });
      book.add(mesh(new THREE.PlaneGeometry(0.96,0.66),new THREE.MeshBasicMaterial({map:tex}),[0,0,0.051]));
      book.position.set(0,0.72,0.98); book.rotation.x=-0.12; g.add(book);
    }
    // 考えの粒
    const orbit=new THREE.Group();
    [0xf0b93e,0x2fd0a8,0xef5b6b].forEach((c,i)=>{const a=i*Math.PI*2/3; orbit.add(mesh(S(0.08),GLOW(c),[Math.cos(a)*1.05,0,Math.sin(a)*1.05]));});
    orbit.position.y=2.45; orbit.userData.spin=true; orbit.userData.role='orbit'; g.add(orbit);
    return g;
  },
  numappa(opt){
    const g=new THREE.Group(), V=(x,y,z)=>new THREE.Vector3(x,y,z), UP=V(0,1,0);
    const green=M(0x3cc39a), greenD=M(0x2a9f7c), hairM=M(0x1f7d62), belly=M(0xe9f7c8),
          white=M(0xffffff, {side:THREE.DoubleSide}), teal=M(0x2fb894), bill=M(0xf6c045), billD=M(0xe39a32);
    const seg=(geoFn,a,b,mat,noOl)=>{ const d=b.clone().sub(a), m=mesh(geoFn(d.length()),mat,[0,0,0],[1,1,1],[0,0,0],noOl);
      m.position.copy(a.clone().add(b).multiplyScalar(0.5)); m.quaternion.setFromUnitVectors(UP,d.normalize()); return m; };
    const point=(geo,mat,p,dir,noOl)=>{ const m=mesh(geo,mat,[0,0,0],[1,1,1],[0,0,0],noOl); m.position.copy(p); m.quaternion.setFromUnitVectors(UP,dir.clone().normalize()); return m; };

    // --- 体・おなか・脚 ---
    g.add(mesh(S(0.5),green,[0,0.62,0],[1,1.05,0.95]));
    g.add(mesh(S(0.38),belly,[0,0.58,0.22],[0.95,1.05,0.75]));
    [-1,1].forEach(k=>{
      g.add(mesh(new THREE.CylinderGeometry(0.11,0.12,0.2,16),green,[k*0.24,0.16,0.04]));
      g.add(mesh(S(0.16),greenD,[k*0.26,0.06,0.14],[1.25,0.42,1.6]));          // 水かきのある足
      [-1,0,1].forEach(t=>g.add(mesh(S(0.05,12),greenD,[k*0.26+t*0.09,0.05,0.36-Math.abs(t)*0.04],[1,0.7,1.2])));
    });

    // --- データ甲羅（紺のドーム＋クリームの縁＋回路） ---
    g.add(mesh(S(0.52),M(0x223867),[0,0.72,-0.34],[1,1.12,0.62]));
    g.add(mesh(new THREE.TorusGeometry(0.5,0.055,10,48),M(0xf6efdc),[0,0.72,-0.3],[1,1.12,1]));
    const backZ=(x,y)=>-0.34-0.322*Math.sqrt(Math.max(0,1-(x/0.52)**2-((y-0.72)/0.58)**2))-0.01;
    [[0,0.95],[-0.22,0.75],[0.22,0.75],[0,0.5],[-0.18,0.45],[0.2,1.0]].forEach(([x,y])=>
      g.add(mesh(S(0.035,12),GLOW(0x2fd0a8),[x,y,backZ(x,y)])));
    [[0,0.95,0,0.5],[-0.22,0.75,0.22,0.75],[-0.18,0.45,0,0.5],[0,0.95,0.2,1.0]].forEach(([x1,y1,x2,y2])=>{
      const len=Math.hypot(x2-x1,y2-y1), mx=(x1+x2)/2, my=(y1+y2)/2;
      g.add(mesh(new THREE.BoxGeometry(len,0.018,0.01),GLOW(0x2fd0a8,0.8),[mx,my,backZ(mx,my)],[1,1,1],[0,0,Math.atan2(y2-y1,x2-x1)]));
    });

    // --- 前の開いた白衣（裾が広がる） ---
    const prof=[[0.33,1.03],[0.4,0.97],[0.49,0.75],[0.58,0.48],[0.7,0.2],[0.72,0.17]].map(([r,y])=>new THREE.Vector2(r,y));
    const gap=0.95;
    g.add(mesh(new THREE.LatheGeometry(prof,40,gap/2,Math.PI*2-gap),white,[0,0,0],[1,1,0.95],[0,0,0],true));
    g.add(mesh(new THREE.TorusGeometry(0.71,0.02,6,60,Math.PI*2-gap),M(0x1f7d62),[0,0.175,0],[1,0.95,1],[Math.PI/2,0,-Math.PI/2+gap/2+Math.PI],true));
    [-1,1].forEach(k=>{  // 襟
      const a=k*(gap/2+0.12);
      g.add(mesh(new THREE.BoxGeometry(0.16,0.3,0.025),teal,[Math.sin(a)*0.42,0.88,Math.cos(a)*0.42*0.95],[1,1,1],[-0.35,a,k*0.35]));
    });
    // 左胸のTU名札
    const pa=-0.8, tagP=[Math.sin(pa)*0.5,0.8,Math.cos(pa)*0.5*0.95], tagR=[-0.28,pa,0];
    g.add(mesh(new THREE.BoxGeometry(0.22,0.15,0.025),M(0x1fa583),tagP,[1,1,1],tagR));
    const tag=TU(GLOW(0xffffff),0.085); tag.position.set(...tagP); tag.rotation.set(...tagR); tag.translateZ(0.016); g.add(tag);

    // --- 腕（白衣の袖・カフス・3本指の手） ---
    const arm=(sh,hand)=>{
      g.add(seg(l=>new THREE.CylinderGeometry(0.1,0.13,l,16),sh,hand,white,true));
      const dir=hand.clone().sub(sh).normalize();
      g.add(point(new THREE.TorusGeometry(0.105,0.03,8,20),teal,hand.clone().sub(dir.clone().multiplyScalar(0.05)),dir,true)).children;
      const h=mesh(S(0.12),green,[0,0,0]); h.position.copy(hand.clone().add(dir.clone().multiplyScalar(0.06))); g.add(h);
      [-1,0,1].forEach(t=>{ const side=V(-dir.y,dir.x,0).normalize();
        const p=h.position.clone().add(dir.clone().multiplyScalar(0.1)).add(side.multiplyScalar(t*0.065));
        g.add(mesh(S(0.045,12),green,p.toArray())); });
    };

    // --- 頭 ---
    g.add(mesh(S(0.72),green,[0,1.62,0],[1.08,0.96,1]));
    // 目：大きなひとみ・ハイライト2つ・まゆ
    [-1,1].forEach(k=>{
      const x=k*0.27, y=1.67, z=0.6;
      g.add(mesh(S(0.19),M(0xffffff),[x,y,z],[0.95,1.2,0.5]));
      g.add(mesh(S(0.14),M(0x16304f),[x+k*0.01,y-0.02,z+0.06],[0.95,1.2,0.5],[0,0,0],true));
      g.add(mesh(S(0.075),M(0x2a7fa8),[x+k*0.01,y-0.06,z+0.115],[1,0.8,0.4],[0,0,0],true));
      g.add(mesh(S(0.045),GLOW(0xffffff),[x+0.05,y+0.07,z+0.14]));
      g.add(mesh(S(0.022),GLOW(0xffffff),[x-0.04,y-0.08,z+0.14]));
      g.add(mesh(new THREE.TorusGeometry(0.1,0.018,6,16,Math.PI*0.7),GLOW(0x1f5f4a),[x,y+0.27,z-0.02],[1,1,1],[0,k*0.2,Math.PI*0.15+(k>0?0:0)]));
    });
    cheeks(g,1.5,0.62,0.5);
    // くちばし（上下2枚＋鼻の穴）
    g.add(mesh(S(0.25),bill,[0,1.44,0.66],[1.3,0.4,0.92]));
    g.add(mesh(S(0.2),billD,[0,1.37,0.62],[1.08,0.34,0.8]));
    g.add(mesh(new THREE.TorusGeometry(0.2,0.012,6,24,Math.PI*0.7),GLOW(0x9a5a1e),[0,1.47,0.62],[1.3,0.6,1],[Math.PI/2+0.25,0,Math.PI*0.65]));
    [-1,1].forEach(k=>g.add(mesh(S(0.022,10),GLOW(0x9a5a1e),[k*0.08,1.5,0.86])));
    // 額に上げたゴーグル
    [-1,1].forEach(k=>{
      g.add(mesh(new THREE.TorusGeometry(0.15,0.045,10,28),M(0xef8a3c),[k*0.21,2.02,0.6],[1,1,1],[-0.6,k*0.3,0]));
      g.add(mesh(new THREE.CircleGeometry(0.14,24),GLOW(0x9cc2f5,0.7),[k*0.21,2.02,0.605],[1,1,1],[-0.6,k*0.3,0]));
    });
    g.add(mesh(new THREE.TorusGeometry(0.66,0.035,8,48),M(0xef8a3c),[0,2.0,0],[1.0,0.92,1],[Math.PI/2,0,0]));
    // 髪：葉っぱのようなとげを輪にする
    g.add(mesh(new THREE.TorusGeometry(0.4,0.08,10,40),hairM,[0,2.24,0],[1,1,1],[Math.PI/2,0,0]));
    for(let i=0;i<11;i++){
      const a=i/11*Math.PI*2+0.15, front=Math.cos(a)>0.6;
      const p=V(Math.sin(a)*0.44,2.24,Math.cos(a)*0.44);
      g.add(point(new THREE.ConeGeometry(0.12,front?0.24:0.4,10),i%2?hairM:M(0x2a9f7c),p,V(Math.sin(a)*0.95,front?0.15:0.3,Math.cos(a)*0.95)));
    }
    // お皿：紺の縁に光るセンサーレンズ
    g.add(mesh(new THREE.CylinderGeometry(0.36,0.36,0.07,40),M(0x172443),[0,2.3,0]));
    g.add(mesh(new THREE.CylinderGeometry(0.27,0.27,0.02,40),GLOW(0x2fd0a8),[0,2.34,0]));
    g.add(mesh(new THREE.TorusGeometry(0.32,0.012,6,40),GLOW(0xf0b93e),[0,2.34,0],[1,1,1],[Math.PI/2,0,0]));

    const holo=new THREE.Group();
    holo.add(mesh(new THREE.TorusGeometry(0.38,0.015,6,48),GLOW(0x5b9df0,0.8),[0,0.02,0],[1,1,1],[Math.PI/2,0,0]));
    if(opt==='tu'){
      arm(V(-0.38,0.92,0.05),V(-0.66,0.6,0.22));
      arm(V(0.38,0.92,0.05),V(0.66,0.6,0.22));
      const t=TU(GLOW(0x2fd0a8,0.9),0.44); t.position.set(0,2.74,0); t.userData.float=2.74; g.add(t);
      [0.12,0.2,0.28].forEach((y,i)=>holo.add(mesh(new THREE.TorusGeometry(0.3-i*0.06,0.01,6,40),GLOW(0x2fd0a8,0.5),[0,y,0],[1,1,1],[Math.PI/2,0,0])));
    } else {
      [0.22,0.38,0.3,0.52].forEach((h,i)=>{ const b=mesh(new THREE.BoxGeometry(0.1,h,0.1),GLOW(0x2fd0a8,0.75),[-0.24+i*0.16,h/2,0]); b.userData.role='bar'; b.userData.h=h; holo.add(b); });
      arm(V(-0.38,0.92,0.05),V(-0.72,1.12,0.2));   // 手をあげてあいさつ
      arm(V(0.38,0.9,0.08),V(0.74,0.66,0.6));      // タブレットを持つ手
      const tex=textTex((x,w,h)=>{
        x.fillStyle='#0d1a30'; x.fillRect(0,0,w,h);
        x.strokeStyle='rgba(91,157,240,.25)'; x.lineWidth=2;
        for(let i=1;i<6;i++){ x.beginPath(); x.moveTo(0,i*h/6); x.lineTo(w,i*h/6); x.stroke(); }
        x.strokeStyle='#ef5b6b'; x.lineWidth=6; x.beginPath();
        [[30,300],[120,270],[210,285],[300,230],[390,240],[480,190]].forEach(([a,b],i)=>i?x.lineTo(a,b):x.moveTo(a,b)); x.stroke();
        x.textAlign='center'; x.textBaseline='middle';
        x.fillStyle='#ffffff'; x.font=`800 104px ${FONT}`; x.fillText('TOYO',w/2,h*0.27);
        x.fillStyle='#f0b93e'; x.font=`800 90px ${FONT}`;  x.fillText('USHIKU',w/2,h*0.56);
      });
      const tab=new THREE.Group();
      tab.add(mesh(new THREE.BoxGeometry(0.92,0.62,0.06),M(0x172443),[0,0,0]));
      tab.add(mesh(new THREE.PlaneGeometry(0.85,0.55),new THREE.MeshBasicMaterial({map:tex}),[0,0,0.032]));
      tab.position.set(0.32,0.66,0.86); tab.rotation.set(-0.12,-0.2,0.06); tab.userData.role='tablet'; g.add(tab);
    }
    holo.position.set(0,2.38,0); holo.userData.spin=true; holo.userData.role='holo'; g.add(holo);
    return g;
  },
};

BUILD.duo = ()=>{
  const g=new THREE.Group();
  const a=BUILD.sophy('tu'); a.position.x=-1.15; a.rotation.y=0.3; g.add(a);
  const b=BUILD.numappa('name'); b.position.x=1.15; b.rotation.y=-0.3; g.add(b);
  return g;
};

return { BUILD, addOutlines, TU };
}
