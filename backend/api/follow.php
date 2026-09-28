<?php
declare(strict_types=1);

/**
 * floppy.io — フォロー API
 *
 * POST /api/follow.php  { "username": "wawa404" }  または { "id": 4 }
 *
 * ログイン中のユーザーが対象ユーザーをフォローする / 外す（トグル）。
 * レスポンス: { "following": true|false, "follower_count": 3 }
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond_error('Method Not Allowed', 405);
}

$user  = require_user();
$input = read_json_body();

$username = trim((string) ($input['username'] ?? ''));
$id       = (int) ($input['id'] ?? 0);

if ($username === '' && $id <= 0) {
    respond_error('フォローするユーザーを指定してください。', 400);
}

$pdo = db();

if ($username !== '') {
    $stmt = $pdo->prepare('SELECT id FROM users WHERE username = ?');
    $stmt->execute([$username]);
} else {
    $stmt = $pdo->prepare('SELECT id FROM users WHERE id = ?');
    $stmt->execute([$id]);
}

$target = $stmt->fetch();

if (!$target) {
    respond_error('ユーザーが見つかりません。', 404);
}

$targetId = (int) $target['id'];

if ($targetId === (int) $user['id']) {
    respond_error('自分自身はフォローできません。', 400);
}

if (is_following((int) $user['id'], $targetId)) {
    $pdo->prepare('DELETE FROM follows WHERE follower_id = ? AND followee_id = ?')
        ->execute([$user['id'], $targetId]);
    $following = false;
} else {
    $pdo->prepare('INSERT INTO follows (follower_id, followee_id) VALUES (?, ?)')
        ->execute([$user['id'], $targetId]);
    $following = true;
}

respond_json([
    'following'      => $following,
    'follower_count' => follow_stats($targetId)['follower_count'],
]);
