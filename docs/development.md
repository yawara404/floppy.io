# 開発・運用ガイド

[← floppy.io の紹介に戻る](../README.md)

セットアップ、実装仕様、API、公開手順をまとめています。コード中のパスとコマンドは、特記がなければリポジトリのルートを基準にしています。

[開発環境](#開発環境) · [運用・障害対策](#運用--障害対策) · [画面と URL](#画面と-url履歴モード) · [API 一覧](#api-一覧) · [セキュリティ](#セキュリティ)

---

## 公開サイト

👉 **<https://fdd.wawa-app.me/floppy.io/>**

Cloudflare Tunnel `floppy` から、ローカルのゲートウェイ (`tools/public_gateway.py`)
へ流し、静的ファイルと FastAPI を振り分けています（Apache / nginx の ProxyPass 相当）。

```text
ブラウザ
  → Cloudflare (fdd.wawa-app.me) → トンネル floppy
    → http://127.0.0.1:8899 (tools/public_gateway.py)
       ├── /floppy.io/             → frontend/dist（Nuxt の静的ビルド）
       ├── /floppy.io/api/...      → http://127.0.0.1:8001/api/...     (FastAPI)
       └── /floppy.io/uploads/...  → http://127.0.0.1:8001/uploads/... (FastAPI)
```

```bash
./tools/public.sh start     # API(:8001) + ゲートウェイ(:8899) + トンネル
./tools/public.sh status    # ローカル 3 点 + 公開 URL を確認
./tools/public.sh stop
./tools/public.sh setup     # トンネル / DNS を作り直すとき（初回のみ）
```

> ポート 8000 は他プロジェクト（Midair.io）が使っているため、floppy.io の API は
> **8001** で動かします。開発時は `FLOPPY_API_PORT=8001 npm run dev` で合わせられます。

## SNS カード（OGP / Twitter Card）

URL を貼るとカードが展開されます。OGP は業界標準なので、X（Twitter）
専用ではなく**各 SNS で共通して使えます**。

| サービス | 参照するタグ |
| --- | --- |
| X（Twitter） | `twitter:*`（無ければ `og:*` にフォールバック） |
| Facebook / Instagram DM | `og:*` |
| Slack / Discord / Teams | `og:*`（Discord は `theme-color` で埋め込みの色を変える） |
| LINE / WhatsApp / Telegram | `og:*` |
| LinkedIn / Pinterest | `og:*` |
| Mastodon / Misskey / Bluesky | `og:*` |
| iMessage / はてなブックマーク / note など | `og:*` |

### サイト共通カード

- トップページなどのカード情報は `frontend/nuxt.config.ts` に**静的に**書いています。
- 画像は 1200×630（`summary_large_image` 推奨サイズ）の
  `frontend/public/card.png` です。元データは `tools/og-card.html` で、
  `tools/make-og-card.sh` で再生成できます。

```bash
tools/make-og-card.sh    # tools/og-card.html → frontend/public/card.png
```

### 投稿別カード（`/p/:id`）

SPA（`ssr: false`）のままではクローラーが投稿本文を読めないため、
**SNS クローラーにだけ投稿別 OGP HTML を返しています**。

- `tools/public_gateway.py` が User-Agent を判定し、`/p/:id` への
  Twitterbot / Facebook / Slack / Discord / LINE / Mastodon などからのアクセスを
  FastAPI の `GET /api/og/post/:id` に転送します。
- 人間のブラウザと検索エンジンには、従来どおり `frontend/dist` の SPA を返します。
- OGP の内容
  - `og:title` / `twitter:title`: `No.31 @wawa404 — floppy.io`
  - `og:description`: ディスク名＋本文（URL は除外、180 文字まで）
  - `og:image`:
    - YouTube → `https://i.ytimg.com/vi/<id>/hqdefault.jpg`
    - 画像 → アップロードされた画像
    - ドット絵のみ → **1200×630 の PNG をサーバー生成**
      （`GET /api/og/post/:id/image.png`・Pillow 不要）
    - テキストのみ → サイト共通 `card.png`
  - `twitter:card=summary_large_image` / `og:url` / `article:published_time`
- 画像・OGP HTML は `Cache-Control` を適切に設定しています。X 側はカードを
  キャッシュするため、既存ツイートのカードを更新したい場合は Card Validator などで
  再取得してください。
- `FLOPPY_PUBLIC_BASE_URL` が `og:url` / `og:image` の絶対 URL に使われます。

## 技術スタック

| レイヤー | 技術 |
| --- | --- |
| フロントエンド | Nuxt 4 (Vue 3 Composition API / SPA / 履歴モード) |
| スタイル | 独自 CSS「RETRO BBS / EARLY TWITTER / MIXI2」（生成り・ミント・青リンク・ドット枠） |
| 描画 | HTML5 Canvas API（外部描画ライブラリ不使用） |
| バックエンド | Python 3.12+ / FastAPI（RESTful JSON API） |
| DB ドライバ | PyMySQL（プレースホルダで SQL インジェクション対策） |
| 認証 | bcrypt + Bearer トークン（`api_tokens`） |
| データベース | MySQL 8.x（`utf8mb4`） |

## コア仕様

- **容量制限（1 投稿あたり）**: 投稿時に本文の UTF-8 バイト数、
  ドット絵データ、添付画像・ファイルのバイト数を合算し、**その投稿の合計**が `1,474,560 Bytes` を超える
  場合は HTTP **403** で弾く。累計では制限しない。
- **ドット絵の超軽量データ化**: 画像ファイルには変換せず、
  「カラーコードのインデックス配列」を 16 進文字列として DB に保存する。
  各文字 `0-9A-F` が 16 色パレットの 1 色に対応。キャンバスは 3 種類:
  - **正方形（32×32 = 1,024 マス / 1,024 バイト）**
  - **Miiverse（32×24 = 768 マス / 768 バイト・4:3）**
  - **クラシック（16×16 = 256 マス / 256 バイト・旧データ互換）**

## ディレクトリ構成

```text
floppy_io/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI アプリ / CORS / エラーハンドラ
│   │   ├── config.py               # 環境変数 (.env) と定数
│   │   ├── db.py                   # PyMySQL 接続 / クエリヘルパー
│   │   ├── security.py             # bcrypt / Bearer 認証 / ユーザー整形
│   │   ├── posts.py                # 投稿の整形 / いいね集計
│   │   ├── disks.py                # ディスク (コミュニティ) の整形
│   │   ├── schemas.py              # リクエストスキーマ
│   │   ├── routers/
│   │   │   ├── auth.py             # 登録 / ログイン / ログアウト / me
│   │   │   ├── posts.py            # 投稿一覧・投稿・削除・プレビュー・容量
│   │   │   ├── disks.py            # ディスク一覧・作成・参加・書き込み一覧
│   │   │   ├── search.py           # 検索サジェスト (ユーザー / ディスク / 投稿)
│   │   │   ├── users.py            # プロフィール / 設定 / アバター
│   │   │   ├── social.py           # いいね / フォロー
│   │   │   └── uploads.py          # /uploads/<name> の配信
│   │   └── utils/
│   │       ├── pixels.py           # ドット絵 (16×16 / 32×32 / 32×24 / 32×32 アイコン)
│   │       ├── avatars.py          # ユーザーアイコン URL の共通組み立て
│   │       ├── sql.py              # LIKE エスケープ
│   │       ├── images.py           # 画像の MIME / 寸法判定
│   │       ├── uploads.py          # ファイル保存 / URL
│   │       └── youtube.py          # YouTube Data API v3 連携
│   ├── uploads/                    # アップロードされた実ファイル
│   ├── requirements.txt
│   ├── .env.example
│   └── run.sh                      # venv 作成 + uvicorn 起動
├── database/
│   ├── schema.sql                  # MySQL DDL（＋デモユーザー投入）
│   └── migrations/                 # 既存 DB 向けの追加マイグレーション
├── frontend/
│   ├── app/
│   │   ├── app.vue                 # Nuxt ルート
│   │   ├── layouts/default.vue     # トップバー / サイドバー / フッター
│   │   ├── pages/                  # ファイルベースルーティング
│   │   │   ├── index.vue           # /
│   │   │   ├── disks.vue           # /disks (ディスク一覧)
│   │   │   ├── d/[slug].vue        # /d/:slug (ディスク個別)
│   │   │   ├── following.vue       # /following（フォロー中タイムライン）
│   │   │   ├── search.vue          # /search
│   │   │   ├── u/[username]/       # /u/:username (+ /following, /followers)
│   │   │   ├── p/[id].vue          # /p/:id
│   │   │   ├── login.vue / register.vue
│   │   │   └── settings.vue / help.vue
│   │   ├── components/             # Composer / PostItem / YouTubeEmbed など
│   │   ├── views/                  # 画面本体 (Home / Disks / Disk / Profile ...)
│   │   ├── composables/            # useAuth / usePostShare / useAvatarImage /
│   │   │                           # useAvatarCanvas / useDialog
│   │   ├── utils/api.js            # API クライアント
│   │   ├── utils/pixel.js          # ドット絵のパース/描画・初期アイコン
│   │   ├── utils/format.js         # 数値・日時の表示整形
│   │   ├── utils/post.js           # 投稿の種類 / ドット絵 / サムネイル判定
│   │   ├── utils/env.js            # IP アドレス判定 / localhost URL
│   │   └── assets/css/main.css     # RETRO BBS デザインシステム
│   ├── public/
│   │   ├── config.js               # 実行時 API 接続先
│   │   ├── card.png                # SNS カード用の画像 (1200x630)
│   │   ├── favicon.svg             # ピクセルフロッピー (SVG)
│   │   ├── favicon.png             # 512x512 fallback
│   │   ├── favicon-32.png          # 32x32 fallback
│   │   └── apple-touch-icon.png    # 180x180
│   ├── nuxt.config.ts              # OGP / フォント / プロキシ / 履歴モード
│   └── package.json
├── tools/
│   ├── og-card.html                # SNS カード画像の元データ
│   └── make-og-card.sh
└── README.md
```

## 開発環境

### 動作確認

フロントエンドの通信テストと、フォロー一覧 API のテストを用意しています。
依存関係の導入後、リポジトリのルートから実行できます。

```bash
npm --prefix frontend test
cd backend
.venv/bin/python -m unittest discover -s tests -v
```


### 1. MySQL

```bash
# スキーマ + デモユーザー (floppy / floppy)
mysql -u root -p < database/schema.sql

# API 用の専用ユーザー（開発用の例。本番は強いパスワードに変更）
mysql -u root -p -e "
  CREATE USER IF NOT EXISTS 'floppy'@'localhost' IDENTIFIED BY 'floppy';
  GRANT SELECT, INSERT, UPDATE, DELETE ON floppy_io.* TO 'floppy'@'localhost';
  FLUSH PRIVILEGES;"
```

> MySQL は標準の **127.0.0.1:3306** で起動している前提です。
> 接続先は `backend/.env` の `FLOPPY_DB_*` で変更できます。

#### 既存の DB を最新スキーマへ更新する

旧バージョン（PHP 版）の DB をそのまま使うと `follows` テーブルが無く、
**ログイン / 新規登録が 503** になります（`public_user()` が
`follows` を参照するため）。`database/schema.sql` は
`CREATE TABLE IF NOT EXISTS` だけで構成されているので、流し込むだけで
既存データを残したまま不足テーブルを追加できます。

```bash
mysql -u root -p < database/schema.sql
```

適用後は `/api/health` と `/login` でログインできることを確認してください。

#### 返信・アイコン・キャンバス拡張を既存 DB に追加する

`database/schema.sql` は `CREATE TABLE IF NOT EXISTS` のため、**既存テーブルに
新しいカラムは追加されません**。返信（`allow_replies` / `reply_to_id`）、
32×32 アイコン（`icon_pixel`）、ドット絵キャンバス（`pixel_width` / `pixel_height`）
を使うには、マイグレーションを順に 1 回ずつ適用します。

```bash
mysql -u root -p < database/migrations/2026-11-05-replies.sql
mysql -u root -p < database/migrations/2026-11-06-canvas.sql
```

（`ALTER TABLE` は DB の所有者権限が必要です。API 用ユーザー `floppy` では
実行できないため、`root` などで実行してください。）

### 2. Python API (FastAPI)

```bash
cd backend
cp .env.example .env        # DB の接続先を必要に応じて編集
./run.sh                    # .venv 作成 + 依存インストール + uvicorn :8000
```

- API ドキュメント: <http://127.0.0.1:8000/api/docs>
- ヘルスチェック: <http://127.0.0.1:8000/api/health>
- アップロードは `backend/uploads/` に保存されます（`FLOPPY_UPLOAD_DIR` で変更可能）。

### 3. Nuxt フロントエンド

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

`nuxt.config.ts` の Vite プロキシが `/api` と `/uploads` を
`http://127.0.0.1:8000` に転送します。

#### VS Code / Nuxtr を使う場合

Nuxt はワークスペース直下ではなく `frontend/` にあるため、Nuxtr には
次の設定が必要です（`.vscode/settings.json` に設定済み）。

```json
{
  "nuxtr.monorepoMode.DirectoryName": "frontend",
  "nuxtr.defaultPackageManager": "NPM"
}
```

1. 設定変更後、コマンドパレットから **Developer: Reload Window** を実行する
2. Nuxtr の **Nuxt dev** を実行する（`frontend/` で `npx nuxi dev` が走ります）
3. 表示された <http://localhost:5173/> を開く

それでも Nuxtr が有効にならない場合は、`frontend/` フォルダを単独で
VS Code に開くと確実です。

### 4. 本番ビルド

```bash
cd frontend
npm run build:subdir        # /floppy.io/ 配下に置く場合
# または npm run build     # ルート直下に置く場合
```

`frontend/dist` を静的配信し、`/api` と `/uploads` を FastAPI に
リバースプロキシしてください（例: `ProxyPass /floppy.io/api http://127.0.0.1:8000/api`）。
サブディレクトリ公開時は `backend/.env` に
`FLOPPY_PUBLIC_BASE_URL=https://example.com/floppy.io/` を設定してください。
共有用 HTML の絶対 URL と、アバター / 画像 / 添付ファイルの URL
（`/floppy.io/uploads/...`）の両方がこの値をもとに生成されます。

## 運用 / 障害対策

### 自動再起動（落ちても復帰する）

| 環境 | 方法 |
| --- | --- |
| 開発 (macOS / Linux) | `cd backend && ./serve.sh`（異常終了したら 3 秒後に自動再起動） |
| macOS 常駐 | `deploy/com.floppy.api.plist` を `~/Library/LaunchAgents/` に置いて `launchctl load` |
| Linux 本番 | `deploy/floppy-api.service` を `/etc/systemd/system/` に置いて `systemctl enable --now floppy-api` |

- `./run.sh` は開発用（`--reload` あり・自動再起動なし）です。常駐には `./serve.sh` か
  `deploy/` の設定を使ってください。
- どちらのスクリプトも、ポートが使用中なら**どのプロセスが握っているか**を表示して終了します
  （別ポートで動かす場合は `PORT=8001 ./run.sh` と `FLOPPY_API_PORT=8001 npm run dev`）。
- ログは `backend/logs/api.log` に残ります（`backend/logs/` は `.gitignore` 済み）。

### 公開スタック（URL）の自動復旧

公開サイトは「API + ゲートウェイ + Cloudflare Tunnel」の 3 つで動いています。
`deploy/com.floppy.public.plist` を launchd に入れると、**1 分ごと**に
`tools/public.sh ensure` が走り、落ちているものだけが復旧します（ログイン時にも実行）。

```bash
mkdir -p logs
cp deploy/com.floppy.public.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.floppy.public.plist
launchctl list | grep com.floppy.public     # 動いているか確認
```

- 停止するとき: `launchctl unload ~/Library/LaunchAgents/com.floppy.public.plist`
- ログ: `logs/launchd.log` / `logs/tunnel.log` / `logs/gateway.log`

> ポイント: この plist には `AbandonProcessGroup=true` が必要です。無いと
> `ensure` が起動した API / ゲートウェイ / トンネルが、ジョブ終了時に巻き添えで
> 停止してしまいます。

### 死活監視

```bash
./tools/healthcheck.sh              # 0 = 正常 / 1 = 異常（ローカル API）
./tools/healthcheck.sh --restart    # 異常時に FLOPPY_RESTART_CMD を実行

# 公開 URL も含めて確認する
./tools/healthcheck.sh https://fdd.wawa-app.me/floppy.io/api/health
./tools/public.sh status
```

`/api/health` は DB 接続・不足テーブル・ディスク残量・稼働時間を返し、異常時は **503** を
返します。外部の監視サービスや cron から叩いてください。

```bash
# 5 分ごとに公開 URL を監視し、落ちていたら公開スタックごと復旧する例
*/5 * * * * cd /path/to/floppy_io && FLOPPY_RESTART_CMD="$PWD/tools/public.sh ensure" ./tools/healthcheck.sh --restart https://fdd.wawa-app.me/floppy.io/api/health >> logs/health.log 2>&1
```

### URL にアクセスできないとき

1. `./tools/public.sh status` — API / ゲートウェイ / トンネル / 公開 URL の 4 点を確認
2. **HTTP 530**（Cloudflare のトンネル未接続）→ `./tools/public.sh start`、`tail -30 logs/tunnel.log`
3. **HTTP 502**（ゲートウェイは動いているが API が死んでいる）→ `tail -30 backend/logs/api.log`
4. `host fdd.wawa-app.me` が **NXDOMAIN** → DNS レコードが消えている（サーバー側は正常）。
   次のどちらかで復旧する:
   ```bash
   # A. コマンドで作り直す（CNAME が別トンネルを向いている場合も上書きされる）
   ./tools/public.sh setup

   # B. Cloudflare ダッシュボード → wawa-app.me → DNS → fdd の CNAME を
   #    ~/.cloudflared/floppy.yml のトンネル (tunnel: floppy) に向け直す
   ```
5. `tail -50 backend/logs/api.log` / `mysqladmin -u floppy -p ping` — アプリ / DB の確認

> 実例: `fdd.wawa-app.me` が **NXDOMAIN** になり公開サイトが見えなくなりました。
> ドメイン本体 `wawa-app.me` は 200 を返していたため「アプリではなく DNS」と切り分け、
> `./tools/public.sh setup` でトンネルと CNAME を作り直して復旧しました。
> なお `cloudflared tunnel route dns` は `--config` を省くと既定の
> `~/.cloudflared/config.yml` を読むため、**別トンネル向けの CNAME** が作られることがあります
> （`setup` は `--config` を明示して回避しています）。

## 画面と URL（履歴モード）

| パス | 画面 |
| --- | --- |
| `/` | ホーム（タイムライン＋投稿フォーム） |
| `/disks` | ディスク一覧（コミュニティの検索・作成・参加中） |
| `/d/:slug` | ディスク個別（説明・参加・専用の投稿フォーム・書き込み一覧） |
| `/following` | フォロー中タイムライン（自分＋フォロー中ユーザーの投稿・要ログイン） |
| `/search?q=...` | 検索（入力中にユーザー / ディスク / 投稿のサジェスト、本文・ユーザー名・表示名の部分一致） |
| `/u/:username` | プロフィール（投稿タブと、本人だけに表示する非公開のいいね履歴） |
| `/u/:username/following` / `/u/:username/followers` | フォロー中・フォロワーの独立した専用一覧（一覧内のタブはなし・投稿へ戻るリンクあり） |
| `/p/:id` | 投稿の個別ビュー（旧 Twitter / mixi 風）＋返信（投稿者が許可したときだけ） |
| `/settings` | 設定（表示名 / bio / 32×32 アイコン / 返信の可否 / パスワード変更 / ログアウト） |
| `/help` | ヘルプ |
| `/login` / `/register` | ログイン / 新規登録 |

`#/p/12` のような**旧ハッシュURLは自動で `/p/12` にリダイレクト**されます
（`frontend/app/plugins/legacy-hash.client.js`）。

履歴モードのため、静的配信側で**未知パスを `index.html` にフォールバック**する設定が
必要です。このリポジトリの公開ゲートウェイ（`tools/public_gateway.py`）は対応済みで、
Apache 用の `.htaccess` にもリライトを同梱しています。

## アカウント

- 新規登録・ログイン・ログアウトに対応。投稿・削除は**ログイン必須**で、
  投稿はユーザーごとに分離されます。
- パスワードは bcryptでハッシュ化して保存します。
- 認証は **Bearer トークン**方式（`localStorage` に保持）です。Cookie を使わないため、
  別オリジン（静的配信サーバーなど）からでもそのまま動きます。
- プロフィールアイコンは **設定 → プロフィールアイコン（32×32 ドット絵）** で描くか、
  **設定 → プロフィール画像** から画像に変更できます。表示の優先順位は
  **32×32 アイコン → プロフィール画像 → 最新投稿のドット絵 → 初期アイコン** です。
- 自分のプロフィール画面（`/u/:username`）の **「プロフィールを編集」** からも、
  表示名 / bio / プロフィール画像 / 32×32 アイコンをその場で編集できます
  （保存するとプロフィール表示とサイドバーが更新されます）。
- デモアカウント: ユーザー名 `floppy` / パスワード `floppy`

## プロフィール画像

- 設定ページの「画像を選ぶ」から JPEG / PNG / GIF / WebP をアップロードできます（1.44MB 以内）。
- 実ファイルは投稿画像と同じ `backend/uploads/` に保存し、`users.avatar_path` などに記録します。
- 置き換え・削除のときは古いファイルも削除します。
- プロフィール画像は**投稿の容量制限（1 投稿 1.44MB）とは別枠**です。

## プロフィールアイコン（32×32 ドット絵）

- 設定ページの「32×32 アイコンを描く」から、**32×32 のドット絵アイコン**を描いて保存できます。
- 1 マス = 1 桁の 16 進文字（0-9A-F、16 色）で `users.icon_pixel` に
  **1024 文字**として保存します。全消去（全透明）で保存すると未設定に戻ります。
- 設定するとプロフィール画像より優先されます。未設定のときは
  「プロフィール画像 → 最新投稿のドット絵 → 初期アイコン」の順に使われます。
- 初期アイコンはサイトのロゴと同じ配色（深緑 × クリーム × 紙）のフロッピーです。
  `/api/icon/:username.svg` は未設定でも **404 にせずこの SVG を返す**ため、
  投稿カードやフォロー一覧が文字だけのフォールバックになることはありません。
  画面側（`drawDefaultAvatar`）も同じ絵を canvas に描きます。
- 画像ファイルと同様、投稿の容量制限（1 投稿 1.44MB）とは別枠です。

## 返信（リプライ）

- 各投稿の「↩ 返信」から、その投稿への返信を書けます（返信はテキストのみ）。
- **返信は既定でオフ（返信を受け付けない）** です。設定ページの「返信」で
  「返信を受け付ける」をオンにしたユーザーの投稿だけに返信できます。
  オフのままの投稿に返信しようとすると API は **403** を返します。
- 返信も 1 投稿として `posts` に保存します（容量は 1.44MB の制限対象）。
  `posts.reply_to_id` に**スレッドのルート投稿 ID** を保持するフラットなスレッドです。
  返信への返信も同じスレッドにまとまります。
- タイムライン / 検索 / ディスクには通常投稿だけを表示し、返信は
  共有ページ（`/p/:id`）のスレッドに表示します。プロフィールには返信も表示し、
  `RE: #ID` のリンクが付きます。
- ルート投稿を削除すると、そのスレッドの返信もまとめて削除します
  （添付ファイルも削除）。返信の削除は自分の投稿のみ可能です。

## YouTube 埋め込み

本文に YouTube の URL が含まれていると、自動で埋め込み表示になります。
対応形式: `youtube.com/watch?v=` / `youtu.be/` / `youtube.com/embed/` / `youtube.com/shorts/`。

- 動画 ID は URL から抜き出すので、**API キーが無くても埋め込みは動作します**
  （サムネイルは `i.ytimg.com` の固定 URL、タイトルは表示されません）。
- **YouTube Data API v3** の API キーを設定すると、`videos.list` から動画タイトルと
  サムネイルを取得して保存します。

## API 一覧

| メソッド | エンドポイント | 説明 |
| --- | --- | --- |
| `POST` | `/api/register` | 新規登録 `{ username, password, display_name? }` |
| `POST` | `/api/login` | ログイン `{ username, password }` |
| `POST` | `/api/logout` | ログアウト（要ログイン） |
| `GET`  | `/api/me` | ログイン中ユーザー（要ログイン） |
| `POST` | `/api/update_profile` | 表示名 / bio 更新（要ログイン） |
| `POST` | `/api/update_avatar` | プロフィール画像の設定 / 削除（要ログイン・multipart） |
| `POST` | `/api/update_icon_pixel` | 32×32 ドット絵アイコンの設定 / 削除 `{ pixel_data }`（要ログイン） |
| `POST` | `/api/update_reply_setting` | 返信の受け付けオン / オフ `{ allow_replies }`（要ログイン） |
| `POST` | `/api/change_password` | パスワード変更（要ログイン） |
| `GET`  | `/api/user?username=floppy` | プロフィール＋その人の投稿 |
| `GET`  | `/api/icon/:username.svg` | 投稿カード用アバター（32×32 アイコン → プロフィール画像へ 302 → 最新の正方形ドット絵 → 初期アイコン。未設定でも 200） |
| `GET`  | `/api/search/suggest?q=flo` | 検索サジェスト（ユーザー最大5 / ディスク最大5 / 投稿最大3） |
| `GET`  | `/api/posts[?username=floppy][&q=キーワード][&disk=retro-pc]` | 投稿一覧（新しい順 / 検索 / ディスク絞り込み） |
| `GET`  | `/api/posts?feed=following` | フォロー中タイムライン＝自分＋フォロー中ユーザーの投稿（要ログイン） |
| `POST` | `/api/posts` | 新規投稿 `{ text, pixel_data, pixel_width?, pixel_height?, reply_to_id?, disk_id? }` / `multipart/form-data`（`image` `floppy` 添付可・要ログイン） |
| `GET`  | `/api/disks[?filter=joined][&q=キーワード]` | ディスク一覧（`filter=joined` は参加中のみ・要ログイン） |
| `GET`  | `/api/disks/:slug` | ディスク 1 件とその書き込み一覧 |
| `POST` | `/api/disks` | ディスク作成 `{ name, slug, description }`（要ログイン・作成者は自動参加） |
| `POST` | `/api/disks/join` | ディスクへの参加 / 退出 `{ slug }` または `{ id }`（要ログイン・トグル） |
| `GET`  | `/api/thread?id=123` | 投稿 1 件とスレッド（返信一覧） |
| `POST` | `/api/delete_post` | 自分の投稿を削除 `{ id }`（要ログイン） |
| `POST` | `/api/like` | いいねの付け外し `{ id }`（要ログイン・トグル） |
| `POST` | `/api/follow` | フォローの付け外し `{ username }` または `{ id }`（要ログイン・トグル） |
| `GET` | `/api/users/:username/likes?offset=0` | 本人専用のいいね履歴。認証必須・所有者一致必須・private, no-store。50 件ずつ取得 |
| `GET` | `/api/users/:username/connections/:kind?offset=0` | 公開フォロー一覧。kind は following / followers。50 件ずつ、users と next_offset を返す |
| `GET`  | `/api/disk_usage[?username=floppy]` | 1 投稿あたりの上限 / 合計（参考値） |
| `GET`  | `/api/preview?id=123` | 埋め込み用プレビュー（メタ情報＋HTML スニペット） |

## 容量の考え方

- **1 投稿 = フロッピー 1 枚**。1 投稿の合計（本文 + ドット絵 + 画像 + フロッピー）が
  1.44MB を超えると 403 で拒否されます。累計では制限しません。
- 投稿フォームの `DISK (C:)` は、**いま書いている投稿**の容量統計（使用バイト数 /
  上限 / 使用率）を表示します。残量は表示しません。
- ドット絵はキャンバスに応じて 256 / 768 / 1,024 バイト（未描画でも消費）。
  本文は UTF-8 のバイト数で数えます。日本語の多くは 1 文字 3 バイト、
  絵文字などはそれ以上になる場合があります。
- **画像も容量に含まれます**。画像は縮小せず実ファイルのまま `backend/uploads/` に保存し、
  そのバイト数を 1 投稿の合計に加算します。つまり写真 1 枚で 1.44MB をほぼ使い切ります。
- **YouTube の埋め込みは容量に含まれません**（本文中の URL 文字列だけが本文バイト数として
  カウントされます）。保存するのは動画 ID・タイトル・サムネイル URL のメタ情報のみです。
- プロフィール画像も投稿の容量制限とは別枠です。
- 保存済みの全投稿の合計は `GET /api/disk_usage` の `total_bytes` で確認できます
  （参考値・制限対象ではありません）。

## フロッピーファイル投稿

- 投稿に**ファイルを添付**できます（投稿フォームの「💾 フロッピーを添付」）。
- ファイルはそのまま `backend/uploads/` に保存し、**バイト数を 1 投稿の容量（1.44MB）
  に加算**します。つまり 1.44MB のフロッピーイメージなら 1 投稿をほぼ使い切ります。
- 実体は実行されないよう常に `.bin` として保存し、元のファイル名は DB に保持して
  投稿カードの「💾 ファイル名 / n bytes をダウンロード」からダウンロードできます。
- 投稿を削除すると添付ファイルも削除されます。
- **音声ファイル（mp3 / wav / ogg / opus / m4a / aac / flac / weba）はプレビューで
  再生できます**。8bit 曲などを書き出して投稿すると、投稿カードと共有カード
  （プレビュー API が返す HTML）にプレイヤーが表示されます。
- 音声は元の拡張子のまま（正しい Content-Type で）配信し、それ以外のファイルは
  実行されないよう `.bin` として保存します。

## アスキーアートスタンプ

投稿フォームの **`[AA] スタンプ`** から、顔文字・BBS 風・フレーム・ドットの
アスキーアートをワンクリックでカーソル位置に挿入できます。

- プリセット: よく使う / 顔文字 / BBS / フレーム / ドット / 自作
- **検索欄**で今のタブのスタンプを絞り込めます（例: `枠`, `猫`, `お祝い`）
- **よく使う**: 直近に挿入したスタンプを最大 12 件、新しい順に自動で並べます
  （localStorage キー: `floppy_aa_recent_v1`）。よく使うタブ以外でも
  「最近使った」として直近 6 件をワンタップで再利用できます
- 自作スタンプは **ブラウザの localStorage**（キー: `floppy_aa_stamps_v1`）に保存
- 保存できる自作スタンプは **最大 50 件 / 1 件 300 文字**
- 保存先は端末・ブラウザごとで、**サーバーには送信されません**
- 自作タブの `×` で削除できます

> 複数行の AA は前後に改行、1 行の顔文字は前後に半角スペースを補って挿入します。

## ドット絵エディタ

投稿フォームの「ドット絵を描く」で、Miiverse 風のツールバー付きエディタが開きます。

- **キャンバス切替**: 正方形（32×32）/ Miiverse（32×24・4:3）/ クラシック（16×16）。
  切り替え時は絵の中央を基準にコピーし、はみ出た部分だけを切り取ります（undo 可能）
- **もどる / すすむ**: 描画・消去・全消去・キャンバス切替を履歴から戻す / やり直す
  （`⌘/Ctrl + Z`、`⌘/Ctrl + Shift + Z` / `Ctrl + Y` でも操作可）
- **ペン / 消しゴム / グリッド / 全消去**: 消しゴムは右クリックまたは `Alt` + ドラッグでも使えます
- 16 色パレット、現在色のインジケータ、ドット数表示
- 描画結果は 16 進文字列として `posts.pixel_data` に、キャンバスは
  `posts.pixel_width` / `pixel_height` に保存します

## 検索

- `/search` の入力欄に文字を入れると、**180ms のデバウンス**で候補を取得します。
- 候補は **ユーザー / ディスク / 投稿** の 3 種類です。
  - ユーザー: `@username` / 表示名の部分一致（最大 5 件）
  - ディスク: 名前 / slug / 説明の部分一致（最大 5 件）
  - 投稿: 本文 / ユーザー名 / 表示名の部分一致（最大 3 件・本文は 120 文字で切り詰め）
- 候補の先頭には常に「**このキーワードで検索**」があり、Enter で通常の検索結果へ移動します。
- キーボード操作: `↑` / `↓` で選択、`Enter` で決定、`Esc` で閉じる。
  `aria-activedescendant` を使ったコンボボックスとして実装しています。
- ユーザーを選ぶと `/u/:username`、ディスクを選ぶと `/d/:slug`、投稿を選ぶと `/p/:id` を開きます。
- 候補の取得は `GET /api/search/suggest?q=...`。入力が変わったら古いレスポンスは破棄します。

## 投稿の個別ビュー

- タイムライン / 検索 / プロフィールの**投稿カードをクリック**すると `/p/:id` を開きます。
  いいね・共有・リンク・メディア操作などの部分は従来どおりその場で動きます。
- 個別ビューは**旧 Twitter / mixi を参考にしたシンプルな 1 枚**です。
  - 投稿者（アバター / 表示名 / @username）
  - 本文、YouTube（クリックで再生）・画像・ドット絵・添付ファイル
  - `No.` / 投稿日時 / ディスク / バイト数
  - いいね・返信・共有・プロフィール・削除（自分の投稿のみ）
- 動画や画像がある投稿では、そのメディアを主役にします。**ドット絵だけの投稿**は
  ドット絵を大きく表示します。
- **返信は投稿者が許可したときだけ表示**します（既定はオフ）。有効な場合は返信フォームと、
  mixi 風のコメント行（アバター＋名前＋本文＋共感）が並びます。
- パンくず（`タイムライン / No.12`）から戻れます。

## 共有

- 各投稿の「↗ 共有」、または共有ページ（`/p/:id`）の「↗ 共有」を押すと、
  **サイトの投稿カードと同じ配色（生成り×ミント×ドット枠）**の共有ダイアログが開きます。
- カードは全サイト共通のデザインです。ミントのヘッダー（`FLOPPY.IO / SHARED POST` と
  `No.`）、投稿のドット絵アバター、表示名・`@username`・`[D] ディスク`、投稿日時・
  バイト数、種別バッジ（YOUTUBE / IMAGE / PIXEL / TEXT）、本文、メディア
  （YouTube / 画像 / ドット絵）、いいね・返信数・「投稿を開く」を 1 枚にまとめます。
  カード自体を押すと `/p/:id` が開きます。
- 本文中の URL はサイトのリンク色（青）で、スキームを省略して表示します。
- 共有先は **X でポスト**、**LINE で送る**、**リンクをコピー**。
  Web Share API に対応した端末では **共有メニュー**（iOS / Android の共有シート）も
  表示されます。
- X の共有文は **サイト本体の URL（`/p/:id`）を先頭**にし、本文中の外部 URL
  （YouTube など）は取り除きます。YouTube のカードではなく、floppy.io の
  共有カードが表示されるようにするためです。
- 共有 URL は `app.baseURL` を考慮して組み立てるため、サブディレクトリ配信
  （`/floppy.io/`）でも `/floppy.io/p/:id` のように正しいリンクになります。
- **埋め込み HTML** は `/api/preview` が自己完結型のスニペットとして生成します。
  ダイアログのプレビューと同じサイト配色のカードを、インライン CSS だけで組み立てます
  （Notion やブログに貼り付け可能）。本文 URL はリンク化し、ドット絵が無い投稿は
  フロッピーのドット絵にフォールバックします。取得に失敗したときは再試行できます。

## ディスク（コミュニティ）

**フロッピー 1 枚 = 1 コミュニティ** として、同じ趣味の書き込みを集める「ディスク」です。
ホームの「タイムライン / フォロー中」に並ぶ第三の導線として残しています。

- `/disks` で全ディスクを一覧・検索できます。ログイン中は「参加中」タブで自分が
  参加しているディスクだけを表示できます。
- ディスクは **名前 / ディスク ID (slug) / 説明** で作成します（要ログイン・作成者は自動参加）。
- `/d/:slug` でディスクを開くと、説明・参加者数・最終書き込み・書き込み一覧を表示します。
- 書き込み（投稿）には **ログイン + そのディスクへの参加** が必要です。
  参加するとディスク専用の投稿フォームが出ます。
- 書き込み先は `posts.disk_id` に保存されます。投稿カードには `[D] ディスク名` の
  バッジが付き、ホームのタイムラインにも流れます。
- フォロー機能とフォロー中タイムライン（`/following`）は従来どおり利用できます。

既存 DB へは次のマイグレーションを 1 回適用してください
（`disks` / `disk_members` と `posts.disk_id` が追加されます）。

```bash
mysql -u root -p < database/migrations/2026-11-06-disks.sql
```

## いいね

- 各投稿に「♡ いいね」ボタンがあります。クリックで付け外し（トグル）できます。
- いいねにはログインが必要です。未ログインで押すと案内が表示されます。
- 件数は誰でも見えますが、押したかどうかはユーザーごとに表示されます。
- `likes` テーブルに保存し、投稿が削除されると連動して消えます
  （1 ユーザー 1 投稿につき 1 件）。

### いいね履歴（本人専用）

- プロフィールは「投稿」タブが既定で、その横に「いいね履歴（非公開）」を本人にだけ表示します。
- `?tab=likes` で開き、いいねした日時の新しい順に 50 件ずつ取得します。解除した投稿は履歴から消えます。
- 履歴の一覧・件数は公開プロフィール API に含めません。未ログインは 401、他人の履歴は 403 を返します。
- 履歴 API は `Cache-Control: private, no-store`。ログアウト・プロフィール移動時は画面の履歴を破棄します。
- 投稿のいいね合計件数は従来どおり公開されます。誰がいいねしたかを公開する一覧はありません。

## フォロー

- プロフィールの「フォローする」を押すと**フォローの付け外し（トグル）**ができます。
  フォロー中はボタンが「フォロー中」に変わります（自分自身にはボタンを出しません）。
- 投稿・プロフィールに**フォロー数 / フォロワー数**を表示します。
- プロフィールと左サイドバーの「フォロー中」「フォロワー」をクリックすると専用のユーザー一覧へ移動します。
  一覧は未ログインでも閲覧でき、相手のプロフィールへ移動できます。ログイン中は一覧内で
  フォローの付け外しも可能です。50 件ずつ追加表示し、Twitter と同じく `/u/:username/following`（フォロー中）と `/u/:username/followers`（フォロワー）を独立した画面として表示します。一覧の中にタブは置かず、プロフィールの件数リンクで行き来し、一覧からは「投稿へ戻る」でプロフィールへ戻ります。旧 `tab` / `connections` の一覧リンクも専用画面へ転送します。
- `follows` テーブル（`follower_id` → `followee_id`）に保存し、どちらかのユーザーが
  消えると連動して消えます（1 組 1 件・自分自身は登録できません）。
- ホームの「フォロー中」タブ（`/following`）は**自分＋フォロー中ユーザーの投稿**を
  新しい順に表示します。ログインが必要です。
- ホームのタブは「タイムライン / フォロー中 / ディスク」の 3 つです。

## 画像投稿

- 投稿フォームの「🖼 画像を添付」から JPEG / PNG / GIF / WebP を選べます。
- 画像は**そのまま** `backend/uploads/` に保存し、`image_path` / `image_bytes` /
  `image_width` / `image_height` を `posts` に記録します。
- 画像のバイト数も 1 投稿の容量（1.44MB）に含まれます。超える場合は 403 で拒否され、
  保存済みの一時ファイルも破棄されます。
- 投稿を削除（フォーマット）すると画像ファイルも削除されます。
- 公開 URL は `FLOPPY_PUBLIC_BASE_URL` を考慮した絶対パス
  （例: `/floppy.io/uploads/<ファイル名>`）で、API のレスポンスに `image_url` として
  含まれます。`/u/name` や `/p/12` のような深いパスでも画像が壊れません。
- DB に記録はあるが実ファイルが無い場合、API は `image_url` / `avatar_url` を
  `null` で返します。画像は表示せず、アバターはドット絵のフォールバックになります。

## モバイル

- 幅 700px 以下で 1 カラム化し、ナビはハンバーガーで開閉します。開いたメニューは
  トップバーの下に**重ねて**表示するので、開閉してもメインの位置はずれません
  （メニュー以外をタップすると閉じます）。
- **入力欄は 16px 以上**に統一しています（iOS Safari は 16px 未満の入力欄に
  フォーカスすると自動で画面を拡大してしまうため）。
- タップ領域を広げています（いいね / 共有 36px、⋯ 34px、色パレット 30px、
  ダイアログの × 40px）。
- 画面より縦に長いダイアログはスクロールできます。
- 添付した画像・YouTube・音声プレイヤーは画面幅に収まります。

## セキュリティ

詳細なポリシー・報告方法・本番チェックリストは **[SECURITY.md](../SECURITY.md)** にまとめています。
実装上の要点は次のとおりです。

| 領域 | 対策 |
| --- | --- |
| パスワード | bcrypt（cost 12）。`$2y$` の旧ハッシュも検証可能 |
| API トークン | 256bit 乱数。DB には SHA-256 で保存（旧平文トークンは自動移行） |
| 認可 | 投稿削除は本人のみ / 設定・アバターは本人のみ / 自分フォロー禁止 |
| SQL | 全クエリでプレースホルダ。`LIKE` の `% _ \` をエスケープ |
| XSS | Vue の自動エスケープ。プレビュー HTML は `html.escape`。`v-html` 不使用 |
| アップロード | マジックバイト判定 / 1.44MB 制限 / ランダム名 / `.bin` 強制 / `nosniff` |
| 乱用対策 | ログイン 10 回/分/IP、登録 5 回/5 分/IP、ボディ上限、一覧 200 件 |
| CSRF | Cookie を使わず Bearer ヘッダのみ。Cookie ベースの CSRF は成立しない |
| ヘッダー | CSP / HSTS / `X-Frame-Options: DENY` / `Referrer-Policy` など |
| トークン期限 | `FLOPPY_TOKEN_TTL_DAYS`（本番 30 日推奨） |
| API ドキュメント | 既定で無効（`FLOPPY_API_DOCS=1` で開発時のみ有効） |

### コピー抑止

サイト上の文章・画像・ドット絵は、テキスト選択・右クリック・ドラッグ・
コピー / カットを抑止しています。入力欄・共有リンク・埋め込みコードは
通常どおりコピーできます。

> これはカジュアルなコピーを減らすための **deterrence** であり、完全な
> コピー防止ではありません。HTML ソース、開発者ツール、スクリーンショット、
> API からの直接取得までは防げません。詳細は [SECURITY.md](../SECURITY.md) を参照してください。

### 本番で必ず行うこと

- HTTPS で公開し、HSTS を有効にする
- `backend/.env` の DB 資格情報を強い値に変更し、`chmod 600` にする
- `FLOPPY_API_DOCS=0` / `FLOPPY_TOKEN_TTL_DAYS=30` / `FLOPPY_CORS_ORIGINS` を設定する
- `/api` と `/uploads` だけを FastAPI にプロキシし、`backend/uploads/` を公開しない
- `pip install --upgrade -r requirements.txt` と `npm audit` を定期実行する

## 設計メモ / 拡張ポイント

- **認証**: Bearer トークン方式。`api_tokens` テーブルに **SHA-256 ハッシュ**を保存し、
  `backend/app/security.py` の `current_user()` / `require_user()` で判定します。
  投稿は `posts.user_id` でユーザーごとに分離されています。
  - Cookie を使わないので、クロスオリジンでも動きます
    （本番では `FLOPPY_CORS_ORIGINS` を公開オリジンに限定してください）。
  - 旧 PHP 版の平文トークンは、初回利用時にハッシュへ自動移行します。
- **ルーティング**: Nuxt 4 の履歴モードを使い、`/u/name` / `/p/12` のような
  通常の URL で表示します。静的配信側では未知パスを `index.html` に
  フォールバックさせてください（`tools/public_gateway.py` は対応済み）。
  旧 `#/...` URL はクライアント側で自動的にパスへ変換します。
- **容量計算**: `posts.total_bytes` に投稿時の値を保存しているため、1 投稿の容量判定は
  投稿時に確定します（本文を再計算する必要はありません）。累計が必要な場合は
  `SUM(total_bytes)` で求まります。
- **ドット絵パレット**: `backend/app/utils/pixels.py` の `PIXEL_PALETTE` と
  `frontend/app/utils/pixel.js` の `PALETTE` は一致させてください。

## 注意

- 本リポジトリはオープンソースではありません。ライセンスがない限り、
  再配布・商用利用・公開ミラーへの転載は許可されません。
- セットアップ手順はこのドキュメントと [SECURITY.md](../SECURITY.md) に記載しています。
  本番の秘密情報（DB パスワード、API キー、トークン）はリポジトリに含めていません。
- 画面上のコピー抑止はカジュアルな転載を減らすためのもので、完全な防御ではありません。
- 公開サーバーとして運用する場合は、[SECURITY.md](../SECURITY.md) のチェックリストを
  実施した上で自己責任でお願いします。
