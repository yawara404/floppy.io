# floppy.io

**1.44MB しか使えない静寂のレトロ SNS**

👉 **公開サイト: <https://music.wawa-app.me/floppy.io/>**

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

## 公開サイト

👉 **<https://music.wawa-app.me/floppy.io/>**

Cloudflare Tunnel 経由で公開しています。トンネルは Host を保ったままローカルの
Apache へ転送するため、Apache の該当 vhost 内で `/floppy.io/` を配信しています。
実体は `~/Quadtecho/floppy.io/` からのシンボリックリンクです（Apache の設定変更なしで公開できる）。

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
│       ├── like.php            # いいねの付け外し（トグル）
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
│   │   │   ├── PostList.vue        # 投稿一覧＋削除＋共有ダイアログ
│   │   │   ├── DiskGauge.vue       # この投稿の容量統計（使用量 / 上限 / 使用率）
│   │   │   ├── PixelEditor.vue     # 16×16 ドット絵 Canvas エディタ
│   │   │   ├── PostItem.vue        # 投稿カード（ドット絵＋本文＋消費バイト数）
│   │   │   └── FloppyCard.vue      # 共有カード（エコシステム用プレビュー）
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
│   │   │   ├── PostView.vue        # 共有ページ（#/p/:id）
│   │   │   └── Auth.vue            # ログイン / 新規登録
│   │   ├── App.vue                 # トップバー（ロゴ＋ナビ）＋ 2 カラム
│   │   ├── main.js
│   │   └── style.css               # 昔の Twitter 風テーマ
│   ├── public/
│   │   ├── config.js               # 実行時 API 接続先（配信元に応じて切替）
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
| `POST` | `/api/register.php` | 新規登録 `{ username, password, display_name? }` |
| `POST` | `/api/login.php` | ログイン `{ username, password }` |
| `POST` | `/api/logout.php` | ログアウト（要ログイン） |
| `GET`  | `/api/me.php` | ログイン中ユーザー（要ログイン） |
| `POST` | `/api/update_profile.php` | 表示名 / bio 更新（要ログイン） |
| `POST` | `/api/update_avatar.php` | プロフィール画像の設定 / 削除（要ログイン・multipart） |
| `POST` | `/api/change_password.php` | パスワード変更（要ログイン） |
| `GET`  | `/api/user.php?username=floppy` | プロフィール＋その人の投稿 |
| `GET`  | `/api/posts.php[?username=floppy][&q=キーワード]` | 投稿一覧（新しい順 / 検索） |
| `POST` | `/api/posts.php` | 新規投稿 `{ text, pixel_data }` / `multipart/form-data`（`image` `floppy` 添付可・要ログイン） |
| `POST` | `/api/delete_post.php` | 自分の投稿を削除 `{ id }`（要ログイン） |
| `POST` | `/api/like.php` | いいねの付け外し `{ id }`（要ログイン・トグル） |
| `GET`  | `/api/disk_usage.php[?username=floppy]` | 1 投稿あたりの上限 / 合計（参考値） |

| `GET`  | `/api/preview.php?id=123` | 埋め込み用プレビュー（メタ情報＋HTML スニペット） |

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

## 共有

- 各投稿の「🔗 共有」を押すと**共有ダイアログ**が開きます。
- **共有リンク**（`#/p/:id`）は、その投稿 1 件だけを表示する共有ページを開きます。
- **外部サイトに貼り付ける HTML** は `preview.php` が自己完結型のスニペットとして
  生成します。本文・ドット絵（SVG）・画像・YouTube・フロッピーファイル（音声は
  プレイヤー付き）が 1 枚のカードにまとまります。
- ドット絵のない投稿では、空白にならないようフロッピーアイコンを表示します。

## いいね

- 各投稿に「♡ いいね」ボタンがあります。クリックで付け外し（トグル）できます。
- いいねにはログインが必要です。未ログインで押すと案内が表示されます。
- 件数は誰でも見えますが、押したかどうかはユーザーごとに表示されます。
- `likes` テーブルに保存し、投稿が削除されると連動して消えます
  （1 ユーザー 1 投稿につき 1 件）。

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

- 幅 700px 以下で 1 カラム化し、ナビはハンバーガーで開閉します。
- **入力欄は 16px 以上**に統一しています（iOS Safari は 16px 未満の入力欄に
  フォーカスすると自動で画面を拡大してしまうため）。
- タップ領域を広げています（いいね / 共有 36px、⋯ 34px、色パレット 30px、
  ダイアログの × 40px）。
- 画面より縦に長いダイアログはスクロールできます。
- 添付した画像・YouTube・音声プレイヤーは画面幅に収まります。

## 設計メモ / 拡張ポイント

- **認証**: Bearer トークン方式。`api_tokens` テーブルにトークンを保存し、
  `backend/config/database.php` の `current_user()` / `require_user()` で判定します。
  投稿は `posts.user_id` でユーザーごとに分離されています。
  - Apache を CGI/FastCGI で運用する場合、`backend/api/.htaccess` の
    `CGIPassAuth On` が無いと `Authorization` ヘッダが PHP に届きません。
  - Cookie を使わないので、クロスオリジンでも動きます
    （CORS で `Authorization` を許可済み）。
- **ルーティング**: 依存を増やさないため、`frontend/src/utils/router.js` に
  ハッシュ方式の小さなルーターを自前実装しています（サーバー側リライト不要）。
- **容量計算**: `posts.total_bytes` に投稿時の値を保存しているため、1 投稿の容量判定は
  投稿時に確定します（本文を再計算する必要はありません）。累計が必要な場合は
  `SUM(total_bytes)` で求まります。
- **ドット絵パレット**: `backend/config/database.php` の `PIXEL_PALETTE` と
  `frontend/src/utils/pixel.js` の `PALETTE` は一致させてください。

## 注意

- 本リポジトリはオープンソースではありません。**セットアップ手順・内部運用情報は
  含めていません**（ローカル環境の手順はリポジトリ外で管理しています）。
- 画面はレトロな見た目を再現していますが、実装は現行の Web 標準に沿っています。
- 公開サーバーとして運用する場合は、十分なセキュリティ設定を行った上で自己責任でお願いします。
