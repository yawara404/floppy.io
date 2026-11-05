# Security Policy

floppy.io は「1 投稿 = 1.44MB」という制約を守る小さな SNS です。
小さなサービスだからこそ、認証・入力検証・アップロード・ヘッダー・
運用設定まで、攻撃面をひとつずつ塞ぐ方針で作っています。

- フロントエンド: Nuxt 4（SPA / 静的生成）
- API: Python 3.12+ / FastAPI
- DB: MySQL 8.x（PyMySQL / プレースホルダ）
- 認証: bcrypt + Bearer トークン

## サポート対象

| バージョン | サポート |
| --- | --- |
| `master` の最新コミット | ✅ |
| 過去のコミット / フォーク / 改変版 | ❌ |

セキュリティ修正は `master` に対して行います。運用者は常に最新の
`master`（またはリリースタグ）へ追従してください。

## 脆弱性の報告

**公開 Issue に脆弱性の詳細を書かないでください。**

1. GitHub の **Security タブ → Report a vulnerability**（Private Vulnerability
   Reporting）から報告してください。
2. それが使えない場合は、リポジトリオーナーへ GitHub 経由で直接連絡してください。

### 報告に含めてほしい情報

- 問題の概要と影響（例: 認証回避、他ユーザーの投稿削除、SSRF など）
- 再現手順または概念実証（PoC）
- 影響するエンドポイント / ファイル
  （例: `backend/app/routers/posts.py`, `frontend/app/utils/api.js`）
- 想定される重大度（CVSS があれば尚可）
- 検証に使った環境（OS / Python / MySQL / ブラウザ）

### 報告に含めないでください

- 実在する秘密情報（DB パスワード、YouTube API キー、他ユーザーのトークン）
- 他者の個人情報
- 破壊的な検証（データ削除・大量投稿・DoS）

秘密情報を誤って送ってしまった場合は、報告前に該当値を失効・再発行してください。

### 対応の目安

| フェーズ | 目安 |
| --- | --- |
| 受領連絡 | 2 営業日以内 |
| 一次トリアージ | 7 日以内 |
| 修正 / 回避策の提示 | 重大度に応じて協議 |
| 公開 | 修正反映後、報告者の同意を得て調整 |

修正が完了するまで、詳細の公開はお控えください。

## 対象範囲

**対象**

- `backend/app/` の FastAPI コード
- `frontend/app/` の Nuxt コード
- `database/schema.sql`
- `frontend/public/.htaccess` などの配信設定
- 認証・アップロード・プレビューなど本リポジトリの実装

**対象外**

- MySQL / Python / Node.js / リバースプロキシなど外部ソフトウェア自体の脆弱性
- YouTube / Google Fonts など外部サービスの問題
- 運用者側のインフラ設定（TLS 証明書、DB の公開設定、バックアップ等）
- ソーシャルエンジニアリング、物理的な攻撃
- ブラウザの開発者ツールやスクリーンショットによる閲覧
  （コピー抑止は「 deterrent 」であり、完全な防御ではありません）

## セキュリティ対策

### 認証とセッション

- パスワードは **bcrypt（cost 12）** でハッシュ化して保存します。平文は保存しません。
- 旧 PHP 版の `$2y$` ハッシュも `$2b$` として検証できるよう互換処理を入れています。
- API トークンは **256bit の乱数**（`secrets.token_hex(32)`）で発行します。
- トークンは DB に平文で保存せず、**SHA-256 ハッシュ**で保存します。
  旧バージョンが発行した平文トークンは、初回利用時に自動でハッシュへ移行します。
- トークンは `Authorization: Bearer <token>` のみで送ります。Cookie は使いません。
  そのため、Cookie ベースの CSRF は成立しません。
- `FLOPPY_TOKEN_TTL_DAYS` で有効期限を設定できます（本番は 30 日を推奨）。
- ログアウト時は該当トークンを DB から削除します。

### 認可

- 投稿削除は「投稿者本人」だけに許可します（`posts.user_id` を SQL 条件に含める）。
- プロフィール更新・パスワード変更・アバター更新はログインユーザー本人のみ。
- フォロー中タイムラインはログインユーザーだけが取得できます。
- 自分自身へのフォローは API 側で拒否します。

### SQL インジェクション

- すべての SQL は PyMySQL のプレースホルダ（`%s`）を使用します。
- `IN (...)` はプレースホルダを個数分並べて生成します。
- 検索の `LIKE` は `%` / `_` / `\` をエスケープします。
- テーブル名・カラム名をユーザー入力から組み立てることはありません。

### XSS

- Vue のテンプレート補間は自動エスケープされます。`v-html` は使用していません。
- 共有用の埋め込み HTML（`/api/preview`）は、本文・表示名・日時などを
  `html.escape()` してから組み立てます。
- 画像 URL・YouTube サムネイル URL は許可された形式のみを出力します。
- CSP（`frontend/public/.htaccess`）で `object-src 'none'` / `frame-ancestors 'none'`
  を指定し、外部スクリプトの読み込みを制限します。

### アップロード

- 画像は **マジックバイトから MIME / 拡張子 / 寸法を判定**します
  （JPEG / PNG / GIF / WebP のみ）。
- 画像・添付ファイルは 1 ファイル **1.44MB 以下**に制限します。
- 保存名は **32 桁のランダム hex + 安全な拡張子**で生成し、元のファイル名は
  DB にのみ保存します（パストラバーサル対策）。
- 音声として再生できる拡張子以外の添付は **`.bin`** として保存し、
  実行可能ファイルとして配信されないようにします。
- 配信時は `X-Content-Type-Options: nosniff` と `Content-Disposition` を設定します。
- アップロードは公開ディレクトリの外（`backend/uploads/`）に置き、
  FastAPI の `/uploads/<name>` 経由で配信します。

### DoS / 乱用対策

- ログインは **10 回 / 60 秒 / IP**、登録は **5 回 / 5 分 / IP** に制限します。
- API のリクエストボディは **約 3.95MB** を超えると 413 を返します。
- 投稿一覧は最大 200 件、検索も同じ上限です。
- 1 投稿の容量を超えるリクエストは、ファイル保存前に 403 で拒否します。

> レート制限は単一プロセス内のメモリで実装しています。複数ワーカーで
> 運用する場合は Redis などの共有ストアに置き換えてください。

### セキュリティヘッダー

`frontend/public/.htaccess`（Apache）で以下を付与します。

| ヘッダー | 値 |
| --- | --- |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=(), payment=()` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Content-Security-Policy` | 下記参照 |

CSP は `default-src 'self'` を基本に、Google Fonts・YouTube・同一オリジンの
API / アップロードだけを許可します。別オリジンに API を置く場合は
`connect-src` にその origin を追加してください。

FastAPI 側でも `X-Content-Type-Options` / `X-Frame-Options` /
`Referrer-Policy` / `Permissions-Policy` / `Cache-Control: no-store` を付与します。

### コピー抑止（deterrence）

サイト上の文章・画像・ドット絵について、次のブラウザ操作を抑止しています。

- テキスト選択（`user-select: none`）
- 右クリックメニュー
- 画像・Canvas・メディアのドラッグ
- `Ctrl/Cmd + C` / `Ctrl/Cmd + X`（入力欄・共有リンク・埋め込みコードを除く）

入力欄、共有リンク、埋め込み HTML は通常どおりコピーできます。
共有ボタンのクリップボード書き込みも動作します。

> **重要**: これはカジュアルなコピーを減らすための UX 上の抑止であり、
> セキュリティ境界ではありません。HTML ソースの閲覧、開発者ツール、
> スクリーンショット、OCR、API からの直接取得まで防ぐことはできません。
> 機密情報はそもそも画面・API に返さない設計にしてください。

### データの取り扱い

- 保存する情報: ユーザー名、表示名、bio、パスワードハッシュ、
  投稿本文、ドット絵、画像・添付ファイル、いいね、フォロー、API トークン（ハッシュ）。
- 保存しない情報: メールアドレス、電話番号、位置情報、クレジットカード。
- アクセスログ: アプリケーションは IP を永続化しません。ただし、
  リバースプロキシ / Cloudflare / uvicorn のログには IP が残る場合があります。
  運用者側で保持期間を定めてください。
- 外部リクエスト: Google Fonts（フォント）、YouTube（サムネイル / 埋め込み）。
  これらは各サービスのプライバシーポリシーに従います。
- 解析タグ・広告・トラッカーは設置していません。

### 秘密情報の管理

- `backend/.env` はコミットしません（`.gitignore` 済み）。
- YouTube API キーはサーバー側の環境変数 `FLOPPY_YOUTUBE_API_KEY` に置き、
  フロントエンドへ渡しません。
- DB のパスワードは本番では必ず `FLOPPY_DB_*` で上書きし、
  開発用の既定値（`floppy` / `floppy`）を使わないでください。
- `.env` のパーミッションは `600` を推奨します。

```bash
chmod 600 backend/.env
```

## 本番運用チェックリスト

- [ ] **HTTPS** で公開し、HTTP からのリダイレクトと HSTS を有効にする
- [ ] MySQL は **localhost バインド**。専用ユーザーに
      `SELECT / INSERT / UPDATE / DELETE` だけを付与する
      （`GRANT` / `FILE` / `SUPER` は不要）
- [ ] DB のパスワードを強い値に変更し、`backend/.env` にのみ保存する
- [ ] `backend/.env` を `600` にする
- [ ] `FLOPPY_API_DOCS=0`（既定）で API ドキュメントを無効化する
- [ ] `FLOPPY_TOKEN_TTL_DAYS=30` など、トークンの有効期限を設定する
- [ ] `FLOPPY_CORS_ORIGINS` を公開オリジンだけに制限する
      （同一オリジン配信なら CORS 自体が不要）
- [ ] リバースプロキシで `/api` と `/uploads` だけを FastAPI に転送し、
      `/api/docs` は本番でブロックする
- [ ] `backend/uploads/` を公開ディレクトリに置かない
- [ ] Apache の `AllowOverride` を有効にし、`.htaccess` のヘッダーを反映する
      （Nginx の場合は同等のヘッダーを `add_header` で設定）
- [ ] 依存パッケージを更新する
      （`pip install -r requirements.txt --upgrade`, `npm audit`, `npm update`）
- [ ] DB の定期バックアップと `backend/uploads/` のバックアップ
- [ ] ログの保持期間とアクセス権を定める
- [ ] 変更後は `/api/health` と主要導線（登録→投稿→削除）を確認する

### Nginx のヘッダー例

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=()" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
# CSP は .htaccess の値を参考に、配信オリジンに合わせて設定する
```

## 既知の制約

- コピー抑止はブラウザ上の deterrent です。完全なコピー防止ではありません。
- レート制限は単一プロセスのメモリ内です。水平スケール時は共有ストアが必要です。
- メールアドレスによる本人確認、2 段階認証、パスワードリセットは未実装です。
- モデレーション（通報・ブロック・NSFW 判定）は未実装です。
- トークンは既定で無期限です。`FLOPPY_TOKEN_TTL_DAYS` の設定を推奨します。
- CSP は Nuxt のインラインスクリプト / スタイルを許可するため
  `'unsafe-inline'` を含みます。nonce ベースへ移行する余地があります。

## 依存関係と更新

```bash
# Python
cd backend
.venv/bin/pip install --upgrade -r requirements.txt
.venv/bin/pip-audit            # 任意 (pip-audit)

# Node / Nuxt
cd frontend
npm audit
npm update
npm run build
```

## 開示方針

- 修正版がリリースされるまで、脆弱性の詳細は公開しません。
- 報告者の希望に応じて、クレジットを掲載します（匿名可）。
- 本ポリシーは必要に応じて更新します。最終更新: 2026-11-05。
