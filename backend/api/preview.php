<?php
declare(strict_types=1);

/**
 * floppy.io — エコシステム連携用プレビュー API
 *
 * GET /api/preview.php?id=123
 *
 * 外部サービス (タイムライン埋め込み・OGP 展開など) 向けに、
 * 投稿のメタ情報と自己完結型の埋め込み HTML を返す。
 */

require_once __DIR__ . '/../config/database.php';

$id = (int) ($_GET['id'] ?? 0);

if ($id <= 0) {
    respond_error('投稿 ID が不正です。', 400);
}

$pdo  = db();
$stmt = $pdo->prepare(
    'SELECT p.id,
            u.username,
            u.display_name,
            p.text,
            p.pixel_data,
            p.image_path,
            p.image_bytes,
            p.image_width,
            p.image_height,
            p.youtube_id,
            p.youtube_title,
            p.youtube_thumbnail,
            p.total_bytes,
            p.created_at
       FROM posts p
       JOIN users u ON u.id = p.user_id
      WHERE p.id = ?'
);
$stmt->execute([$id]);
$post = $stmt->fetch();

if (!$post) {
    respond_error('投稿が見つかりません。', 404);
}

// ホスト名からベース URL を組み立てる
$scheme = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
$host   = $_SERVER['HTTP_HOST'] ?? 'localhost';
$base   = $scheme . '://' . $host;

$text  = htmlspecialchars($post['text'], ENT_QUOTES, 'UTF-8');
$name  = htmlspecialchars($post['username'], ENT_QUOTES, 'UTF-8');
$shown = htmlspecialchars(
    $post['display_name'] !== '' ? $post['display_name'] : $post['username'],
    ENT_QUOTES,
    'UTF-8'
);
$svg   = pixel_svg($post['pixel_data']);
$bytes = number_format((int) $post['total_bytes']);
$date  = htmlspecialchars($post['created_at'], ENT_QUOTES, 'UTF-8');

$imageUrl  = post_image_url($post);
$imageHtml = $imageUrl !== null
    ? '<div style="margin:6px 0"><img src="'
      . htmlspecialchars($imageUrl, ENT_QUOTES, 'UTF-8')
      . '" alt="" style="max-width:100%;display:block;border:1px solid #808080"></div>'
    : '';

// YouTube 埋め込み (サムネイルをリンクにした軽量版)
$youtubeHtml = '';
if (($post['youtube_id'] ?? '') !== '') {
    $videoId   = rawurlencode((string) $post['youtube_id']);
    $thumb     = htmlspecialchars(
        (string) ($post['youtube_thumbnail'] !== ''
            ? $post['youtube_thumbnail']
            : 'https://i.ytimg.com/vi/' . $videoId . '/hqdefault.jpg'),
        ENT_QUOTES,
        'UTF-8'
    );
    $videoUrl  = 'https://www.youtube.com/watch?v=' . $videoId;
    $youtubeTitle = htmlspecialchars(
        (string) ($post['youtube_title'] !== '' ? $post['youtube_title'] : 'YouTube'),
        ENT_QUOTES,
        'UTF-8'
    );
    $youtubeHtml = '<div style="margin:6px 0"><a href="' . $videoUrl
        . '" target="_blank" rel="noopener"><img src="' . $thumb
        . '" alt="" style="max-width:100%;display:block;border:1px solid #808080"></a>'
        . '<div style="font-size:11px;color:#404040">▶ ' . $youtubeTitle . '</div></div>';
}

// 自己完結型の埋め込みカード HTML
$html = <<<HTML
<div style="font-family:'Courier New',monospace;background:#c0c0c0;border:2px solid;border-color:#ffffff #808080 #808080 #ffffff;padding:12px;max-width:340px;color:#000">
  <div style="display:flex;gap:12px;align-items:flex-start">
    <div style="background:#ffffff;border:1px solid #808080;padding:3px;line-height:0">{$svg}</div>
    <div style="min-width:0">
      <div style="font-weight:bold;color:#000080">floppy.io</div>
      <div style="margin:6px 0;white-space:pre-wrap;word-break:break-word">{$text}</div>
      {$imageHtml}
      {$youtubeHtml}
      <div style="font-size:11px;color:#404040">{$shown} (@{$name}) · {$bytes} bytes · {$date}</div>
    </div>
  </div>
</div>
HTML;

respond_json([
    'type'         => 'floppy_io:post',
    'version'      => '1.0',
    'id'           => (int) $post['id'],
    'author'       => $post['username'],
    'author_name'  => $post['display_name'] !== '' ? $post['display_name'] : $post['username'],
    'text'         => $post['text'],
    'pixel_data'   => $post['pixel_data'],
    'pixel_svg'    => $svg,
    'image_url'    => $imageUrl,
    'image_bytes'  => (int) $post['image_bytes'],
    'youtube_id'   => (string) $post['youtube_id'],
    'youtube_title' => (string) $post['youtube_title'],
    'youtube_thumbnail' => (string) $post['youtube_thumbnail'],
    'total_bytes'  => (int) $post['total_bytes'],
    'created_at'   => $post['created_at'],
    'url'          => $base . '/api/preview.php?id=' . $post['id'],
    'html'         => $html,
]);
