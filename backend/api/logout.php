<?php
declare(strict_types=1);

/**
 * floppy.io — ログアウト API
 *
 * POST /api/logout.php  (Authorization: Bearer <token>)
 *
 * 使用中のトークンを無効化する。
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond_error('Method Not Allowed', 405);
}

require_user();

$token = bearer_token();
$stmt  = db()->prepare('DELETE FROM api_tokens WHERE token = ?');
$stmt->execute([$token]);

respond_json(['ok' => true]);
