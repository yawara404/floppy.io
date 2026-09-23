<?php
declare(strict_types=1);

/**
 * floppy.io — ログイン API
 *
 * POST /api/login.php  { "username": "alice", "password": "secret" }
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond_error('Method Not Allowed', 405);
}

$input    = read_json_body();
$username = trim((string) ($input['username'] ?? ''));
$password = (string) ($input['password'] ?? '');

if ($username === '' || $password === '') {
    respond_error('ユーザー名とパスワードを入力してください。', 400);
}

$pdo  = db();
$stmt = $pdo->prepare(
    'SELECT ' . USER_COLUMNS . ', password_hash
       FROM users
      WHERE username = ?'
);
$stmt->execute([$username]);
$row = $stmt->fetch();

if (!$row || $row['password_hash'] === '' || !password_verify($password, $row['password_hash'])) {
    respond_error('ユーザー名またはパスワードが違います。', 401);
}

$token = issue_token((int) $row['id']);

respond_json([
    'token' => $token,
    'user'  => public_user($row),
]);
