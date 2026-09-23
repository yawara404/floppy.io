<?php
declare(strict_types=1);

/**
 * floppy.io — パスワード変更 API
 *
 * POST /api/change_password.php  { "current_password": "old", "new_password": "new" }
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond_error('Method Not Allowed', 405);
}

$user  = require_user();
$input = read_json_body();

$current = (string) ($input['current_password'] ?? '');
$new     = (string) ($input['new_password'] ?? '');

if (strlen($new) < 6) {
    respond_error('新しいパスワードは 6 文字以上にしてください。', 400);
}

$pdo  = db();
$stmt = $pdo->prepare('SELECT password_hash FROM users WHERE id = ?');
$stmt->execute([$user['id']]);
$hash = (string) $stmt->fetchColumn();

if ($hash === '' || !password_verify($current, $hash)) {
    respond_error('現在のパスワードが違います。', 400);
}

$stmt = $pdo->prepare('UPDATE users SET password_hash = ? WHERE id = ?');
$stmt->execute([password_hash($new, PASSWORD_BCRYPT), $user['id']]);

respond_json(['ok' => true]);
