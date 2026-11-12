# TOYO USHIKU SSH 特設サイト

東洋大学附属牛久中学校・高等学校 スーパーサイエンスハイスクール特設サイト。
公開先: https://n-hatayama-ai.github.io/ssh-toyo-ushiku/

## しくみ

- 記事の正本は **Googleサイト**（https://sites.google.com/toyo.jp/test2026ssh/ ）。先生方はこれまで通り Googleサイトを更新する。
- このサイトは Googleサイトの本文を取り込んで、下層ページを作り直す。Googleサイト側は変更しない。

## 更新のしかた

```sh
python3 tools/sync_gsites.py   # Googleサイトを取り込む → content/gsites.json
python3 tools/build.py         # 下層9ページ・site-data.js・sitemap.xml・robots.txt を生成
python3 -m http.server 8792    # http://127.0.0.1:8792/ で確認してから公開（push）
```

生成のあとに出る［お知らせ］に、新しい記事・未設定の項目・見つからない見出しが並ぶ。

## どこを直すか

| 直したいもの | ファイル |
|---|---|
| 記事の本文 | Googleサイト（取り込み直す） |
| 記事の日付・分類・写真、新サイトだけの記事、SSH通信の各号の見出し | `content/articles.json` |
| ページを「サイト内で表示」か「Googleサイトへ直接リンク」か | `content/site.json`（`local` / `gsites`） |
| 下層ページの構成・受賞一覧・数字 | `tools/build.py` |
| トップページ（3D・章の文章・数字） | `index.html` |
| 下層ページの見た目 | `sub.css` / `sub.js` |
| 記事の写真 | `assets/news/`　SSH通信の表紙: `assets/logos/noN.jpg` |
| 記事の写真を複数枚に（カルーセル） | `content/articles.json` の記事に `"imgs": ["a.jpg", "b.jpg"]` を足す |

`inquiry.html` などの下層ページ、`site-data.js`、`sitemap.xml`、`robots.txt` は生成物。直接編集しない。

## 方針

- 生徒の個人名は載せない。取り込み時に取り除く（規則は `tools/sync_gsites.py` の `SCRUB`）。氏名が残っていそうな行は取り込み時に［要確認］として表示される。
- 3D の部品（three.js r160）は `vendor/` に置き、外部の配信元に依存しない。
- 3D が使えない端末・「視差効果を減らす」設定の端末では、通常の表示に切り替わる（`?flat` を付けると確認できる）。
- 以前のトップページは `classic/` に残してある。
