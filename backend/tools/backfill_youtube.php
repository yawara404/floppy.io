<?php
declare(strict_types=1);

/**
 * floppy.io — YouTube メタ情報のバックフィル
 *
 * YouTube Data API のキーを後から設定した場合など、
 * youtube_id は保存済みだが youtube_title が空の投稿に対して
 * 動画タイトル・サムネイルを取り直して更新する。
 *
 * 使い方:
 *   php backend/tools/backfill_youtube.php
 */

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../config/youtube.php';

if (!youtube_api_enabled()) {
    fwrite(STDERR, "YouTube API キーが未設定です。\n");
    fwrite(STDERR, "backend/config/youtube.php の YOUTUBE_API_KEY か、環境変数 FLOPPY_YOUTUBE_API_KEY を設定してください。\n");
    exit(1);
}

$pdo = db();

$rows = $pdo->query(
    "SELECT id, youtube_id FROM posts
      WHERE youtube_id <> '' AND youtube_title = ''
      ORDER BY id"
)->fetchAll();

if ($rows === []) {
    echo "対象の投稿はありません。\n";
    exit(0);
}

echo count($rows) . " 件を更新します。\n";

$update = $pdo->prepare(
    'UPDATE posts SET youtube_title = ?, youtube_thumbnail = ? WHERE id = ?'
);

$ok = 0;
$ng = 0;

foreach ($rows as $row) {
    $videoId = (string) $row['youtube_id'];
    $meta    = youtube_fetch_metadata($videoId);

    if ($meta === null) {
        echo "  #{$row['id']} {$videoId} ... 取得失敗\n";
        $ng++;
        continue;
    }

    $update->execute([
        mb_substr($meta['title'], 0, 255),
        $meta['thumbnail'] !== '' ? $meta['thumbnail'] : youtube_thumbnail_url($videoId),
        (int) $row['id'],
    ]);

    echo "  #{$row['id']} {$videoId} ... {$meta['title']}\n";
    $ok++;
}

echo "完了: 更新 {$ok} 件 / 失敗 {$ng} 件\n";
