<?php
declare(strict_types=1);

/**
 * floppy.io — ユーザープロフィール取得 API
 *
 * GET /api/user.php?username=floppy
 *
 * プロフィール情報と、そのユーザーの投稿一覧を返す。
 */

require_once __DIR__ . '/../config/database.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
    respond_error('Method Not Allowed', 405);
}

$username = trim((string) ($_GET['username'] ?? ''));

if ($username === '') {
    respond_error('ユーザー名を指定してください。', 400);
}

$pdo  = db();
$stmt = $pdo->prepare(
    'SELECT ' . USER_COLUMNS . '
       FROM users
      WHERE username = ?'
);
$stmt->execute([$username]);
$row = $stmt->fetch();

if (!$row) {
    respond_error('ユーザーが見つかりません。', 404);
}

$stmt = $pdo->prepare(
    'SELECT p.id,
            p.user_id,
            u.username,
            u.display_name,
            p.text,
            p.pixel_data,
            p.image_path,
            p.image_mime,
            p.image_bytes,
            p.image_width,
            p.image_height,
            p.youtube_id,
            p.youtube_title,
            p.youtube_thumbnail,
            p.text_bytes,
            p.pixel_bytes,
            p.total_bytes,
            p.created_at
       FROM posts p
       JOIN users u ON u.id = p.user_id
      WHERE p.user_id = ?
      ORDER BY p.created_at DESC, p.id DESC
      LIMIT 200'
);
$stmt->execute([$row['id']]);

$posts = array_map(static function (array $post): array {
    $post['image_url'] = post_image_url($post);

    return $post;
}, $stmt->fetchAll());

respond_json([
    'user'  => public_user($row),
    'posts' => $posts,
]);
