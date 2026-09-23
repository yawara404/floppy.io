<?php

declare(strict_types=1);

/**
 * floppy.io — YouTube Data API v3 連携
 *
 * 投稿の本文に YouTube の URL が含まれていると、動画 ID を抜き出して
 * 埋め込み表示用のメタ情報（タイトル・サムネイル）を保存する。
 *
 * API キーが未設定でも、URL から動画 ID を抜き出して埋め込みは動作する
 * （サムネイルは i.ytimg.com の固定 URL を使い、タイトルは取得しない）。
 *
 * API キーの設定方法:
 *   1. Google Cloud Console で「YouTube Data API v3」を有効化
 *   2. API キーを発行
 *   3. 下の YOUTUBE_API_KEY に貼り付ける、または環境変数
 *      FLOPPY_YOUTUBE_API_KEY を設定する（環境変数が優先）
 */

// キーは環境変数 FLOPPY_YOUTUBE_API_KEY か、
// コミット対象外の ./youtube.local.php で設定する（公開リポジトリに含めないため）
const YOUTUBE_API_KEY = '';

/** API キーを取得する (環境変数 > 定数) */
function youtube_api_key(): string
{
    // 1) 環境変数が最優先
    $key = getenv('FLOPPY_YOUTUBE_API_KEY');

    if ($key !== false && $key !== '') {
        return $key;
    }

    // 2) コミット対象外のローカル設定（backend/config/youtube.local.php）
    $local = __DIR__ . '/youtube.local.php';

    if (is_file($local)) {
        $config = require $local;

        if (is_array($config) && !empty($config['api_key'])) {
            return (string) $config['api_key'];
        }
    }

    // 3) 最終フォールバック（通常は空）
    return YOUTUBE_API_KEY;
}

/** YouTube Data API を使えるか */
function youtube_api_enabled(): bool
{
    return youtube_api_key() !== '';
}

/**
 * テキスト中から最初の YouTube 動画 ID (11 文字) を抜き出す。
 * watch / youtu.be / embed / shorts / v に対応。
 */
function youtube_video_id(string $text): ?string
{
    $pattern = '~(?:youtube\.com/(?:watch\?(?:[^\s]*&)?v=|embed/|shorts/|v/)|youtu\.be/)'
        . '([A-Za-z0-9_-]{11})~i';

    return preg_match($pattern, $text, $m) ? $m[1] : null;
}

/**
 * 動画 ID からサムネイル URL を組み立てる (API が使えないときのフォールバック)。
 */
function youtube_thumbnail_url(string $videoId): string
{
    return 'https://i.ytimg.com/vi/' . rawurlencode($videoId) . '/hqdefault.jpg';
}

/**
 * YouTube Data API v3 で動画情報を取得する。
 * キー未設定・通信失敗・動画が存在しない場合は null を返す (投稿は止めない)。
 *
 * @return array{title:string,thumbnail:string}|null
 */
function youtube_fetch_metadata(string $videoId): ?array
{
    if (!youtube_api_enabled()) {
        return null;
    }

    $url = 'https://www.googleapis.com/youtube/v3/videos'
        . '?part=snippet&id=' . rawurlencode($videoId)
        . '&key=' . rawurlencode(youtube_api_key());

    $raw = youtube_http_get($url);

    if ($raw === null) {
        return null;
    }

    $data = json_decode($raw, true);
    $item = $data['items'][0]['snippet'] ?? null;

    if (!is_array($item)) {
        return null;
    }

    $thumbs = $item['thumbnails'] ?? [];
    $thumb  = $thumbs['medium']['url']
        ?? $thumbs['high']['url']
        ?? $thumbs['default']['url']
        ?? '';

    return [
        'title'     => (string) ($item['title'] ?? ''),
        'thumbnail' => (string) $thumb,
    ];
}

/** シンプルな GET (cURL があれば優先) */
function youtube_http_get(string $url): ?string
{
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 2,
            CURLOPT_TIMEOUT        => 4,
            CURLOPT_FOLLOWLOCATION => true,
        ]);
        $body = curl_exec($ch);
        $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        // PHP 8.5 で curl_close() は非推奨 (no-op) のため呼び出さない

        return ($body !== false && $code === 200) ? (string) $body : null;
    }

    $context = stream_context_create([
        'http' => ['timeout' => 4, 'ignore_errors' => true],
    ]);
    $body = @file_get_contents($url, false, $context);

    return is_string($body) && $body !== '' ? $body : null;
}

/**
 * 投稿本文から YouTube の埋め込み情報を組み立てる。
 *
 * @return array{id:string,title:string,thumbnail:string}
 */
function youtube_embed_info(string $text): array
{
    $videoId = youtube_video_id($text);

    if ($videoId === null) {
        return ['id' => '', 'title' => '', 'thumbnail' => ''];
    }

    $meta = youtube_fetch_metadata($videoId);

    return [
        'id'        => $videoId,
        'title'     => $meta !== null ? mb_substr($meta['title'], 0, 255) : '',
        'thumbnail' => ($meta['thumbnail'] ?? '') !== ''
            ? $meta['thumbnail']
            : youtube_thumbnail_url($videoId),
    ];
}
