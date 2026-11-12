#!/usr/bin/env python3
"""下層ページ・サイト設定・sitemap を生成する。
使い方: python3 tools/sync_gsites.py （Googleサイトを取り込む） → python3 tools/build.py
- 本文の正本は Googleサイト（content/gsites.json）。
- 記事ごとの日付・分類・写真は content/articles.json。
- ページを「サイト内表示 / Googleサイトへ直接リンク」に切り替えるのは content/site.json。
"""
import json, re, html, random, datetime, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
G = json.loads((ROOT / 'content/gsites.json').read_text(encoding='utf-8'))
SITE = json.loads((ROOT / 'content/site.json').read_text(encoding='utf-8'))
CFG = json.loads((ROOT / 'content/articles.json').read_text(encoding='utf-8'))
BASE_URL, GS = SITE['base_url'], SITE['gsites_base']
DRIVE = 'https://drive.google.com/file/d/%s/view'
esc = html.escape
NOTES = []   # 生成時にお知らせする事項

# slug, 表示名, 英字, リード文, 色, Googleサイト上のページ名
PAGES = [
 ('inquiry', '東洋大牛久の目指す探究教育', 'INQUIRY EDUCATION', '「哲学という羅針盤」と「科学という武器」を、同時に手にする。', '#3f6fd1', '東洋大牛久の目指す探究教育'),
 ('frontier', 'FRONTIER BOOST PROGRAM', 'FRONTIER BOOST', 'SSH 高大・産学連携の取組。大学・企業・研究所とつながり、教室の外で学ぶ。', '#2fd0a8', 'frontier-boost-program'),
 ('achievements', 'SSH成果物', 'ACHIEVEMENTS', '生徒の研究は、校外でどう評価されたか。数字で振り返ります。', '#f0b93e', 'ssh成果物'),
 ('activities', '探究活動の様々な取り組み', 'INQUIRY ACTIVITIES', '課題研究・Lab活動・各種コンテスト。日々の探究の記録です。', '#ef5b6b', '探究活動の様々な取り組み'),
 ('outreach', 'SSH普及・発信活動', 'OUTREACH', '全国の高校へ、県内の高校へ、地域へ。成果を外に届ける取り組み。', '#5b9df0', 'ssh普及発信活動'),
 ('reports', '研究開発実施報告書', 'RESEARCH REPORTS', '文部科学省へ提出する年次報告書と、研究発表の資料。', '#3f6fd1', '研究開発実施報告書'),
 ('committee', '運営指導委員会', 'STEERING COMMITTEE', '大学の専門家から、指導と助言を受けています。', '#2fd0a8', '運営指導委員会'),
 ('visits', 'SSH先進校視察・受け入れ', 'SCHOOL VISITS', '他校に学び、本校の取り組みを見ていただく。', '#f0b93e', 'ssh先進校視察及び視察の受け入れ'),
 ('logos', 'SSH通信「LOGOS Ushiku」', 'NEWSLETTER', '哲学 × データサイエンスで未来を読み解く SSH News。', '#ef5b6b', 'ssh通信logos-ushiku'),
]
AUD = dict(inquiry='junior edu', activities='junior student', frontier='junior student', logos='junior student', achievements='junior student edu',
           outreach='edu', reports='edu', committee='edu', visits='edu')
ORDER = ['inquiry', 'activities', 'frontier', 'logos', 'achievements', 'outreach', 'reports', 'committee', 'visits']   # トップの一覧での並び
gs_url = lambda name: GS + urllib.parse.quote(name)
is_local = lambda slug: SITE['pages'].get(slug, 'local') == 'local'
def href(slug, frag=''):
    p = next(p for p in PAGES if p[0] == slug)
    return f'{slug}.html{frag}' if is_local(slug) else gs_url(p[5])
def ext(slug): return '' if is_local(slug) else ' target="_blank" rel="noopener"'

# ---------------- Googleサイトの本文を読む ----------------
def flat(page):
    out = []
    for s in G[page]: out += s['lines'] + ['<<SEC>>']
    return out
def heads(page): return [h for s in G[page] for h in s['heads']]
def after(page, start, n=None):
    """start で始まる行の次から、区画の終わりまで（n 行まで）"""
    L = flat(page)
    for i, l in enumerate(L):
        if l.startswith(start):
            out = []
            for m in L[i + 1:]:
                if m == '<<SEC>>': break
                out.append(m)
            return out[:n] if n else out
    raise SystemExit(f'Googleサイト「{page}」に「{start}」で始まる行が見つかりません。Googleサイト側の文言が変わった可能性があります。')
def line(page, start):
    for l in flat(page):
        if l.startswith(start): return l
    raise SystemExit(f'Googleサイト「{page}」に「{start}」で始まる行が見つかりません。')
def frames(page): return [f for s in G[page] for f in s['frames']]

# ---------------- 記事 ----------------
CATS = {'award': '発表・受賞', 'lecture': '講座・講演', 'field': 'フィールドワーク', 'global': '国際交流', 'lab': 'Lab研究', 'media': 'メディア', 'visit': '視察・委員会', 'other': 'その他'}
ACT_PAGE = '探究活動の様々な取り組み'
ACT, ACT_HEADS = flat(ACT_PAGE), heads(ACT_PAGE)
KNOWN = [a['head'] for a in CFG['articles']]
def is_head(l, pat): return l.startswith(pat[:-1]) if pat.endswith('*') else l == pat
def body_of(start_index):
    out = []
    for m in ACT[start_index + 1:]:
        if m in CFG['ignore_heads']: continue
        if m == '<<SEC>>' or m in ACT_HEADS or any(is_head(m, h) for h in KNOWN) or m.startswith('指定以前'): break
        if re.fullmatch(r'\d{4}年\d+月\d+日', m) or re.match(r'\d{4}\.\d+\.\d+ ', m) or m == '掲載されました。' or m.startswith('― '): continue
        out.append(m.replace('Yhoo!', 'Yahoo!'))
    return out
ARTS, used = [], set()
for a in CFG['articles']:
    idx = next((i for i, l in enumerate(ACT) if is_head(l, a['head'])), None)
    if idx is None:
        NOTES.append(f'記事「{a["title"]}」の見出しが Googleサイトに見つからないため、載せていません（見出しが変わった可能性）。'); continue
    used.add(ACT[idx]); b = body_of(idx)
    if b: ARTS.append({**a, 'body': b})
for h in ACT_HEADS:                      # 設定のない新しい記事は「その他・日付なし」で末尾に
    if h in used or h in CFG['ignore_heads'] or any(is_head(h, k) for k in KNOWN): continue
    b = body_of(ACT.index(h))
    if not b: continue
    ARTS.append(dict(id='new-' + re.sub(r'\W+', '', h)[:12], title=h, date='', key='00000000', cat='other', img='', body=b))
    NOTES.append(f'新しい記事「{h}」を見つけました。日付・分類が未設定です（content/articles.json に1行足すと整います）。')
ARTS += [dict(e) for e in CFG['extra']]
ARTS.sort(key=lambda a: a['key'], reverse=True)
AR = {a['id']: a for a in ARTS}
for a in ARTS:
    if a['img'] and not (ROOT / 'assets/news' / a['img']).exists(): NOTES.append(f'写真が見つかりません: assets/news/{a["img"]}（{a["title"]}）'); a['img'] = ''

def linkify(t): return re.sub(r'(https?://[^\s<）)]+)', r'<a href="\1" target="_blank" rel="noopener">\1</a>', t)
def paras(ps): return ''.join(f'<p>{linkify(esc(p))}</p>' for p in ps)
def sec(en, jp, inner, cls='cream'): return f'<section class="sec {cls}"><div class="in"><p class="eyebrow rv">{en}</p><h2 class="rv">{jp}</h2>{inner}</div></section>'
def fig(img, alt, cls=''): return f'<figure class="rv {cls}"><img src="assets/news/{img}" alt="{esc(alt)}" loading="lazy"></figure>'
def card(a, full=True):
    im = f'<img src="assets/news/{a["img"]}" alt="" loading="lazy">' if a['img'] else f'<div class="noimg c-{a["cat"]}"><span>{CATS[a["cat"]]}</span></div>'
    summ = esc(a['body'][0][:96]) + ('…' if len(a['body'][0]) > 96 or len(a['body']) > 1 else '')
    more = f'<details><summary>全文を読む</summary>{paras(a["body"])}</details>' if full else f'<a class="more" href="{href("activities", "#" + a["id"])}"{ext("activities")}>くわしく →</a>'
    return f'<article class="card rv" id="{a["id"]}" data-cat="{a["cat"]}">{im}<div class="cb"><p class="meta"><time>{a["date"]}</time><span class="tag c-{a["cat"]}">{CATS[a["cat"]]}</span></p><h3>{esc(a["title"])}</h3><p class="summ">{summ}</p>{more}</div></article>'
def cards(ids, full=False): return '<div class="cards">' + ''.join(card(AR[i], full) for i in ids if i in AR) + '</div>'
def pdf(title, fid, note=''): return f'<a class="pdf rv" href="{DRIVE % fid}" target="_blank" rel="noopener"><b>PDF</b><span>{esc(title)}<small>{esc(note)}</small></span><i>↗</i></a>'
def nums(items): return '<div class="nums">' + ''.join(f'<div class="num rv"><b>{n}<small>{u}</small></b><span>{esc(l)}</span></div>' for n, u, l in items) + '</div>'

# ---------------- 各ページ ----------------
def p_inquiry():
    pg = '東洋大牛久の目指す探究教育'; t = line(pg, '東洋大学附属牛久が目指す')
    if 'まず、' in t and '「哲学という羅針盤」' in t:
        a, rest = t.split('まず、', 1); b, c = rest.split('「哲学という羅針盤」', 1); ps = [a, 'まず、' + b, '「哲学という羅針盤」' + c]
    else: ps = [t]
    h = sec('VISION', '科学と哲学の対話から、新しい価値を。', f'<div class="two"><div class="rv prose">{paras(ps)}</div><div class="stack">{fig("inq-00.jpg", "実験に取り組む生徒")}{fig("inq-01.jpg", "CAD実習に取り組む生徒")}</div></div>')
    h += sec('THREE PILLARS', '3つの柱', '<div class="pillars">'
        '<div class="pillar rv" style="--c:#3f6fd1"><b>01</b><h3>哲学シンキング</h3><p>全教科で展開。「なぜそうなのか」「真に価値があるものは何か」という、本質的な問いを立てる力を磨きます。</p></div>'
        '<div class="pillar rv" style="--c:#ef5b6b"><b>02</b><h3>データサイエンス</h3><p>AIやICTを活用し、主観的な問いを客観的なエビデンスで実証するプロセスを確立します。</p></div>'
        '<div class="pillar rv" style="--c:#f0b93e"><b>03</b><h3>社会への実装と発信</h3><p>地域社会の課題解決やグローバルな発信活動を通じて、自らの「好き」や「疑問」を社会実装へつなげます。</p></div></div>', 'soft')
    h += sec('GOAL', '目標と、3つの開発プログラム', '<p class="lede rv narrow">「総合知」を核とした「哲学的思考（問いを立てる力）× データサイエンス（科学的解決）」融合プログラムを開発し、全校に普及定着させることで、文理の壁を超越した次世代のグローバルリーダーを育成する。</p>'
        '<ol class="journey rv narrow"><li><b>01</b>東洋大学や研究機関、企業等と連携し、データサイエンス、統計的な手法、およびAIを活用できるプログラムの開発。</li>'
        '<li><b>02</b>哲学シンキングを導入し、先端的な科学技術の知識を活用した探究活動に取り組みながら、人間・社会・自然などの多様な側面を総合的に理解し、本質的な問いを創出し、論理的に判断する力を育成するプログラムの開発。</li>'
        '<li><b>03</b>アントレプレナー教育と融合した具体的な体験や経験の中で、自然科学、人文・社会科学、さらには地域社会、文化・芸術など幅広い領域の知見を活用し、新たな価値を創造できるプログラムの開発。</li></ol>'
        + nums([('47', '校', '令和8年度のSSH新規採択（全国）'), ('3', '校', 'うち文理融合基礎枠。本校を含む'), ('8', '校目', '茨城県内のSSH指定校として'), ('5', '年間', '2026年度からの指定期間')]))
    h += sec('MODEL', '総合知トライアングル', '<figure class="tri rv"><img src="assets/concept-triangle.jpg" alt="TOYO USHIKU 文理融合SSHモデル図：哲学シンキング・Data Science・グローバル教育の三要素が「総合知」を中心に循環する概念図" loading="lazy"><figcaption>哲学シンキング × Data Science × グローバル教育</figcaption></figure>', 'soft')
    h += sec('IN PRACTICE', '実際の授業・活動から', cards(['elsi', 'agri', 'genai']), 'navy')
    return h

def p_frontier():
    pg = 'frontier-boost-program'; sa = after(pg, '高大連携事業', 1); ph = after(pg, '問いを立てる力', 1)
    h = sec('UNIVERSITY', '高大連携事業 Summer Academia', f'<div class="two"><div class="rv prose">{paras(sa)}</div>{fig("fbp-00.jpg", "Summer Academia の体験講座")}</div>' + nums([('100', '名以上', '本校から毎年参加'), ('12', '学部', '体験講座を実施'), ('4', 'キャンパス', '白山・赤羽台・川越・朝霞'), ('2', '日間', '夏休みに実施')]))
    h += sec('PHILOSOPHY', '問いを立てる力 ～哲学シンキング～', f'<div class="two rev">{fig("fbp-01.jpg", "哲学シンキング講演会")}<div class="rv prose">{paras(ph)}</div></div>', 'soft')
    jour = ['哲学シンキング ①', '哲学シンキング ②', '哲学シンキング ③', 'データサイエンス教育 ①', 'データサイエンス教育 ②', 'データサイエンス教育 ③', 'データサイエンス教育 ④', '理系大学 施設見学', 'つくば市研究所 施設見学', '東洋大学 施設見学', '茨城大学農学部 インターンシップ', 'STEAM講座']
    h += sec('SCIENCE FRONTIER CLASS', '理数フロンティアクラス プログラム', '<div class="two"><div class="rv"><p class="lede">長期研究型プロジェクト「フロンティアラボ」と、12回の「インサイトジャーニー」で構成します。</p><ol class="journey">' + ''.join(f'<li><b>{i + 1:02d}</b>{esc(j)}</li>' for i, j in enumerate(jour)) + f'</ol></div><div class="stack">{fig("fbp-03.jpg", "理科実験室での実習")}{fig("fbp-02.jpg", "理数フロンティアクラス プログラム一覧表", "plain")}</div></div><p class="rv"><a class="btn" href="https://sites.google.com/toyo.jp/science-frontier" target="_blank" rel="noopener">理数フロンティアクラスの紹介サイト ↗</a></p>')
    h += sec('2026', '1期生の歩み', cards(['hrcamp', 'seminar', 'robot', 'steam', 'genai', 'camp']), 'navy')
    return h

AWARDS = [
 ('グランプリ', 'IBARAKIドリーム・パスAWARD', '過去最多 857件の応募から。倍率約54倍の選考を経て優勝。', 'dreampass'),
 ('第3位', '全国ユース環境活動発表大会（全国大会）', '国連大学サステイナビリティ高等研究所 所長賞。全国16チーム中、普通科として最上位。', 'youth'),
 ('最優秀賞', 'クールアースいばらき2026大会', '茨城県代表として「脱炭素チャレンジカップ2027」へ。', 'coolearth'),
 ('特別賞', '高校生バイオサミット in 鶴岡', '初代「One ip TOHOKU賞」。決勝45演題の中から受賞。', 'biosummit'),
 ('大賞', '第27回げんでん科学技術振興事業', '第18回高校生理科研究発表会でも優秀賞。', 'genden'),
 ('優秀賞', 'CIEC春季カンファレンス2026', '優秀賞と奨励賞を受賞。', 'ciec'),
 ('選出', 'つくば Science Edge', '過去最多477件の中から、ブースポスタープレゼンテーションに選出。', 'scienceedge'),
 ('初参加', '令和8年度 SSH生徒研究発表会', '全国239校が集う国内最大級の発表会に、ICT Lab が参加。', 'sshconf'),
]
def p_achievements():
    h = sec('BY THE NUMBERS', '数字で見る成果', nums([('857', '件', '応募の中からグランプリ'), ('16', 'チーム', '全国大会で第3位'), ('45', '演題', '決勝進出から特別賞'), ('239', '校', 'が集う発表会に初参加')]), 'navy')
    h += sec('AWARDS', '主な受賞・選出', '<div class="awards">' + ''.join(f'<a class="award rv" href="{href("activities", "#" + i)}"{ext("activities")}><b>{esc(n)}</b><h3>{esc(t)}</h3><p>{esc(d)}</p><span>{AR[i]["date"]} ・ 記事を読む →</span></a>' for n, t, d, i in AWARDS if i in AR) + '</div>')
    h += sec('MATERIALS', '報告書・ルーブリックなど', f'<p class="lede rv">報告書やルーブリックなどの成果物は、完成しだいここに掲載します。研究発表のスライドは「研究開発実施報告書」のページで公開しています。</p><p class="rv"><a class="btn" href="{href("reports")}"{ext("reports")}>研究発表の資料を見る →</a></p>', 'soft')
    return h

def p_activities():
    cats = [(k, v) for k, v in CATS.items() if any(a['cat'] == k for a in ARTS)]
    f = f'<div class="filter rv" id="filter"><button data-c="all" aria-pressed="true">すべて <i>{len(ARTS)}</i></button>' + ''.join(f'<button data-c="{k}" aria-pressed="false">{v} <i>{sum(a["cat"] == k for a in ARTS)}</i></button>' for k, v in cats) + '</div>'
    new = [a['id'] for a in ARTS if a['key'] >= '20260401' or a['key'] == '00000000']; old = [a['id'] for a in ARTS if '00000000' < a['key'] < '20260401']
    return sec('2026 —', 'SSH指定後の取り組み', f + cards(new, True)) + sec('BEFORE 2026', '指定以前の取り組み', cards(old, True), 'soft')

def p_outreach():
    pg = 'ssh普及発信活動'; t = after(pg, '本校の取り組みが「日経サイエンス」'); fr = frames(pg)
    names = [('SSHガイドブック', ''), ('令和8年度 SSH生徒研究発表会 参加登録について', '一般参加者向け')]
    h = sec('MEDIA', '『日経サイエンス』に掲載されました', f'<div class="two"><div class="rv prose">{paras(t)}</div>{fig("out-00.jpg", "日経サイエンス掲載ページ：廃棄物を利用した大豆生産研究", "tall")}</div>')
    h += sec('IN THE NEWS', 'メディア・地域での発信', cards(['yahoo', 'radio', 'aeon', 'kengikai', 'nikkei']), 'navy')
    items = [(names[i] if i < len(names) else (f'資料 {i + 1}', '')) + (fid,) for i, fid in enumerate(fr)]
    h += sec('FOR SCHOOLS', '全国高校への発信・県内高校への発信', '<div class="pdfs">' + ''.join(pdf(t, fid, note) for t, note, fid in items) + '</div>', 'soft')
    return h

def p_reports():
    pg = '研究開発実施報告書'; fr = frames(pg)
    names = ['SDGs Lab エコアスファルト研究 説明用スライド', 'SDGs Lab 発表スライド', 'げんでん科学技術振興事業 表彰式 発表スライド']
    notice = line(pg, '26年度新規指定校') if any(l.startswith('26年度新規指定校') for l in flat(pg)) else ''
    h = sec('ANNUAL REPORT', '研究開発実施報告書', '<div class="notice rv"><b>2026年度末に完成予定</b><p>本校は2026年度の新規指定校のため、今年度末に第1年次の研究開発実施報告書が完成します。完成しだい、このページで公開します。</p></div>' if notice else '<p class="lede rv">報告書は下の資料からご覧いただけます。</p>')
    h += sec('SLIDES', '研究発表の資料', '<div class="pdfs">' + ''.join(pdf(names[i] if i < len(names) else f'資料 {i + 1}', fid) for i, fid in enumerate(fr)) + '</div>', 'soft')
    h += sec('RELATED', '関連する記事', cards(['asphalt', 'genden', 'youth']), 'navy')
    return h

def p_committee():
    pg = '運営指導委員会'; mem = [l for l in flat(pg) if '先生' in l and '大学' in l]
    rows = ''.join('<tr><th>{}</th><td>{}</td></tr>'.format(*[esc(x.strip()) for x in re.split(r'先生[\s　]+', m, 1)]) for m in mem if re.search(r'先生[\s　]+', m))
    sched = [l.lstrip('■') for l in flat(pg) if re.match(r'■第\d+回', l)]
    def li(l):
        m = re.match(r'(第\d+回運営指導委員会)[\s　]*(\d+)年(\d+)月(\d+)日[\s　]*(.*)', l)
        return f'<li class="rv"><time>{int(m[2])}.{int(m[3]):02d}.{int(m[4]):02d}</time><b>{esc(m[1])}</b><span>{esc(m[5])}</span></li>' if m else f'<li class="rv"><b>{esc(l)}</b></li>'
    h = sec('MEMBERS', '2026年度 運営指導委員の先生方', f'<table class="members rv"><tbody>{rows}</tbody></table>')
    h += sec('SCHEDULE', '2026年度 日程', f'<ol class="tl">{"".join(li(l) for l in sched)}</ol>', 'soft')
    if 'committee1' in AR: h += sec('REPORT', '第1回運営指導委員会の報告', f'<div class="prose rv narrow">{paras(AR["committee1"]["body"])}</div>')
    return h

def p_visits():
    pg = 'ssh先進校視察及び視察の受け入れ'; z = str.maketrans('０１２３４５６７８９', '0123456789')
    recs = [re.match(r'(\d+)年(\d+)月(\d+)日[\s　]*(.+)', l.translate(z)) for l in flat(pg)]
    tl = ''.join(f'<li class="rv {"in" if "受け入れ" in m[4] else ""}"><time>{int(m[1])}.{int(m[2]):02d}.{int(m[3]):02d}</time><b>{esc(m[4])}</b><span>{"受け入れ" if "受け入れ" in m[4] else "視察"}</span></li>' for m in recs if m)
    h = sec('RECORD', '視察と受け入れの記録', f'<div class="two"><ol class="tl">{tl}</ol>{fig("vis-00.jpg", "本校の生徒たち")}</div>')
    h += sec('REPORTS', '視察・受け入れの報告', cards(['nagoya', 'kengikai', 'fuji']), 'navy')
    return h

def p_logos():
    pg = 'ssh通信logos-ushiku'; intro = line(pg, '公式通信'); ids = frames(pg); T = CFG['logos_topics']
    def issue(i, f):
        n = i + 1; t = T.get(str(n), [f'LOGOS Ushiku No.{n}', '']); cover = ROOT / f'assets/logos/no{n}.jpg'
        if str(n) not in T: NOTES.append(f'SSH通信 No.{n} が増えています。見出し（content/articles.json の logos_topics）と表紙画像（assets/logos/no{n}.jpg）が未設定です。')
        im = f'<img src="assets/logos/no{n}.jpg" alt="LOGOS Ushiku No.{n} の紙面" loading="lazy">' if cover.exists() else '<div class="noimg c-media"><span>LOGOS Ushiku</span></div>'
        return f'<a class="issue rv" href="{DRIVE % f}" target="_blank" rel="noopener">{im}<div><small>2026年度 No.{n}</small><b>{esc(t[0])}</b><span>{esc(t[1])}</span><i>PDFを開く ↗</i></div></a>'
    iss = ''.join(issue(i, f) for i, f in reversed(list(enumerate(ids))))
    h = sec('ABOUT', 'LOGOS ＝ 論理、真理。', f'<p class="lede rv narrow">{esc(intro)}</p>')
    h += sec('BACK NUMBERS', 'バックナンバー', f'<div class="issues">{iss}</div>', 'navy')
    if ids: h += sec('LATEST', f'最新号 No.{len(ids)}', f'<div class="viewer rv"><iframe src="https://drive.google.com/file/d/{ids[-1]}/preview" title="LOGOS Ushiku No.{len(ids)}" loading="lazy" allow="autoplay"></iframe></div>', 'soft')
    return h

BODY = dict(inquiry=p_inquiry, frontier=p_frontier, achievements=p_achievements, activities=p_activities, outreach=p_outreach, reports=p_reports, committee=p_committee, visits=p_visits, logos=p_logos)
FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@300;400;500;700;900&family=Zen+Old+Mincho:wght@400;600;900&family=Plus+Jakarta+Sans:wght@700;800&family=Fragment+Mono&display=swap" rel="stylesheet">'

def render(i):
    slug, jp, en, lead, color, gname = PAGES[i]
    random.seed(slug)
    dots = ''.join(f'<i style="left:{random.randint(2, 98)}%;top:{random.randint(6, 92)}%;--s:{random.randint(4, 11)}px;--d:{random.uniform(5, 11):.1f}s;--c:{random.choice(["#f0b93e", "#ef5b6b", "#2fd0a8", "#5b9df0"])}"></i>' for _ in range(22))
    menu = ''.join(f'<li style="--i:{k}"><a href="{href(p[0])}"{ext(p[0])}{" aria-current=page" if k == i else ""}>{esc(p[1])}<small>{k + 1:02d} — {p[2]}</small></a></li>' for k, p in enumerate(PAGES))
    loc = [p for p in PAGES if is_local(p[0])]; j = loc.index(PAGES[i]); prev, nxt = loc[j - 1], loc[(j + 1) % len(loc)]
    k = 0; words = []
    for w in jp.split(' '):
        words.append('<span class="w">' + ''.join(f'<span style="--i:{k + n}">{esc(c)}</span>' for n, c in enumerate(w)) + '</span>'); k += len(w)
    title = f'{jp}｜TOYO USHIKU SSH'; url = BASE_URL + slug + '.html'
    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(lead)} 東洋大学附属牛久中学校・高等学校 SSH特設サイト。">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/png" sizes="32x32" href="assets/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png">
<meta property="og:type" content="article"><meta property="og:locale" content="ja_JP"><meta property="og:site_name" content="TOYO USHIKU SSH">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(lead)}"><meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE_URL}assets/hero-enryo.jpg"><meta name="twitter:card" content="summary_large_image">
{FONTS}
<link rel="stylesheet" href="sub.css">
</head>
<body style="--pc:{color}">
<!-- このファイルは tools/build.py が生成します。直接編集しないでください。 -->
<header class="top"><a class="brand" href="./"><b>SSH</b>東洋大学附属牛久中学校・高等学校</a></header>
<button class="menu-btn" id="menuBtn" type="button" aria-expanded="false" aria-controls="menu">MENU</button>
<nav class="menu" id="menu" aria-label="メニュー"><div class="cols"><div><h3>CONTENTS</h3><ul>{menu}</ul></div><div><h3>TOP</h3><ul><li style="--i:2"><a href="./">トップページ<small>HOME</small></a></li><li style="--i:3"><a href="https://www.toyo.ac.jp/ushiku/" target="_blank" rel="noopener">学校公式サイト ↗<small>TOYO USHIKU</small></a></li></ul></div></div></nav>
<div class="hero"><div class="dots" aria-hidden="true">{dots}</div><div class="in">
  <p class="eyebrow">{i + 1:02d} / {len(PAGES):02d} — {en}</p>
  <h1 aria-label="{esc(jp)}">{' '.join(words)}</h1>
  <p class="lead">{esc(lead)}</p>
</div></div>
<main>{BODY[slug]()}</main>
<p class="gs"><a href="{gs_url(gname)}" target="_blank" rel="noopener">このページの Googleサイト版を見る ↗</a></p>
<nav class="pager" aria-label="前後のページ"><a href="{prev[0]}.html"><small>← PREV</small>{esc(prev[1])}</a><a href="./#entrance"><small>CONTENTS</small>一覧へ</a><a href="{nxt[0]}.html"><small>NEXT →</small>{esc(nxt[1])}</a></nav>
<footer class="foot"><div class="in">
  <div class="id"><img src="assets/school-crest.png" alt="東洋大学附属牛久中学校・高等学校 校章"><div><span>TOYO UNIV. USHIKU</span><b>東洋大学附属牛久中学校・高等学校</b><span>スーパーサイエンスハイスクール特設サイト</span></div></div>
  <a class="topl" href="https://www.toyo.ac.jp/ushiku/" target="_blank" rel="noopener">東洋大学附属牛久中学校・高等学校 TOPへ ↗</a>
  <small>TOYO UNIV USHIKU｜webmaster@toyo-ushiku.ed.jp｜029-872-0350<br>© 2026 Toyo University Ushiku Junior &amp; Senior High School. All Rights Reserved.</small>
</div></footer>
<script src="sub.js"></script>
</body>
</html>
'''

made = []
for i, p in enumerate(PAGES):
    f = ROOT / f'{p[0]}.html'
    if is_local(p[0]): f.write_text(render(i), encoding='utf-8'); made.append(p[0])
    elif f.exists(): f.unlink()

# トップページが読む設定（一覧・メニュー・写真の行き先）
data = {p[0]: dict(title=p[1], en=p[2].title(), href=href(p[0]), external=not is_local(p[0]), aud=AUD[p[0]]) for p in PAGES}
arts = {a['id']: True for a in ARTS}
(ROOT / 'site-data.js').write_text('// tools/build.py が生成します。直接編集しないでください。\nwindow.SSH_SITE = ' + json.dumps(dict(order=ORDER, pages=data, articles=arts), ensure_ascii=False, indent=1) + ';\n', encoding='utf-8')

today = datetime.date.today().isoformat()
urls = [BASE_URL] + [BASE_URL + s + '.html' for s in made]
(ROOT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n' for u in urls) + '</urlset>\n', encoding='utf-8')
(ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nDisallow: /classic/\n\nSitemap: {BASE_URL}sitemap.xml\n', encoding='utf-8')

print(f'生成: {len(made)}ページ / 記事 {len(ARTS)}本（写真あり {sum(bool(a["img"]) for a in ARTS)}本） / Googleサイトへ直接リンク: {[p[0] for p in PAGES if not is_local(p[0])] or "なし"}')
if NOTES:
    print('\n[お知らせ]'); [print('  -', n) for n in dict.fromkeys(NOTES)]
