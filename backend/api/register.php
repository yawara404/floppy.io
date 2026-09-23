<?php
declare(strict_types=1);

/**
 * floppy.io — ユーザー登録 API
 *
 * POST /api/register.php  { "username": "alice", "password": "secret", "display_name": "Alice" }
 *
 * 成功時はトークンを発行してそのままログイン状態にする。
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond_error('Method Not Allowed', 405);
}

$input       = read_json_body();
$username    = trim((string) ($input['username'] ?? ''));
$password    = (string) ($input['password'] ?? '');
$displayName = trim((string) ($input['display_name'] ?? ''));

if (!is_valid_username($username)) {
    respond_error('ユーザー名は半角英数字とアンダースコア (_) の 3〜20 文字で入力してください。', 400);
}

if (strlen($password) < 6) {
    respond_error('パスワードは 6 文字以上にしてください。', 400);
}

if (mb_strlen($displayName) > 64) {
    respond_error('表示名は 64 文字以内にしてください。', 400);
}

$pdo = db();

$stmt = $pdo->prepare('SELECT id FROM users WHERE username = ?');
$stmt->execute([$username]);
if ($stmt->fetch()) {
    respond_error('このユーザー名は既に使われています。', 409);
}

$stmt = $pdo->prepare(
    'INSERT INTO users (username, display_name, bio, password_hash)
     VALUES (?, ?, ?, ?)'
);
$stmt->execute([
    $username,
    $displayName !== '' ? $displayName : $username,
    '',
    password_hash($password, PASSWORD_BCRYPT),
]);

$userId = (int) $pdo->lastInsertId();
$token  = issue_token($userId);

$stmt = $pdo->prepare('SELECT ' . USER_COLUMNS . ' FROM users WHERE id = ?');
$stmt->execute([$userId]);

respond_json([
    'token' => $token,
    'user'  => public_user($stmt->fetch()),
], 201);
