<?php
declare(strict_types=1);

/**
 * floppy.io — プロフィール更新 API
 *
 * POST /api/update_profile.php  { "display_name": "Alice", "bio": "..." }
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond_error('Method Not Allowed', 405);
}

$user  = require_user();
$input = read_json_body();

$displayName = trim((string) ($input['display_name'] ?? ''));
$bio         = trim((string) ($input['bio'] ?? ''));

if ($displayName === '') {
    respond_error('表示名を入力してください。', 400);
}

if (mb_strlen($displayName) > 64) {
    respond_error('表示名は 64 文字以内にしてください。', 400);
}

if (mb_strlen($bio) > 300) {
    respond_error('bio は 300 文字以内にしてください。', 400);
}

$pdo  = db();
$stmt = $pdo->prepare('UPDATE users SET display_name = ?, bio = ? WHERE id = ?');
$stmt->execute([$displayName, $bio, $user['id']]);

$stmt = $pdo->prepare('SELECT ' . USER_COLUMNS . ' FROM users WHERE id = ?');
$stmt->execute([$user['id']]);

respond_json(['user' => public_user($stmt->fetch())]);
