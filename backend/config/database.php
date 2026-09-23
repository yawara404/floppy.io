<?php
declare(strict_types=1);

/**
 * floppy.io — DB 接続 & 共通ヘルパー
 *
 * MySQL への PDO 接続と、REST API で共通利用する JSON レスポンス /
 * エラーレスポンス / リクエストボディ読み取りヘルパーを提供する。
 */

// ---------------------------------------------------------------------------
// 接続設定
//
// 既定値は MAMP / MAMP PRO (Apache :8888 / MySQL :8889, root / root) に合わせている。
//
// MAMP PRO は MySQL の TCP を無効化していることがある（skip_networking=ON）ため、
// 接続は「unix ソケット → TCP」の順に試す。ソケットが無い環境では TCP になる。
//
// 環境変数 FLOPPY_DB_* で上書きできる:
//   FLOPPY_DB_PORT=3306 FLOPPY_DB_PASS= php -S localhost:8000
// ---------------------------------------------------------------------------
function env_value(string $key, string $default): string
{
    $value = getenv($key);

    return ($value === false || $value === '') ? $default : $value;
}

define('DB_HOST', env_value('FLOPPY_DB_HOST', '127.0.0.1'));
define('DB_PORT', (int) env_value('FLOPPY_DB_PORT', '8889'));
define('DB_NAME', env_value('FLOPPY_DB_NAME', 'floppy_io'));
define('DB_USER', env_value('FLOPPY_DB_USER', 'root'));
define('DB_PASS', env_value('FLOPPY_DB_PASS', 'root'));

// MAMP / MAMP PRO の MySQL ソケット (存在すれば優先して使う)
define('DB_SOCKET', env_value('FLOPPY_DB_SOCKET', '/Applications/MAMP/tmp/mysql/mysql.sock'));

// ---------------------------------------------------------------------------
// 1.44MB フロッピーディスクの容量制限 (バイト)
//   1.44 MB = 1,474,560 Bytes
// ---------------------------------------------------------------------------
const DISK_LIMIT_BYTES = 1474560;

// ---------------------------------------------------------------------------
// CORS 設定 (開発時の Vite / Live Server からのアクセスを許可)
// ---------------------------------------------------------------------------
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ---------------------------------------------------------------------------
// PDO 接続 (シングルトン)
//
// MAMP PRO は MySQL の TCP を無効化していることがあるので、
// unix ソケットが存在すればそれを優先し、失敗したら TCP にフォールバックする。
// ---------------------------------------------------------------------------
function db(): PDO
{
    static $pdo = null;

    if ($pdo !== null) {
        return $pdo;
    }

    $options = [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ];

    $targets = [];

    if (DB_SOCKET !== '' && @file_exists(DB_SOCKET)) {
        $targets[] = 'unix_socket=' . DB_SOCKET;
    }

    $targets[] = sprintf('host=%s;port=%d', DB_HOST, DB_PORT);

    $error = null;

    foreach ($targets as $target) {
        try {
            $pdo = new PDO(
                'mysql:' . $target . ';dbname=' . DB_NAME . ';charset=utf8mb4',
                DB_USER,
                DB_PASS,
                $options
            );

            return $pdo;
        } catch (PDOException $e) {
            $error = $e;
        }
    }

    throw $error ?? new PDOException('MySQL に接続できませんでした。');
}

// ---------------------------------------------------------------------------
// JSON レスポンスを返して終了
// ---------------------------------------------------------------------------
function respond_json(array $data, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

// ---------------------------------------------------------------------------
// エラーレスポンスを返して終了
// ---------------------------------------------------------------------------
function respond_error(string $message, int $status = 400): void
{
    respond_json(['error' => $message], $status);
}

// ---------------------------------------------------------------------------
// リクエストボディ (JSON) を配列として読み取る
// ---------------------------------------------------------------------------
function read_json_body(): array
{
    $raw  = file_get_contents('php://input');
    $data = json_decode($raw !== false ? $raw : '', true);

    return is_array($data) ? $data : [];
}

// ---------------------------------------------------------------------------
// 16 色パレット (ドット絵のインデックス → 色)
// 文字 '0'〜'9','A'〜'F' がインデックス 0〜15 に対応する。
// ---------------------------------------------------------------------------
const PIXEL_PALETTE = [
    0  => '#ffffff', // 白
    1  => '#c0c0c0', // ライトグレー
    2  => '#808080', // グレー
    3  => '#000000', // 黒
    4  => '#ff0000', // 赤
    5  => '#800000', // 暗赤
    6  => '#ffff00', // 黄
    7  => '#808000', // オリーブ
    8  => '#00ff00', // 緑
    9  => '#008000', // 暗緑
    10 => '#00ffff', // シアン
    11 => '#008080', // ティール
    12 => '#0000ff', // 青
    13 => '#000080', // 紺
    14 => '#ff00ff', // マゼンタ
    15 => '#800080', // 紫
];

// ---------------------------------------------------------------------------
// pixel_data (256 文字) を正規化する。不正なら全透明 (0) を返す。
// ---------------------------------------------------------------------------
function normalize_pixel_data(?string $pixel): string
{
    if ($pixel !== null && preg_match('/^[0-9A-Fa-f]{256}$/', $pixel)) {
        return strtoupper($pixel);
    }

    return str_repeat('0', 256);
}

// ---------------------------------------------------------------------------
// pixel_data が「全マス透明(0)」かどうか
// ---------------------------------------------------------------------------
function is_blank_pixel(string $pixel): bool
{
    return trim($pixel, '0') === '';
}

// ---------------------------------------------------------------------------
// pixel_data から自己完結型 SVG (埋め込みプレビュー用) を生成する
// ---------------------------------------------------------------------------
function pixel_svg(string $pixel, int $cell = 8): string
{
    $size = 16 * $cell;
    $svg  = '<svg xmlns="http://www.w3.org/2000/svg" width="' . $size
          . '" height="' . $size . '" shape-rendering="crispEdges" viewBox="0 0 '
          . $size . ' ' . $size . '">';

    for ($i = 0; $i < 256; $i++) {
        $idx = hexdec($pixel[$i]);
        $x   = ($i % 16) * $cell;
        $y   = intdiv($i, 16) * $cell;
        $svg .= '<rect x="' . $x . '" y="' . $y . '" width="' . $cell
              . '" height="' . $cell . '" fill="' . PIXEL_PALETTE[$idx] . '"/>';
    }

    return $svg . '</svg>';
}

// ---------------------------------------------------------------------------
// 認証 (Bearer トークン)
//
// Cookie ではなくトークンを使うため、Live Server のような別オリジンからでも
// Authorization ヘッダを付けるだけで認証できる。
// ---------------------------------------------------------------------------

/** リクエストヘッダから Bearer トークンを取り出す */
function bearer_token(): ?string
{
    $header = $_SERVER['HTTP_AUTHORIZATION']
        ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION']
        ?? '';

    if ($header === '' && function_exists('getallheaders')) {
        foreach (getallheaders() as $name => $value) {
            if (strcasecmp((string) $name, 'Authorization') === 0) {
                $header = (string) $value;
                break;
            }
        }
    }

    return preg_match('/Bearer\s+(\S+)/i', $header, $m) ? $m[1] : null;
}

/** トークンに紐づくユーザーを返す (未ログインなら null) */
function find_user_by_token(?string $token): ?array
{
    if ($token === null || $token === '') {
        return null;
    }

    $stmt = db()->prepare(
        'SELECT u.id, u.username, u.display_name, u.bio,
                u.avatar_path, u.avatar_mime, u.avatar_bytes,
                u.avatar_width, u.avatar_height, u.created_at
           FROM api_tokens t
           JOIN users u ON u.id = t.user_id
          WHERE t.token = ?'
    );
    $stmt->execute([$token]);
    $user = $stmt->fetch();

    return $user ?: null;
}

/** 現在ログイン中のユーザー (1 リクエスト内でキャッシュ) */
function current_user(): ?array
{
    static $loaded = false;
    static $user   = null;

    if (!$loaded) {
        $loaded = true;
        $user   = find_user_by_token(bearer_token());
    }

    return $user;
}

/** ログイン必須エンドポイント用。未ログインなら 401 で終了する。 */
function require_user(): array
{
    $user = current_user();

    if ($user === null) {
        respond_error('ログインが必要です。', 401);
    }

    return $user;
}

/** 新しい API トークンを発行する */
function issue_token(int $userId): string
{
    $token = bin2hex(random_bytes(32));

    $stmt = db()->prepare('INSERT INTO api_tokens (user_id, token) VALUES (?, ?)');
    $stmt->execute([$userId, $token]);

    return $token;
}

/** ユーザーの投稿統計 (合計 / 件数 / 最大) */
function user_stats(int $userId): array
{
    $stmt = db()->prepare(
        'SELECT COALESCE(SUM(total_bytes), 0),
                COUNT(*),
                COALESCE(MAX(total_bytes), 0)
           FROM posts
          WHERE user_id = ?'
    );
    $stmt->execute([$userId]);
    [$total, $count, $largest] = $stmt->fetch(PDO::FETCH_NUM);

    return [
        'total_bytes'        => (int) $total,
        'post_count'         => (int) $count,
        'largest_post_bytes' => (int) $largest,
    ];
}

/** ユーザーの最新投稿のドット絵 (アイコン代わり)。無ければ null。 */
function user_avatar_pixel(int $userId): ?string
{
    // ドット絵が描かれていない (全て 0) 投稿は飛ばす
    $stmt = db()->prepare(
        'SELECT pixel_data FROM posts
          WHERE user_id = ? AND pixel_data <> REPEAT(\'0\', 256)
          ORDER BY created_at DESC, id DESC LIMIT 1'
    );
    $stmt->execute([$userId]);
    $pixel = $stmt->fetchColumn();

    return is_string($pixel) ? $pixel : null;
}

/** API レスポンス用にユーザー情報を整形する */
function public_user(array $row, bool $withStats = true): array
{
    $id = (int) $row['id'];

    $user = [
        'id'           => $id,
        'username'     => $row['username'],
        'display_name' => $row['display_name'] !== '' ? $row['display_name'] : $row['username'],
        'bio'          => $row['bio'],
        'created_at'   => $row['created_at'],
        // プロフィール画像 (未設定なら null)
        'avatar_url'   => user_avatar_url($row),
        // 画像が無いときのフォールバック (最新投稿のドット絵)
        'avatar_pixel' => user_avatar_pixel($id),
    ];

    return $withStats ? $user + user_stats($id) : $user;
}

/** users テーブルの共通 SELECT 列 */
const USER_COLUMNS = 'id, username, display_name, bio,
    avatar_path, avatar_mime, avatar_bytes, avatar_width, avatar_height,
    created_at';

/** ユーザー名の妥当性チェック (半角英数字とアンダースコア 3〜20 文字) */
function is_valid_username(string $username): bool
{
    return (bool) preg_match('/^[A-Za-z0-9_]{3,20}$/', $username);
}

// ---------------------------------------------------------------------------
// 画像アップロード
//
// 画像は backend/uploads/ に実ファイルとして保存し、そのバイト数も
// 1 投稿あたりの容量 (1.44MB) に含める。
// ---------------------------------------------------------------------------

/** 許可する画像形式 (MIME => 拡張子) */
const ALLOWED_IMAGE_TYPES = [
    'image/jpeg' => 'jpg',
    'image/png'  => 'png',
    'image/gif'  => 'gif',
    'image/webp' => 'webp',
];

/** 画像の保存先ディレクトリ */
function upload_dir(): string
{
    return __DIR__ . '/../uploads';
}

/**
 * uploads ディレクトリの公開 URL を組み立てる。
 * MAMP: http://localhost:8888/floppy_io/uploads
 * php -S: http://localhost:8000/uploads
 */
function uploads_base_url(): string
{
    $scheme = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
    $host   = $_SERVER['HTTP_HOST'] ?? 'localhost';
    $script = str_replace('\\', '/', $_SERVER['SCRIPT_NAME'] ?? '/api/posts.php');
    $base   = rtrim(dirname(dirname($script)), '/');

    return $scheme . '://' . $host . $base . '/uploads';
}

/** 投稿行に画像 URL を付与する */
function post_image_url(array $row): ?string
{
    return !empty($row['image_path'])
        ? uploads_base_url() . '/' . rawurlencode($row['image_path'])
        : null;
}

/** ユーザー行にプロフィール画像 URL を付与する */
function user_avatar_url(array $row): ?string
{
    return !empty($row['avatar_path'])
        ? uploads_base_url() . '/' . rawurlencode($row['avatar_path'])
        : null;
}

/**
 * アップロードされた画像を検証する (ファイルはまだ移動しない)。
 *
 * @return array{error:?string,tmp?:string,mime?:string,bytes?:int,width?:int,height?:int}
 */
function validate_uploaded_image(array $file): array
{
    $error = $file['error'] ?? UPLOAD_ERR_NO_FILE;

    if ($error === UPLOAD_ERR_NO_FILE) {
        return ['error' => null, 'bytes' => 0];
    }

    if ($error !== UPLOAD_ERR_OK) {
        $message = match ($error) {
            UPLOAD_ERR_INI_SIZE, UPLOAD_ERR_FORM_SIZE => '画像が大きすぎます。',
            UPLOAD_ERR_PARTIAL                        => '画像のアップロードが中断されました。',
            UPLOAD_ERR_NO_TMP_DIR                     => '一時保存先が見つかりません。',
            UPLOAD_ERR_CANT_WRITE                     => '画像を書き込めませんでした。',
            default                                   => '画像のアップロードに失敗しました。',
        };

        return ['error' => $message];
    }

    $size = (int) ($file['size'] ?? 0);
    if ($size <= 0) {
        return ['error' => '画像が空です。'];
    }

    $info = @getimagesize((string) ($file['tmp_name'] ?? ''));
    if ($info === false) {
        return ['error' => '画像として読み込めないファイルです。'];
    }

    $mime = (string) ($info['mime'] ?? '');
    if (!isset(ALLOWED_IMAGE_TYPES[$mime])) {
        return ['error' => '対応していない画像形式です（JPEG / PNG / GIF / WebP）。'];
    }

    return [
        'error'  => null,
        'tmp'    => (string) $file['tmp_name'],
        'mime'   => $mime,
        'bytes'  => $size,
        'width'  => (int) $info[0],
        'height' => (int) $info[1],
    ];
}

/** 検証済みの画像を uploads/ に移動し、ファイル名を返す */
function store_uploaded_image(array $validated): ?string
{
    $dir = upload_dir();

    if (!is_dir($dir) && !@mkdir($dir, 0775, true)) {
        return null;
    }

    $name = bin2hex(random_bytes(16)) . '.' . ALLOWED_IMAGE_TYPES[$validated['mime']];
    $dest = $dir . '/' . $name;

    if (!move_uploaded_file($validated['tmp'], $dest)) {
        return null;
    }

    return $name;
}

/** 保存済みの画像ファイルを削除する */
function delete_uploaded_image(?string $name): void
{
    if ($name === null || $name === '') {
        return;
    }

    $path = upload_dir() . '/' . basename($name);
    if (is_file($path)) {
        @unlink($path);
    }
}
