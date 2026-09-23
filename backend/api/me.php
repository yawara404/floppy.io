<?php
declare(strict_types=1);

/**
 * floppy.io — ログイン中ユーザー取得 API
 *
 * GET /api/me.php  (Authorization: Bearer <token>)
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
    respond_error('Method Not Allowed', 405);
}

$user = require_user();

respond_json(['user' => public_user($user)]);
