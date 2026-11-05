# floppy.io

**1.44MB しか使えない静寂のレトロ SNS**

👉 **公開サイト: <https://fdd.wawa-app.me/floppy.io/>**

「現代の Web はリソースを消費しすぎている」というアンチテーゼから生まれた、レトロ
コンピューティング趣味全開のミニマル SNS。**1 投稿あたり**の容量上限はフロッピー
ディスク 1 枚分 (**1.44MB = 1,474,560 Bytes**) で、1 投稿＝フロッピー 1 枚という
イメージ。テキスト投稿と超軽量なドット絵だけを許可し、1 投稿の合計が 1.44MB を
超えるものは投稿できません（累計は制限しません）。

画面は「古い Twitter の 2 カラム × mixi2 の静けさ × レトロ掲示板」を参考にした
ライトテーマ。生成りの紙色、淡いミントのトップバー、青リンク、等幅の `No.` /
`bytes` 表示、ドット枠とピクセルフロッピーで、1 投稿＝1 枚というコンセプトを
UI そのもので表現しています。ホームは「タイムライン / フォロー中」のタブ切り替え、
設定・ヘルプは右端の三点メニューに集約しています。

---

## 公開サイト

👉 **<https://fdd.wawa-app.me/floppy.io/>**

Cloudflare Tunnel 経由で、静的配信（Nginx / Apache）と FastAPI に振り分けています。
バックエンドは FastAPI のみです。

```text
~/Quadtecho/floppy.io/
├── index.html, _nuxt/, config.js, favicon.png, card.png  -> frontend/dist へのリンク
├── api      -> ProxyPass → http://127.0.0.1:8000/api      (FastAPI)
└── uploads  -> ProxyPass → http://127.0.0.1:8000/uploads  (FastAPI)
```

## SNS カード（OGP / Twitter Card）

URL を貼るとサイトのカードが展開されます。OGP は業界標準なので、X（Twitter）
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

- カードの情報は `frontend/nuxt.config.ts` に**静的に**書いています。X などの
  クローラーは JavaScript を実行しないため、実行時の注入では間に合いません。
- 画像は 1200×630（`summary_large_image` 推奨サイズ・約 77KB）の
  `frontend/public/card.png` です。
- 元データは `tools/og-card.html` で、`tools/make-og-card.sh` で再生成できます。

```bash
tools/make-og-card.sh    # tools/og-card.html → frontend/public/card.png
```

> ⚠️ ハッシュルーティング（`#/p/12`）は X がフラグメントを無視するため、
> 投稿ごとのカードには対応していません（サイト共通のカードになります）。

## 技術スタック

| レイヤー | 技術 |
| --- | --- |
| フロントエンド | Nuxt 4 (Vue 3 Composition API / SPA / ハッシュルーティング) |
| スタイル | 独自 CSS「RETRO BBS / EARLY TWITTER / MIXI2」（生成り・ミント・青リンク・ドット枠） |
| 描画 | HTML5 Canvas API（外部描画ライブラリ不使用） |
| バックエンド | Python 3.12+ / FastAPI（RESTful JSON API） |
| DB ドライバ | PyMySQL（プレースホルダで SQL インジェクション対策） |
| 認証 | bcrypt + Bearer トークン（`api_tokens`） |
| データベース | MySQL 8.x（`utf8mb4`） |

## コア仕様

- **容量制限（1 投稿あたり）**: 投稿時に本文の UTF-8 バイト長と
  ドット絵データのバイト長を合算し、**その投稿の合計**が `1,474,560 Bytes` を超える
  場合は HTTP **403** で弾く。累計では制限しない。
- **ドット絵の超軽量データ化**: 16×16（計 256 マス）。画像ファイルには変換せず、
  「カラーコードのインデックス配列」を **16 進数 256 文字（= 256 バイト）** の文字列
  として DB に保存する。各文字 `0-9A-F` が 16 色パレットの 1 色に対応。

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
│   │   ├── schemas.py              # リクエストスキーマ
│   │   ├── routers/
│   │   │   ├── auth.py             # 登録 / ログイン / ログアウト / me
│   │   │   ├── posts.py            # 投稿一覧・投稿・削除・プレビュー・容量
│   │   │   ├── users.py            # プロフィール / 設定 / アバター
│   │   │   ├── social.py           # いいね / フォロー
│   │   │   └── uploads.py          # /uploads/<name> の配信
│   │   └── utils/
│   │       ├── pixels.py           # 16×16 / 256 バイトのドット絵
│   │       ├── images.py           # 画像の MIME / 寸法判定
│   │       ├── uploads.py          # ファイル保存 / URL
│   │       └── youtube.py          # YouTube Data API v3 連携
│   ├── uploads/                    # アップロードされた実ファイル
│   ├── requirements.txt
│   ├── .env.example
│   └── run.sh                      # venv 作成 + uvicorn 起動
├── database/
│   └── schema.sql                  # MySQL DDL（＋デモユーザー投入）
├── frontend/
│   ├── app/
│   │   ├── app.vue                 # Nuxt ルート
│   │   ├── layouts/default.vue     # トップバー / サイドバー / フッター
│   │   ├── pages/                  # ファイルベースルーティング
│   │   │   ├── index.vue           # /
│   │   │   ├── following.vue       # /following
│   │   │   ├── search.vue          # /search
│   │   │   ├── u/[username].vue    # /u/:username
│   │   │   ├── p/[id].vue          # /p/:id
│   │   │   ├── login.vue / register.vue
│   │   │   └── settings.vue / help.vue
│   │   ├── components/             # Composer / PostItem / DiskGauge など
│   │   ├── views/                  # 画面本体 (Home / Profile / Auth ...)
│   │   ├── composables/useAuth.js  # ログイン状態（localStorage トークン）
│   │   ├── utils/api.js            # API クライアント
│   │   ├── utils/pixel.js          # ドット絵のパース/描画
│   │   └── assets/css/main.css     # RETRO BBS デザインシステム
│   ├── public/
│   │   ├── config.js               # 実行時 API 接続先
│   │   ├── card.png                # SNS カード用の画像 (1200x630)
│   │   └── favicon.png
│   ├── nuxt.config.ts              # OGP / フォント / プロキシ / ハッシュルーティング
│   └── package.json
├── tools/
│   ├── og-card.html                # SNS カード画像の元データ
│   └── make-og-card.sh
└── README.md
```

## 開発環境

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
`FLOPPY_PUBLIC_BASE_URL=https://example.com/floppy.io/` を設定すると、
共有用 HTML の URL が正しくなります。

## 画面と URL（ハッシュルーティング）

| パス | 画面 |
| --- | --- |
| `#/` | ホーム（タイムライン＋投稿フォーム） |
| `#/following` | フォロー中タイムライン（自分＋フォロー中ユーザーの投稿・要ログイン） |
| `#/search?q=...` | 検索（本文・ユーザー名・表示名の部分一致） |
| `#/u/:username` | プロフィール（自分・他ユーザーどちらも） |
| `#/p/:id` | 共有された投稿（1 投稿だけを表示する共有ページ） |
| `#/settings` | 設定（表示名 / bio / パスワード変更 / ログアウト） |
| `#/help` | ヘルプ |
| `#/login` / `#/register` | ログイン / 新規登録 |

サーバー側のリライトが不要なハッシュ方式なので、静的配信でもそのまま動きます。

## アカウント

- 新規登録・ログイン・ログアウトに対応。投稿・削除は**ログイン必須**で、
  投稿はユーザーごとに分離されます。
- パスワードは `password_hash()`（bcrypt）でハッシュ化して保存します。
- 認証は **Bearer トークン**方式（`localStorage` に保持）です。Cookie を使わないため、
  別オリジン（静的配信サーバーなど）からでもそのまま動きます。
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

## API 一覧

| メソッド | エンドポイント | 説明 |
| --- | --- | --- |
| `POST` | `/api/register` | 新規登録 `{ username, password, display_name? }` |
| `POST` | `/api/login` | ログイン `{ username, password }` |
| `POST` | `/api/logout` | ログアウト（要ログイン） |
| `GET`  | `/api/me` | ログイン中ユーザー（要ログイン） |
| `POST` | `/api/update_profile` | 表示名 / bio 更新（要ログイン） |
| `POST` | `/api/update_avatar` | プロフィール画像の設定 / 削除（要ログイン・multipart） |
| `POST` | `/api/change_password` | パスワード変更（要ログイン） |
| `GET`  | `/api/user?username=floppy` | プロフィール＋その人の投稿 |
| `GET`  | `/api/posts[?username=floppy][&q=キーワード]` | 投稿一覧（新しい順 / 検索） |
| `GET`  | `/api/posts?feed=following` | フォロー中タイムライン＝自分＋フォロー中ユーザーの投稿（要ログイン） |
| `POST` | `/api/posts` | 新規投稿 `{ text, pixel_data }` / `multipart/form-data`（`image` `floppy` 添付可・要ログイン） |
| `POST` | `/api/delete_post` | 自分の投稿を削除 `{ id }`（要ログイン） |
| `POST` | `/api/like` | いいねの付け外し `{ id }`（要ログイン・トグル） |
| `POST` | `/api/follow` | フォローの付け外し `{ username }` または `{ id }`（要ログイン・トグル） |
| `GET`  | `/api/disk_usage[?username=floppy]` | 1 投稿あたりの上限 / 合計（参考値） |
| `GET`  | `/api/preview?id=123` | 埋め込み用プレビュー（メタ情報＋HTML スニペット） |

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

- プリセット: 顔文字 / BBS / フレーム / ドット
- 自作スタンプは **ブラウザの localStorage**（キー: `floppy_aa_stamps_v1`）に保存
- 保存できる自作スタンプは **最大 50 件 / 1 件 300 文字**
- 保存先は端末・ブラウザごとで、**サーバーには送信されません**
- 自作タブの `×` で削除できます

> 複数行の AA は前後に改行、1 行の顔文字は前後に半角スペースを補って挿入します。

## 共有

- 各投稿の「🔗 共有」を押すと**共有ダイアログ**が開きます。
- **共有リンク**（`#/p/:id`）は、その投稿 1 件だけを表示する共有ページを開きます。
- **外部サイトに貼り付ける HTML** は `/api/preview` が自己完結型のスニペットとして
  生成します。本文・ドット絵（SVG）・画像・YouTube・フロッピーファイル（音声は
  プレイヤー付き）が 1 枚のカードにまとまります。
- ドット絵のない投稿では、空白にならないようフロッピーアイコンを表示します。

## いいね

- 各投稿に「♡ いいね」ボタンがあります。クリックで付け外し（トグル）できます。
- いいねにはログインが必要です。未ログインで押すと案内が表示されます。
- 件数は誰でも見えますが、押したかどうかはユーザーごとに表示されます。
- `likes` テーブルに保存し、投稿が削除されると連動して消えます
  （1 ユーザー 1 投稿につき 1 件）。

## フォロー / フォロー中タイムライン

- プロフィールの「フォローする」を押すと**フォローの付け外し（トグル）**ができます。
  フォロー中はボタンが「フォロー中」に変わります（自分自身にはボタンを出しません）。
- ホームのタブで「タイムライン」（全員の投稿）と「**フォロー中**」（`#/following`）を
  切り替えられます。フォロー中タイムラインは**自分＋フォロー中ユーザーの投稿**を
  新しい順に表示します。
- フォロー中タイムラインは**ログイン必須**です（誰をフォローしているかは本人にしか
  見せません）。未ログインで開くとログインの案内を表示します。
- 投稿・プロフィールに**フォロー数 / フォロワー数**を表示します。
- `follows` テーブル（`follower_id` → `followee_id`）に保存し、どちらかのユーザーが
  消えると連動して消えます（1 組 1 件・自分自身は登録できません）。

## 画像投稿

- 投稿フォームの「🖼 画像を添付」から JPEG / PNG / GIF / WebP を選べます。
- 画像は**そのまま** `backend/uploads/` に保存し、`image_path` / `image_bytes` /
  `image_width` / `image_height` を `posts` に記録します。
- 画像のバイト数も 1 投稿の容量（1.44MB）に含まれます。超える場合は 403 で拒否され、
  保存済みの一時ファイルも破棄されます。
- 投稿を削除（フォーマット）すると画像ファイルも削除されます。
- 公開 URL は `<ローカル URL>/floppy_io/uploads/<ファイル名>` で、
  API のレスポンスに `image_url` として含まれます。

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

詳細なポリシー・報告方法・本番チェックリストは **[SECURITY.md](./SECURITY.md)** にまとめています。
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
> API からの直接取得までは防げません。詳細は [SECURITY.md](./SECURITY.md) を参照してください。

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
- **ルーティング**: Nuxt 4 の `router.options.hashMode` を使い、
  `#/u/name` / `#/p/12` のような URL を維持しています（サーバー側リライト不要）。
- **容量計算**: `posts.total_bytes` に投稿時の値を保存しているため、1 投稿の容量判定は
  投稿時に確定します（本文を再計算する必要はありません）。累計が必要な場合は
  `SUM(total_bytes)` で求まります。
- **ドット絵パレット**: `backend/app/utils/pixels.py` の `PIXEL_PALETTE` と
  `frontend/app/utils/pixel.js` の `PALETTE` は一致させてください。

## 注意

- 本リポジトリはオープンソースではありません。ライセンスがない限り、
  再配布・商用利用・公開ミラーへの転載は許可されません。
- セットアップ手順はこの README と [SECURITY.md](./SECURITY.md) に記載しています。
  本番の秘密情報（DB パスワード、API キー、トークン）はリポジトリに含めていません。
- 画面上のコピー抑止はカジュアルな転載を減らすためのもので、完全な防御ではありません。
- 公開サーバーとして運用する場合は、[SECURITY.md](./SECURITY.md) のチェックリストを
  実施した上で自己責任でお願いします。
