<?php
declare(strict_types=1);

/**
 * floppy.io — 投稿 API
 *
 * GET  /api/posts.php[?username=floppy][&q=キーワード]
 *      投稿一覧 (新しい順)。username で絞り込み、q で本文・ユーザー名を検索。
 *
 * POST /api/posts.php
 *      JSON               { text, pixel_data }
 *      multipart/form-data { text, pixel_data, image? }
 *      要ログイン / 1 投稿あたり 1.44MB の容量判定あり。
 */

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../config/youtube.php';

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

/** LIKE 検索用に % _ \ をエスケープする */
function like_escape(string $value): string
{
    return str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $value);
}

/** 投稿行に画像 / フロッピーファイルの URL を付与する */
function with_image_url(array $row): array
{
    $row['image_url']  = post_image_url($row);
    $row['floppy_url']  = post_floppy_url($row);
    $row['floppy_kind'] = $row['floppy_name'] !== '' ? floppy_kind($row['floppy_name']) : null;

    return $row;
}

const POST_COLUMNS = 'p.id,
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
            p.floppy_path,
            p.floppy_name,
            p.floppy_bytes,
            p.text_bytes,
            p.pixel_bytes,
            p.total_bytes,
            p.created_at';

// ---------------------------------------------------------------------------
// GET: 投稿一覧取得 (?username= で絞り込み / ?q= で検索)
// ---------------------------------------------------------------------------
if ($method === 'GET') {
    $username = trim((string) ($_GET['username'] ?? ''));
    $query    = trim((string) ($_GET['q'] ?? ''));

    $sql    = 'SELECT ' . POST_COLUMNS . '
                 FROM posts p
                 JOIN users u ON u.id = p.user_id';
    $where  = [];
    $params = [];

    if ($username !== '') {
        $where[]  = 'u.username = ?';
        $params[] = $username;
    }

    if ($query !== '') {
        $like   = '%' . like_escape($query) . '%';
        $where[] = '(p.text LIKE ? OR u.username LIKE ? OR u.display_name LIKE ?)';
        array_push($params, $like, $like, $like);
    }

    if ($where !== []) {
        $sql .= ' WHERE ' . implode(' AND ', $where);
    }

    $sql .= ' ORDER BY p.created_at DESC, p.id DESC LIMIT 200';

    $stmt = db()->prepare($sql);
    $stmt->execute($params);

    $posts = array_map('with_image_url', $stmt->fetchAll());
    $posts = attach_likes($posts, current_user());

    respond_json(['posts' => $posts]);
}

// ---------------------------------------------------------------------------
// POST: 新規投稿 (容量判定)
// ---------------------------------------------------------------------------
if ($method === 'POST') {
    $user = require_user();

    $contentType = (string) ($_SERVER['CONTENT_TYPE'] ?? '');
    $isMultipart = str_starts_with($contentType, 'multipart/form-data');

    if ($isMultipart) {
        $text  = (string) ($_POST['text'] ?? '');
        $pixel = normalize_pixel_data($_POST['pixel_data'] ?? null);
    } else {
        $input = read_json_body();
        $text  = (string) ($input['text'] ?? '');
        $pixel = normalize_pixel_data($input['pixel_data'] ?? null);
    }

    // 画像 (任意)
    $upload = ['error' => null, 'bytes' => 0];
    if ($isMultipart && isset($_FILES['image'])) {
        $upload = validate_uploaded_image($_FILES['image']);
        if ($upload['error'] !== null) {
            respond_error($upload['error'], 400);
        }
    }

    $hasImage = (int) ($upload['bytes'] ?? 0) > 0;

    // フロッピーファイル (任意)
    $floppy = ['error' => null, 'bytes' => 0];
    if ($isMultipart && isset($_FILES['floppy'])) {
        $floppy = validate_uploaded_floppy($_FILES['floppy']);
        if ($floppy['error'] !== null) {
            respond_error($floppy['error'], 400);
        }
    }

    $hasFloppy = (int) ($floppy['bytes'] ?? 0) > 0;

    // 本文もドット絵も画像も無いなら弾く
    if ($text === '' && is_blank_pixel($pixel) && !$hasImage && !$hasFloppy) {
        respond_error('本文・ドット絵・画像・フロッピーファイルのいずれかを入力してください。', 400);
    }

    // UTF-8 バイト長 (strlen) で実消費量を計算する
    $textBytes  = strlen($text);
    $pixelBytes = strlen($pixel);          // 常に 256
    $imageBytes  = (int) ($upload['bytes'] ?? 0);
    $floppyBytes = (int) ($floppy['bytes'] ?? 0);
    $totalBytes  = $textBytes + $pixelBytes + $imageBytes + $floppyBytes;

    // 容量制限は「1 投稿あたり」。累計では制限しない。
    // 1 投稿の合計 (本文 + ドット絵 + 画像) が 1.44MB を超える場合は HTTP 403。
    if ($totalBytes > DISK_LIMIT_BYTES) {
        respond_error(
            '1 投稿あたりの容量上限（1.44MB）を超えています。'
            . '（本文 ' . number_format($textBytes) . ' + ドット絵 ' . number_format($pixelBytes)
            . ' + 画像 ' . number_format($imageBytes)
            . ' + フロッピー ' . number_format($floppyBytes) . ' bytes）',
            403
        );
    }

    // 容量チェックを通ってから画像を保存する
    $imagePath = '';
    if ($hasImage) {
        $imagePath = store_uploaded_image($upload);
        if ($imagePath === null) {
            respond_error('画像の保存に失敗しました。', 500);
        }
    }

    // フロッピーファイルを保存する（容量チェック後）
    $floppyPath = '';
    if ($hasFloppy) {
        $floppyPath = store_uploaded_floppy($floppy);
        if ($floppyPath === null) {
            delete_uploaded_image($imagePath);
            respond_error('ファイルの保存に失敗しました。', 500);
        }
    }

    // 本文に YouTube の URL があれば埋め込み用のメタ情報を取得する
    // (API キー未設定でも動画 ID とサムネイルは保存される)
    $youtube = youtube_embed_info($text);

    $pdo = db();

    try {
        $stmt = $pdo->prepare(
            'INSERT INTO posts
                (user_id, text, pixel_data, image_path, image_mime, image_bytes,
                 image_width, image_height, youtube_id, youtube_title, youtube_thumbnail,
                 floppy_path, floppy_name, floppy_bytes,
                 text_bytes, pixel_bytes, total_bytes)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        );
        $stmt->execute([
            $user['id'],
            $text,
            $pixel,
            $imagePath,
            $hasImage ? $upload['mime'] : '',
            $imageBytes,
            $hasImage ? $upload['width'] : 0,
            $hasImage ? $upload['height'] : 0,
            $youtube['id'],
            $youtube['title'],
            $youtube['thumbnail'],
            $floppyPath,
            $hasFloppy ? $floppy['name'] : '',
            $floppyBytes,
            $textBytes,
            $pixelBytes,
            $totalBytes,
        ]);
    } catch (Throwable $e) {
        delete_uploaded_image($imagePath);
        delete_uploaded_image($floppyPath);
        respond_error('投稿の保存に失敗しました。', 500);
    }

    $id = (int) $pdo->lastInsertId();

    $stmt = $pdo->prepare(
        'SELECT ' . POST_COLUMNS . '
           FROM posts p
           JOIN users u ON u.id = p.user_id
          WHERE p.id = ?'
    );
    $stmt->execute([$id]);

    respond_json(['post' => with_image_url($stmt->fetch())], 201);
}

respond_error('Method Not Allowed', 405);
