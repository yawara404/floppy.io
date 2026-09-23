<?php
declare(strict_types=1);

/**
 * floppy.io — 投稿削除 API (容量解放 / 「フォーマット」)
 *
 * POST /api/delete_post.php  { "id": 123 }
 *
 * 自分の投稿のみ削除できる。画像が付いていれば実ファイルも削除する。
 */

require_once __DIR__ . '/../config/database.php';

$method = $_SERVER['REQUEST_METHOD'] ?? 'POST';

if ($method === 'POST' || $method === 'DELETE') {
    $user  = require_user();
    $input = read_json_body();
    $id    = (int) ($input['id'] ?? 0);

    if ($id <= 0) {
        respond_error('投稿 ID が不正です。', 400);
    }

    $pdo  = db();
    $stmt = $pdo->prepare(
        'SELECT image_path, floppy_path FROM posts WHERE id = ? AND user_id = ?'
    );
    $stmt->execute([$id, $user['id']]);
    $row = $stmt->fetch();

    if ($row === false) {
        respond_error('投稿が見つかりません。', 404);
    }

    $imagePath  = (string) $row['image_path'];
    $floppyPath = (string) $row['floppy_path'];

    $stmt = $pdo->prepare('DELETE FROM posts WHERE id = ? AND user_id = ?');
    $stmt->execute([$id, $user['id']]);

    delete_uploaded_image($imagePath);
    delete_uploaded_image($floppyPath);

    respond_json(['deleted' => $id]);
}

respond_error('Method Not Allowed', 405);
