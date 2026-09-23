<?php
declare(strict_types=1);

/**
 * floppy.io — プロフィール画像の更新 API
 *
 * POST /api/update_avatar.php   (multipart/form-data)
 *   avatar : 画像ファイル (JPEG / PNG / GIF / WebP)
 *   remove : "1" を送ると現在の画像を削除する
 *
 * 要ログイン。画像は backend/uploads/ に保存し、古い画像は削除する。
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond_error('Method Not Allowed', 405);
}

$user = require_user();
$pdo  = db();

$remove = (string) ($_POST['remove'] ?? '') === '1';

// 現在の画像ファイル名
$stmt = $pdo->prepare('SELECT avatar_path FROM users WHERE id = ?');
$stmt->execute([$user['id']]);
$current = (string) $stmt->fetchColumn();

// 画像を外す場合
if ($remove) {
    $stmt = $pdo->prepare(
        'UPDATE users
            SET avatar_path = \'\', avatar_mime = \'\', avatar_bytes = 0,
                avatar_width = 0, avatar_height = 0
          WHERE id = ?'
    );
    $stmt->execute([$user['id']]);

    delete_uploaded_image($current);

    $stmt = $pdo->prepare('SELECT ' . USER_COLUMNS . ' FROM users WHERE id = ?');
    $stmt->execute([$user['id']]);

    respond_json(['user' => public_user($stmt->fetch())]);
}

// 画像を設定する場合
if (!isset($_FILES['avatar'])) {
    respond_error('画像が選択されていません。', 400);
}

$upload = validate_uploaded_image($_FILES['avatar']);

if ($upload['error'] !== null) {
    respond_error($upload['error'], 400);
}

if ((int) ($upload['bytes'] ?? 0) <= 0) {
    respond_error('画像が選択されていません。', 400);
}

// プロフィール画像は投稿の容量制限とは別だが、常識的な上限を設ける
if ((int) $upload['bytes'] > DISK_LIMIT_BYTES) {
    respond_error('プロフィール画像は 1.44MB 以内にしてください。', 400);
}

$path = store_uploaded_image($upload);

if ($path === null) {
    respond_error('画像の保存に失敗しました。', 500);
}

$stmt = $pdo->prepare(
    'UPDATE users
        SET avatar_path = ?, avatar_mime = ?, avatar_bytes = ?,
            avatar_width = ?, avatar_height = ?
      WHERE id = ?'
);
$stmt->execute([
    $path,
    $upload['mime'],
    (int) $upload['bytes'],
    (int) $upload['width'],
    (int) $upload['height'],
    $user['id'],
]);

// 置き換え前の画像を削除する
delete_uploaded_image($current);

$stmt = $pdo->prepare('SELECT ' . USER_COLUMNS . ' FROM users WHERE id = ?');
$stmt->execute([$user['id']]);

respond_json(['user' => public_user($stmt->fetch())]);
