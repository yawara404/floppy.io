# floppy.io

**1.44MB しか使えない静寂のレトロ SNS**

「現代の Web はリソースを消費しすぎている」というアンチテーゼから生まれた、レトロ
コンピューティング趣味全開のミニマル SNS。**1 投稿あたり**の容量上限はフロッピー
ディスク 1 枚分 (**1.44MB = 1,474,560 Bytes**) で、1 投稿＝フロッピー 1 枚という
イメージ。テキスト投稿と超軽量なドット絵だけを許可し、1 投稿の合計が 1.44MB を
超えるものは投稿できません（累計は制限しません）。

画面は 2008〜2010 年頃の Twitter 風（水色のトップバー・左のプロフィール欄・白い
タイムライン・青リンク）。ドット絵アイコンと 💾 ロゴで floppy.io らしさを残しています。
モバイル（幅 700px 以下）では 1 カラムに切り替え、ナビはハンバーガーメニューに格納、
プロフィールを横並びのコンパクト表示に、投稿ボタンを全幅にするなど最適化しています。

---

## 公開

| 種類 | URL |
| --- | --- |
| 公開サイト（Cloudflare Tunnel） | `<公開ホスト>/floppy.io/` |
| ローカル（MAMP PRO） | <http://floppy.io:8080/> |
| ローカル（Live Server） | <http://localhost:5500/> |
| DB 管理（Adminer） | <http://floppy.io:8080/floppy_io/db/> |

Cloudflare Tunnel は `<公開ホスト>` の Host を保ったまま `localhost:8888` へ
転送するため、Apache の `<公開ホスト>` vhost 内で `/floppy.io/` を配信しています。
実体は `~/Quadtecho/floppy.io/` からのシンボリックリンクです（設定変更なしで公開できる）。

```text
~/Quadtecho/floppy.io/
├── index.html, assets/, config.js, favicon.png  -> frontend/dist へのリンク
├── api      -> backend/api
└── uploads  -> backend/uploads
```

## 技術スタック

| レイヤー | 技術 |
| --- | --- |
| フロントエンド | Vue 3 (Composition API, `<script setup>`) + Vite |
| スタイル | 昔の Twitter 風カスタム CSS（水色トップバー・青リンク・白いカード） |
| 描画 | HTML5 Canvas API（外部描画ライブラリ不使用） |
| バックエンド | PHP 8.x（RESTful JSON API、PDO Prepared Statements） |
| データベース | MySQL 8.x（`utf8mb4`） |

## コア仕様

- **容量制限（1 投稿あたり）**: 投稿時に本文の UTF-8 バイト長 (`strlen($text)`) と
  ドット絵データのバイト長を合算し、**その投稿の合計**が `1,474,560 Bytes` を超える
  場合は HTTP **403** で弾く。累計では制限しない。
- **ドット絵の超軽量データ化**: 16×16（計 256 マス）。画像ファイルには変換せず、
  「カラーコードのインデックス配列」を **16 進数 256 文字（= 256 バイト）** の文字列
  として DB に保存する。各文字 `0-9A-F` が 16 色パレットの 1 色に対応。

## ディレクトリ構成

```text
floppy_io/
├── backend/
│   ├── config/
│   │   ├── database.php        # MySQL PDO 接続 & 共通ヘルパー / 認証ヘルパー
│   │   └── youtube.php         # YouTube Data API v3 連携 (API キー設定)
│   └── api/
│       ├── .htaccess           # Authorization ヘッダを PHP に渡す (CGIPassAuth)
│       ├── register.php        # ユーザー登録（トークン発行）
│       ├── login.php           # ログイン（トークン発行）
│       ├── logout.php          # ログアウト（トークン無効化）
│       ├── me.php              # ログイン中ユーザー取得
│       ├── update_profile.php  # 表示名 / bio の更新
│       ├── update_avatar.php   # プロフィール画像の設定 / 削除
│       ├── change_password.php # パスワード変更
│       ├── user.php            # プロフィール＋そのユーザーの投稿一覧
│       ├── posts.php           # 投稿一覧取得・新規投稿（容量判定 / 要ログイン）
│       ├── delete_post.php     # 投稿削除（自分のみ）
│       ├── disk_usage.php      # 容量の参考値取得
│       └── preview.php         # エコシステム連携用プレビュー API
│   └── uploads/                # アップロードされた画像の実ファイル置き場
│   └── tools/
│       └── backfill_youtube.php # 既存投稿の YouTube メタ情報を後から取得
├── database/
│   └── schema.sql              # MySQL DDL（＋デモユーザー投入）
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ProfileCard.vue     # 左カラムのプロフィール（ドット絵アイコン＋統計）
│   │   │   ├── Composer.vue        # 投稿フォーム（容量メーター＋画像添付）
│   │   │   ├── PostList.vue        # 投稿一覧＋削除＋埋め込みプレビュー
│   │   │   ├── DiskGauge.vue       # この投稿の容量統計（使用量 / 上限 / 使用率）
│   │   │   ├── PixelEditor.vue     # 16×16 ドット絵 Canvas エディタ
│   │   │   ├── PostItem.vue        # 投稿カード（ドット絵＋本文＋消費バイト数）
│   │   │   └── FloppyCard.vue      # エコシステム用埋め込みプレビューカード
│   │   ├── store/
│   │   │   └── auth.js             # ログイン状態（トークンを localStorage に保持）
│   │   ├── utils/
│   │   │   ├── api.js              # API クライアント（Bearer トークン付与）
│   │   │   ├── router.js           # 依存なしのハッシュルーター
│   │   │   └── pixel.js            # ドット絵のパース/描画ユーティリティ
│   │   ├── views/
│   │   │   ├── Home.vue            # ホーム（タイムライン＋投稿フォーム）
│   │   │   ├── Search.vue          # 検索（#/search?q=...）
│   │   │   ├── Profile.vue         # プロフィール（#/u/username）
│   │   │   ├── Settings.vue        # 設定（表示名・bio・パスワード・ログアウト）
│   │   │   ├── Help.vue            # ヘルプ
│   │   │   └── Auth.vue            # ログイン / 新規登録
│   │   ├── App.vue                 # トップバー（ロゴ＋ナビ）＋ 2 カラム
│   │   ├── main.js
│   │   └── style.css               # 昔の Twitter 風テーマ
│   ├── public/
│   │   ├── config.js               # 実行時 API 接続先 (MAMP / Live Server 切替)
│   │   └── favicon.png             # 💾 をファビコン化したもの
│   ├── index.html
│   ├── vite.config.js              # 開発時 /api → :8000 プロキシ / 相対パス出力
│   └── package.json
└── README.md
```

## 画面と URL（ハッシュルーティング）

| パス | 画面 |
| --- | --- |
| `#/` | ホーム（タイムライン＋投稿フォーム） |
| `#/search?q=...` | 検索（本文・ユーザー名・表示名の部分一致） |
| `#/u/:username` | プロフィール（自分・他ユーザーどちらも） |
| `#/settings` | 設定（表示名 / bio / パスワード変更 / ログアウト） |
| `#/help` | ヘルプ |
| `#/login` / `#/register` | ログイン / 新規登録 |

サーバー側のリライトが不要なハッシュ方式なので、MAMP の静的配信でも
Live Server でもそのまま動きます。

## アカウント

- 新規登録・ログイン・ログアウトに対応。投稿・削除は**ログイン必須**で、
  投稿はユーザーごとに分離されます。
- パスワードは `password_hash()`（bcrypt）でハッシュ化して保存します。
- 認証は **Bearer トークン**方式（`localStorage` に保持）です。Cookie を使わないため、
  Live Server からのクロスオリジンでもそのまま動きます。
- プロフィールアイコンは **設定 → プロフィール画像** から画像に変更できます
  （未設定のときは、そのユーザーの最新投稿のドット絵 → フロッピーの絵 の順に使われます）。
- デモアカウント: ユーザー名 `floppy` / パスワード `floppy`

## プロフィール画像

- 設定ページの「画像を選ぶ」から JPEG / PNG / GIF / WebP をアップロードできます（1.44MB 以内）。
- 実ファイルは投稿画像と同じ `backend/uploads/` に保存し、`users.avatar_path` などに記録します。
- 置き換え・削除のときは古いファイルも削除します。
- プロフィール画像は**投稿の容量制限（1 投稿 1.44MB）とは別枠**です。

## YouTube 埋め込み

本文に YouTube の URL が含まれていると、自動で埋め込み表示になります。
対応形式: `youtube.com/watch?v=` / `youtu.be/` / `youtube.com/embed/` / `youtube.com/shorts/`。

- 動画 ID は URL から抜き出すので、**API キーが無くても埋め込みは動作します**
  （サムネイルは `i.ytimg.com` の固定 URL、タイトルは表示されません）。
- **YouTube Data API v3** の API キーを設定すると、`videos.list` から動画タイトルと
  サムネイルを取得して保存します。

### API キーの設定

1. [Google Cloud Console](https://console.cloud.google.com/) で「YouTube Data API v3」を有効化
2. API キーを発行
3. 次のいずれかで設定する
   - `backend/config/youtube.php` の `YOUTUBE_API_KEY` に貼り付ける
   - 環境変数 `FLOPPY_YOUTUBE_API_KEY` を設定する（優先されます）

```bash
# 例: PHP 内蔵サーバーで使う場合
FLOPPY_YOUTUBE_API_KEY=AIza... php -S localhost:8000
```

- 取得結果（`youtube_id` / `youtube_title` / `youtube_thumbnail`）は投稿行に保存されます。
- API 呼び出しに失敗しても投稿は成功します（タイトル無しの埋め込みになります）。
- 埋め込みは**クリックするまで iframe を読み込まない**ので、タイムラインは軽いままです。
- **`127.0.0.1` のような IP アドレスで開いたページでは埋め込みを再生できません**
  （YouTube 側の制限で「この動画は再生できません」になります）。`localhost` で開いてください。
  その場合は画面にも案内を表示し、埋め込みの下に「YouTube で見る」リンクも置いています。
- **キーを後から設定した場合**、それ以前の投稿はタイトルが空のままです。次のコマンドで
  まとめて取り直せます。

  ```bash
  php backend/tools/backfill_youtube.php
  ```

## API 一覧

| メソッド | エンドポイント | 説明 |
| --- | --- | --- |
| `POST` | `/api/register.php` | 新規登録 `{ username, password, display_name? }` |
| `POST` | `/api/login.php` | ログイン `{ username, password }` |
| `POST` | `/api/logout.php` | ログアウト（要ログイン） |
| `GET`  | `/api/me.php` | ログイン中ユーザー（要ログイン） |
| `POST` | `/api/update_profile.php` | 表示名 / bio 更新（要ログイン） |
| `POST` | `/api/update_avatar.php` | プロフィール画像の設定 / 削除（要ログイン・multipart） |
| `POST` | `/api/change_password.php` | パスワード変更（要ログイン） |
| `GET`  | `/api/user.php?username=floppy` | プロフィール＋その人の投稿 |
| `GET`  | `/api/posts.php[?username=floppy][&q=キーワード]` | 投稿一覧（新しい順 / 検索） |
| `POST` | `/api/posts.php` | 新規投稿 `{ text, pixel_data }` または `multipart/form-data`（要ログイン / 容量判定） |
| `POST` | `/api/delete_post.php` | 自分の投稿を削除 `{ id }`（要ログイン） |
| `GET`  | `/api/disk_usage.php[?username=floppy]` | 1 投稿あたりの上限 / 合計（参考値） |

| `GET`  | `/api/preview.php?id=123` | 埋め込み用プレビュー（メタ情報＋HTML スニペット） |

## セットアップ

### 0. 前提

- PHP 8.x（PDO MySQL 拡張）
- MySQL 8.x
- Node.js 18+ / npm

---

### A. MAMP で開く（推奨・最短）

MAMP の Apache は `:8888`、MySQL は `:8889`（`root` / `root`）で動いている前提です。

1. **MAMP で Apache と MySQL を起動する**
   - MAMP アプリで「Start Servers」を押す（Apache / MySQL の両方）。

2. **データベースを作成する**

   ```bash
   /Applications/MAMP/Library/bin/mysql80/bin/mysql \
     -u root -proot --socket=/Applications/MAMP/tmp/mysql/mysql.sock \
     < database/schema.sql
   ```

   > コマンドが無い場合は MAMP 同梱の phpMyAdmin から `database/schema.sql` を
   > インポートしても同じです。

3. **Apache に floppy.io の別名を登録する**

   `/Applications/MAMP/conf/apache/httpd.conf` に以下を追記します
   （本リポジトリでは設定済み）。

   ```apache
   Alias /floppy_io/api     ~/floppy_io/backend/api
   Alias /floppy_io/uploads ~/floppy_io/backend/uploads
   Alias /floppy_io         ~/floppy_io/frontend/dist

   <Directory "~/floppy_io">
       Options All
       AllowOverride All
       Require all granted
   </Directory>
   ```

   - フロントは `frontend/dist`（Vite のビルド成果物）を静的配信
   - PHP API は `/floppy_io/api/*` → `backend/api/*`
   - ルートの `/api` は TuneDrop 用プロキシが使用中のため、あえて
     `/floppy_io/api` に置いています。

   変更後は Apache を再起動してください（MAMP アプリの「Stop」→「Start」、
   または `sudo /Applications/MAMP/Library/bin/httpd -f
   /Applications/MAMP/conf/apache/httpd.conf -k restart`）。

4. **フロントをビルドする**

   ```bash
   cd frontend
   npm install
   npm run build
   ```

5. **ブラウザで開く**

   👉 <http://localhost:8888/floppy_io/>

---

### B. MAMP PRO で開く

MAMP PRO は GUI でホスト（バーチャルホスト）を管理するため、無料版のように
`httpd.conf` を直接編集しません。**ホストの設定画面に追記**します。

前提として、MAMP PRO に `floppy.io` というホストを作ってあるものとします
（ホスト名は何でも構いません。変えた場合は `frontend/public/config.js` の
`MAMP_PRO_HOSTS` も合わせて変更して再ビルドしてください）。

#### 1. ホストの DocumentRoot を設定する

**Hosts → `floppy.io` → General**

| 項目 | 値 |
| --- | --- |
| Host name | `floppy.io` |
| Document root | `~/floppy_io/frontend/dist` |

> `frontend/dist` は Vite のビルド成果物です。`npm run build` で生成されます。

#### 2. PHP API と画像の Alias を追加する

**同じホストの Apache タブ →「<VirtualHost> への追加パラメータ」**
（英語 UI では "Additional parameters for `<VirtualHost>`"）に次を追記します。

```apache
Alias /floppy_io/api     ~/floppy_io/backend/api
Alias /floppy_io/uploads ~/floppy_io/backend/uploads

<Directory "~/floppy_io/backend">
    Options Includes FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
```

- `Alias /floppy_io/api` … PHP の API（`backend/api`）を公開
- `Alias /floppy_io/uploads` … アップロード画像（`backend/uploads`）を公開
- `AllowOverride All` … **必須**。`backend/api/.htaccess` の `CGIPassAuth On` が
  効かないと、`Authorization` ヘッダが PHP に届かずログイン（Bearer トークン）が
  動きません。

> **⚠️ `/api` というパスは使えません。**
> MAMP PRO の `httpd-ssl.conf` にはサーバー全体に
> `ProxyPass /api/ http://127.0.0.1:5002/api/`（QuadTecho 用の Flask）が
> 設定されており、**ProxyPass は Alias より優先される**ため、
> `/api` に Alias を張っても Flask に横取りされます。
> そのため `/floppy_io/api` という衝突しないパスを使います。

追記したら **保存 → サーバーを再起動**（MAMP PRO の Stop → Start）。

#### 3. ホスト名を解決させる

MAMP PRO が `/etc/hosts` に `127.0.0.1 floppy.io` を自動で追記します
（管理者パスワードを求められたら許可してください）。

> `floppy.io` は実在するドメインなので、この追記が無いと**本物の公開サイトに
> 飛んでしまいます**。心配な場合は `floppy.local` のようなホスト名に変えるのが
> 安全です。

#### 4. データベースを作成する

MAMP PRO の MySQL は無料版とは**別のデータディレクトリ**を使うため、
`floppy_io` データベースを改めて作成する必要があります。

**方法 A: phpMyAdmin を使う**

1. MAMP PRO のメニューから phpMyAdmin を開く
   （<http://localhost:8888/phpMyAdmin6/>）
2. `root` / `root` でログイン
3. 「インポート」→ `~/floppy_io/database/schema.sql` を選択 → 実行

**方法 B: コマンドライン**

```bash
/Applications/MAMP/Library/bin/mysql80/bin/mysql \
  -u root -proot --socket=/Applications/MAMP/tmp/mysql/mysql.sock \
  < ~/floppy_io/database/schema.sql
```

> MAMP PRO の MySQL は **TCP を無効化している**ことがあります
> （`skip_networking=ON`）。その場合は `-h 127.0.0.1 -P 8889` ではなく
> 上記のように `--socket` を使ってください。

確認：

```bash
/Applications/MAMP/Library/bin/mysql80/bin/mysql -u root -proot \
  --socket=/Applications/MAMP/tmp/mysql/mysql.sock \
  -e "USE floppy_io; SHOW TABLES; SELECT id, username FROM users;"
```

`users` / `posts` / `api_tokens` とデモユーザー `floppy` が見えれば OK です。

> アプリ側（`backend/config/database.php`）は **unix ソケット → TCP の順に試す**ので、
> TCP が無効でも追加設定なしで接続できます。

#### 5. フロントをビルドする

```bash
cd frontend
npm install
npm run build
```

> `frontend/public/config.js` を書き換えた場合も、この再ビルドが必要です。

#### 6. ブラウザで開く

👉 **<https://floppy.io:8890/>**

- MAMP PRO は既定で **HTTP(8888) → HTTPS(8890) にリダイレクト**します。
- 自己署名証明書の警告が出たら「詳細設定」→「アクセスする」で進んでください。
- 警告を消したい場合はホストの **SSL チェックを外す**と `http://floppy.io:8888/`
  で開けます（その場合は `config.js` の変更は不要です。ホスト名で判定しています）。

#### 7. 動作確認チェックリスト

| 確認 | 期待する結果 |
| --- | --- |
| `https://floppy.io:8890/` | サイトが表示される |
| `https://floppy.io:8890/floppy_io/api/posts.php` | `{"posts":[...]}` が返る |
| `https://floppy.io:8890/floppy_io/uploads/` | 403（Alias が効いていれば 404 ではなく 403） |
| `floppy` / `floppy` でログイン | 成功する |
| 投稿・画像添付 | できる |
| YouTube 埋め込み | 再生できる（IP アドレスではないため） |

#### 8. つまずきポイント

| 症状 | 原因と対処 |
| --- | --- |
| `/floppy_io/api/posts.php` が **404** | Alias 未設定、または保存後の再起動忘れ |
| `/api/posts.php` が **Flask の 404** を返す | MAMP PRO の ProxyPass に横取りされている。`/floppy_io/api` を使う |
| API が **HTML のエラー**を返す | DB 未作成。手順 4 を実施 |
| ログインが **401** になる | `<Directory>` の `AllowOverride All` 忘れ（`.htaccess` が効いていない） |
| **403 Forbidden** | DocumentRoot が `frontend/dist` になっていない |
| 「この動画は再生できません」 | `127.0.0.1` でアクセスしている。`floppy.io` で開く |
| 8888 が繋がらない | **無料版 MAMP と同時起動している**。無料版を Stop する |

> **無料版 MAMP と MAMP PRO は同時に起動しないでください。**
> Apache 8888 / MySQL 8889 / ソケットパスが丸被りします。
>
> 無料版 MAMP を使う場合は、MAMP PRO を Stop すれば従来どおり
> <http://localhost:8888/floppy_io/> で動きます。

---

### C. VS Code の Live Server で開く

Live Server は PHP を実行できないため、ビルド済みの `frontend/dist` を配信し、
API だけ MAMP の PHP を直接呼びます（CORS は許可済み）。

1. MAMP で Apache と MySQL を起動する（上記 A-1 / A-2 を済ませておく）。
2. `frontend/dist` を最新にする（`cd frontend && npm run build`）。
3. VS Code でこのフォルダを開き、**Live Server を再起動**する。
   `.vscode/settings.json` で配信ルートとホストを設定してあります。

   ```json
   {
     "liveServer.settings.root": "/frontend/dist",
     "liveServer.settings.port": 5500,
     "liveServer.settings.host": "localhost"
   }
   ```

4. 👉 <http://localhost:5500/>

> **`127.0.0.1:5500` ではなく `localhost:5500` で開いてください。**
> YouTube は IP アドレスからの埋め込みを拒否するため、`127.0.0.1` で開くと
> 動画が「この動画は再生できません」になります（Live Server の既定ホストは
> `127.0.0.1` なので、上記の `host` 設定で `localhost` に変えています）。
> もし IP アドレスで開いてしまった場合は、画面にも案内が表示されます。

> `frontend/dist/index.html` を直接右クリック →「Open with Live Server」でも
> 同じように開けます。

---

### D. Vite 開発サーバーで開く（ホットリロード）

```bash
# ターミナル 1: PHP API
cd backend
php -S localhost:8000

# ターミナル 2: Vite
cd frontend
npm install
npm run dev
```

ブラウザで <http://localhost:5173> を開いてください。`/api/*` へのリクエストは
自動的に `http://localhost:8000` へプロキシされます。

> `php -S` を素の MySQL（`:3306` / `root` / パスワードなし）で使う場合は
> 環境変数で上書きできます。
>
> ```bash
> FLOPPY_DB_PORT=3306 FLOPPY_DB_PASS= php -S localhost:8000
> ```

### 4. 本番ビルド

```bash
cd frontend
npm run build      # dist/ に出力
```

`dist/` を静的ホスティングし、`/api/*` を PHP サーバーへリバースプロキシしてください。

### API の接続先を変える

`frontend/public/config.js` がページの配信元に応じて API のベース URL を
自動で切り替えます（MAMP → 同一オリジンの `/floppy_io/api`、Live Server →
`http://localhost:8888/floppy_io/api`、Vite → `/api`）。ポートや公開パスを
変えた場合はこのファイルの `MAMP_ORIGIN` / `MAMP_API_PATH` を書き換えて
再ビルドしてください。


## データベースを操作する

現在のデータのダンプは **`database/floppy_io.sql`**（スキーマ＋データ）にあります。
復元するには:

```bash
./tools/db.sh < database/floppy_io.sql
```

> `database/floppy_io.sql` は **パスワードハッシュを含むため `.gitignore` で
> コミット対象外**にしています（`database/schema.sql` は DDL のみでコミットされます）。
> リポジトリにも含めたい場合は `.gitignore` から外してください。


このフォルダの中から DB を直接いじれるように、**Adminer（Web 画面）** と
**CLI ツール** を用意しています。

### 1. Web 画面（Adminer）

👉 **<http://floppy.io:8080/floppy_io/db/>**

- ログイン画面が出たら、`サーバ: localhost`（空欄でも可）/ `ユーザー名: root` /
  `パスワード: root`（何でも通ります）/ `データベース: floppy_io` で入ります。
- 事前入力して開くなら
  <http://floppy.io:8080/floppy_io/db/?username=root&db=floppy_io>
- テーブルの閲覧・編集・SQL 実行ができます。
- 接続先は `backend/config/database.php` と同じ（MAMP / MAMP PRO の
  MySQL は TCP 無効のことがあるため `localhost` = unix ソケットを使用）。
- 安全のため **127.0.0.1 / ::1 からのみ**アクセスできます。

本体（`backend/db/adminer.php`）はサードパーティ製なので、`.gitignore` で除外し
次のコマンドで取得し直せます。

```bash
./tools/fetch-adminer.sh
```

### 2. コマンドライン

```bash
./tools/db.sh                          # 対話シェル（SQL を直接入力）
./tools/db.sh "SELECT * FROM users;"   # 1 クエリだけ実行
./tools/db.sh < database/schema.sql    # SQL ファイルを流し込む
```

接続情報は環境変数で上書きできます。

```bash
FLOPPY_DB_SOCKET=/path/to/mysql.sock ./tools/db.sh "SHOW TABLES;"
```

## 容量の考え方

- **1 投稿 = フロッピー 1 枚**。1 投稿の合計（本文 + ドット絵 256 バイト + 画像）が
  1.44MB を超えると 403 で拒否されます。累計では制限しません。
- 投稿フォームの `DISK (C:)` は、**いま書いている投稿**の容量統計（使用バイト数 /
  上限 / 使用率）を表示します。残量は表示しません。
- ドット絵は常に 256 バイト固定（未描画でも 256 バイト消費）。本文はマルチバイト文字も
  `strlen` のバイト数でカウントするため、日本語は 1 文字 3 バイトとして消費されます。
- **画像も容量に含まれます**。画像は縮小せず実ファイルのまま `backend/uploads/` に保存し、
  そのバイト数を 1 投稿の合計に加算します。つまり写真 1 枚で 1.44MB をほぼ使い切ります。
- **YouTube の埋め込みは容量に含まれません**（本文中の URL 文字列だけが本文バイト数として
  カウントされます）。保存するのは動画 ID・タイトル・サムネイル URL のメタ情報のみです。
- プロフィール画像も投稿の容量制限とは別枠です。
- 保存済みの全投稿の合計は `GET /api/disk_usage.php` の `total_bytes` で確認できます
  （参考値・制限対象ではありません）。

## 画像投稿

- 投稿フォームの「🖼 画像を添付」から JPEG / PNG / GIF / WebP を選べます。
- 画像は**そのまま** `backend/uploads/` に保存し、`image_path` / `image_bytes` /
  `image_width` / `image_height` を `posts` に記録します。
- 画像のバイト数も 1 投稿の容量（1.44MB）に含まれます。超える場合は 403 で拒否され、
  保存済みの一時ファイルも破棄されます。
- 投稿を削除（フォーマット）すると画像ファイルも削除されます。
- 公開 URL は `http://localhost:8888/floppy_io/uploads/<ファイル名>` で、
  API のレスポンスに `image_url` として含まれます。

## 設計メモ / 拡張ポイント

- **認証**: Bearer トークン方式。`api_tokens` テーブルにトークンを保存し、
  `backend/config/database.php` の `current_user()` / `require_user()` で判定します。
  投稿は `posts.user_id` でユーザーごとに分離されています。
  - MAMP の Apache は CGI/FastCGI 経由のため、`backend/api/.htaccess` の
    `CGIPassAuth On` が無いと `Authorization` ヘッダが PHP に届きません。
  - Cookie を使わないので、Live Server のようなクロスオリジンでも動きます
    （CORS で `Authorization` を許可済み）。
- **ルーティング**: 依存を増やさないため、`frontend/src/utils/router.js` に
  ハッシュ方式の小さなルーターを自前実装しています（サーバー側リライト不要）。
- **容量計算**: `posts.total_bytes` に投稿時の値を保存しているため、1 投稿の容量判定は
  投稿時に確定します（本文を再計算する必要はありません）。累計が必要な場合は
  `SUM(total_bytes)` で求まります。
- **ドット絵パレット**: `backend/config/database.php` の `PIXEL_PALETTE` と
  `frontend/src/utils/pixel.js` の `PALETTE` は一致させてください。
