<?php
declare(strict_types=1);

/**
 * floppy.io — データベース管理画面 (Adminer)
 *
 * backend/db を置いておくだけで、ローカルからデータベースを閲覧・編集できる。
 *
 * 公開サーバーで事故が起きないよう、次の3点を必須にしている。
 *
 *  1. 既定では無効。環境変数 `FLOPPY_DB_ADMIN_TOKEN` を設定したときだけ動く。
 *     未設定なら常に 403（= リポジトリをそのまま置いても管理画面は開かない）。
 *  2. トークンの一致が必要（`?token=...` または `X-Admin-Token` ヘッダ）。
 *  3. DB の接続情報は環境変数 `FLOPPY_DB_*` から読み、パスワードは Adminer の
 *     ログイン画面で入力する（リポジトリに既定の資格情報を置かない）。
 *
 * ※ 127.0.0.1 / ::1 のチェックも残しているが補助的なもの。Cloudflare Tunnel や
 *    リバースプロキシ経由だと REMOTE_ADDR は 127.0.0.1 になるため、これだけでは
 *    保護にならない（実際の保護は下のトークン）。
 */

// --- 1. ローカルからのアクセスのみ（補助的な確認） -------------------------
$remoteIp = $_SERVER['REMOTE_ADDR'] ?? '';

if (!in_array($remoteIp, ['127.0.0.1', '::1'], true)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    exit('この DB 管理画面はローカルからのみ利用できます。');
}

// --- 2. トークンが設定されていなければ常に無効 -----------------------------
/** 管理画面を有効にするトークン（環境変数。未設定なら無効）。 */
function floppy_db_admin_token(): string
{
    return trim((string) getenv('FLOPPY_DB_ADMIN_TOKEN'));
}

/** リクエストに付けられたトークン（ヘッダ優先・次にクエリ）。 */
function floppy_db_admin_candidate(): string
{
    foreach (['HTTP_X_ADMIN_TOKEN', 'REDIRECT_HTTP_X_ADMIN_TOKEN'] as $key) {
        if (!empty($_SERVER[$key])) {
            return trim((string) $_SERVER[$key]);
        }
    }

    return trim((string) ($_GET['token'] ?? ''));
}

$expected  = floppy_db_admin_token();
$candidate = floppy_db_admin_candidate();

if ($expected === '' || $candidate === '' || !hash_equals($expected, $candidate)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: no-store');
    exit(
        $expected === ''
            ? "この DB 管理画面は無効です。使う場合は環境変数 FLOPPY_DB_ADMIN_TOKEN に"
              . "ランダムな文字列を設定して起動し直し、?token=<その値> で開いてください。"
            : '管理者トークンが違います。'
    );
}

/**
 * Adminer の拡張ポイント。
 * 接続先だけ環境変数から補い、認証は Adminer のログイン画面に任せる。
 */
function adminer_object()
{
    // Adminer 6 以降は名前空間 Adminer\ の中に本体クラスがある
    if (!class_exists('Adminer') && class_exists('Adminer\\Adminer')) {
        class_alias('Adminer\\Adminer', 'Adminer');
    }

    class FloppyAdminer extends Adminer
    {
        // 自動ログインはしない（login() は上書きしない）。
        // リポジトリに既定の DB 資格情報を置かないため、パスワードは画面で入力する。

        /** 接続情報 (server, username, password)。値は環境変数 FLOPPY_DB_* から読む。 */
        public function credentials()
        {
            $host = (string) (getenv('FLOPPY_DB_HOST') ?: '127.0.0.1');
            $user = (string) (getenv('FLOPPY_DB_USER') ?: 'root');
            // パスワードの既定値は置かない（公開リポジトリに載せない）。
            $pass = (string) (getenv('FLOPPY_DB_PASS') ?: '');

            return [$host, $user, $pass];
        }

        // 最初から開くデータベース
        public function database()
        {
            return (string) (getenv('FLOPPY_DB_NAME') ?: 'floppy_io');
        }

        public function name()
        {
            return 'floppy.io DB';
        }
    }

    return new FloppyAdminer;
}

include __DIR__ . '/adminer.php';
