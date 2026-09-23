<?php
declare(strict_types=1);

/**
 * floppy.io — いいね API
 *
 * POST /api/like.php  { "id": 123 }
 *
 * ログイン中のユーザーが対象投稿にいいねを付ける / 外す（トグル）。
 * レスポンス: { "liked": true|false, "like_count": 3 }
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond_error('Method Not Allowed', 405);
}

$user  = require_user();
$input = read_json_body();
$id    = (int) ($input['id'] ?? 0);

if ($id <= 0) {
    respond_error('投稿 ID が不正です。', 400);
}

$pdo = db();

$stmt = $pdo->prepare('SELECT id FROM posts WHERE id = ?');
$stmt->execute([$id]);

if (!$stmt->fetch()) {
    respond_error('投稿が見つかりません。', 404);
}

$stmt = $pdo->prepare('SELECT 1 FROM likes WHERE post_id = ? AND user_id = ?');
$stmt->execute([$id, $user['id']]);

if ($stmt->fetch()) {
    $pdo->prepare('DELETE FROM likes WHERE post_id = ? AND user_id = ?')
        ->execute([$id, $user['id']]);
    $liked = false;
} else {
    $pdo->prepare('INSERT INTO likes (post_id, user_id) VALUES (?, ?)')
        ->execute([$id, $user['id']]);
    $liked = true;
}

respond_json([
    'liked'      => $liked,
    'like_count' => like_count($id),
]);
