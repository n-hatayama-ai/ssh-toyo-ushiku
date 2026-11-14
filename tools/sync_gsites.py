#!/usr/bin/env python3
"""Googleサイト(正本)の本文を取り込み、content/gsites.json に保存する。
使い方: python3 tools/sync_gsites.py
- ログイン不要の公開ページを読むだけ。Googleサイト側は変更しない。
- 生徒の個人名は保存時に取り除く（このリポジトリは公開のため）。
"""
import json, re, sys, urllib.request, urllib.parse
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://sites.google.com/toyo.jp/test2026ssh/'
PAGES = ['東洋大牛久の目指す探究教育', 'frontier-boost-program', 'ssh成果物', '探究活動の様々な取り組み', 'ssh普及発信活動',
         '研究開発実施報告書', '運営指導委員会', 'ssh先進校視察及び視察の受け入れ', 'ssh通信logos-ushiku']

# 2026-11-14 方針変更: このサイトはJSTへの報告を兼ねるため、生徒氏名はGoogleサイトの記載どおり載せる。
# 特定の文を取り除きたくなったときだけ SCRUB に (正規表現, 置換) を足す。
SCRUB = []
DROP_LINE = None                                                       # 以前は「学校名＋氏名」だけの行を落としていた
SUSPECT = re.compile(r'さん[(（]\d+[)）]|\d[A-Z]\d+[\s　]')            # 氏名が残っていそうな形

class P(HTMLParser):
    BLOCK = {'h1', 'h2', 'h3', 'p', 'li'}
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.secs, s.sec, s.depth, s.buf, s.tag, s.skip, s.a = [], None, 0, None, None, 0, None
    def handle_starttag(s, t, attrs):
        a = dict(attrs)
        if t == 'section':
            s.depth += 1
            if s.depth == 1: s.sec = dict(lines=[], heads=[], frames=[], links=[])
        if s.sec is None: return
        if t in ('script', 'style', 'svg'): s.skip += 1
        u = a.get('data-embed-open-url') or ''
        m = re.search(r'[?&]id=([\w-]+)', u) or re.search(r'/d/([\w-]+)', u)
        if m and m.group(1) not in s.sec['frames']: s.sec['frames'].append(m.group(1))
        if t in s.BLOCK and s.buf is None: s.buf, s.tag = [], t
        if t == 'br' and s.buf is not None: s.buf.append('\n')
        if t == 'a' and a.get('href', '').startswith('http'): s.a = [a['href'], []]
    def handle_endtag(s, t):
        if t == 'section':
            s.depth -= 1
            if s.depth == 0 and s.sec is not None:
                if s.sec['lines'] or s.sec['frames']: s.secs.append(s.sec)
                s.sec = None
            return
        if s.sec is None: return
        if t in ('script', 'style', 'svg') and s.skip: s.skip -= 1
        if t == 'a' and s.a:
            txt = ''.join(s.a[1]).strip()
            if 'test2026ssh' not in s.a[0] and 'google.com/url' not in s.a[0] or 'q=' in s.a[0]:
                href = urllib.parse.parse_qs(urllib.parse.urlparse(s.a[0]).query).get('q', [s.a[0]])[0]
                if 'test2026ssh' not in href: s.sec['links'].append([txt, href])
            s.a = None
        if t == s.tag and s.buf is not None:
            lines = [l.strip().strip('　').strip() for l in ''.join(s.buf).replace('\xa0', ' ').split('\n')]
            lines = [l for l in lines if l]
            if lines and t in ('h1', 'h2', 'h3'): s.sec['heads'].append(lines[0])
            s.sec['lines'] += lines
            s.buf = s.tag = None
    def handle_data(s, d):
        if s.sec is None or s.skip: return
        if s.buf is not None: s.buf.append(d)
        if s.a: s.a[1].append(d)

def scrub(line):
    if DROP_LINE and DROP_LINE.match(line): return None
    for pat, rep in SCRUB: line = re.sub(pat, rep, line)
    return line.strip() or None

def main():
    out, warn = {}, []
    for pg in PAGES:
        req = urllib.request.Request(BASE + urllib.parse.quote(pg), headers={'User-Agent': 'Mozilla/5.0'})
        p = P(); p.feed(urllib.request.urlopen(req, timeout=40).read().decode('utf-8'))
        for sec in p.secs:
            sec['lines'] = [x for x in (scrub(l) for l in sec['lines']) if x]
            warn += [f'{pg}: {l[:60]}' for l in sec['lines'] if SUSPECT.search(l)]
        if not any(s['lines'] for s in p.secs): sys.exit(f'本文を取得できませんでした: {pg}（Googleサイトの公開設定や構造を確認）')
        out[pg] = p.secs
        print(f'{pg}: {len(p.secs)}区画 / {sum(len(s["lines"]) for s in p.secs)}行 / 見出し{sum(len(s["heads"]) for s in p.secs)} / PDF{sum(len(s["frames"]) for s in p.secs)}')
    (ROOT / 'content').mkdir(exist_ok=True)
    (ROOT / 'content/gsites.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    if warn:
        print('\n[参考] 氏名を含む行（方針どおり掲載）:'); [print('  -', w) for w in warn]
    print('\n保存: content/gsites.json  → 次は python3 tools/build.py')

if __name__ == '__main__': main()
