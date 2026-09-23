<?php
declare(strict_types=1);

/**
 * floppy.io — データベース管理画面 (Adminer)
 *
 * backend/db を置いておくだけで、
 *   http://floppy.io:8080/floppy_io/db/
 * からデータベースを閲覧・編集できる。
 *
 * 接続情報は backend/config/database.php と同じ既定値 (root / root / floppy_io)。
 * MAMP / MAMP PRO の MySQL は TCP が無効なことがあるため、server は
 * "localhost"（= unix ソケット）を使う。
 *
 * 安全のため、127.0.0.1 / ::1 からのアクセスのみ許可する。
 */

$remoteIp = $_SERVER['REMOTE_ADDR'] ?? '';

if (!in_array($remoteIp, ['127.0.0.1', '::1'], true)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    exit('この DB 管理画面はローカルからのみ利用できます。');
}

/**
 * Adminer の拡張ポイント。
 * ログイン画面を出さず、既定の接続情報でそのまま開く。
 */
function adminer_object()
{
    // Adminer 6 以降は名前空間 Adminer\ の中に本体クラスがある
    if (!class_exists('Adminer') && class_exists('Adminer\\Adminer')) {
        class_alias('Adminer\\Adminer', 'Adminer');
    }

    class FloppyAdminer extends Adminer
    {
        // パスワード入力なしでログインさせる
        public function login($login, $password)
        {
            return true;
        }

        // 接続情報 (server, username, password)
        public function credentials()
        {
            return ['localhost', 'root', 'root'];
        }

        // 最初から開くデータベース
        public function database()
        {
            return 'floppy_io';
        }

        public function name()
        {
            return 'floppy.io DB';
        }
    }

    return new FloppyAdminer;
}

include __DIR__ . '/adminer.php';
