<?php
declare(strict_types=1);

/**
 * floppy.io — ディスク容量取得 API
 *
 * GET /api/disk_usage.php[?username=floppy]
 *
 * 容量制限は「1 投稿あたり 1.44MB」なので、上限は投稿単位。
 * ここでは上限の情報に加えて、指定ユーザー（省略時は全ユーザー）の
 * 保存済み投稿の合計（参考値）を返す。
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
    respond_error('Method Not Allowed', 405);
}

$pdo      = db();
$username = trim((string) ($_GET['username'] ?? ''));

$sql = 'SELECT COALESCE(SUM(total_bytes), 0),
               COUNT(*),
               COALESCE(MAX(total_bytes), 0)
          FROM posts';
$params = [];

if ($username !== '') {
    $sql .= ' JOIN users u ON u.id = posts.user_id WHERE u.username = ?';
    $params[] = $username;
}

$stmt = $pdo->prepare($sql);
$stmt->execute($params);
[$totalBytes, $postCount, $largestPostBytes] = $stmt->fetch(PDO::FETCH_NUM);

respond_json([
    // 1 投稿あたりの上限
    'limit_bytes'        => DISK_LIMIT_BYTES,
    'limit_scope'        => 'post',
    'username'           => $username !== '' ? $username : null,
    // 保存済み投稿の合計（制限対象ではない参考値）
    'total_bytes'        => (int) $totalBytes,
    'post_count'         => (int) $postCount,
    'largest_post_bytes' => (int) $largestPostBytes,
]);
