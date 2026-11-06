-- ============================================================
-- floppy.io — 返信（リプライ）＋ 32×32 アイコン機能の追加マイグレーション
--
-- 既存のデータベースに 1 回だけ適用してください:
--   mysql -u root -p < database/migrations/2026-11-05-replies.sql
-- 新規に database/schema.sql から作る場合は不要です。
-- ============================================================

USE floppy_io;

-- 32×32 のプロフィールアイコン (1024 文字の 16 進文字列)。空は未設定。
-- 返信の受け付け (0 = オフ / 1 = オン)。既定はオフ＝返信できない。
ALTER TABLE users
  ADD COLUMN icon_pixel VARCHAR(1024) NOT NULL DEFAULT '' AFTER avatar_height,
  ADD COLUMN allow_replies TINYINT(1) NOT NULL DEFAULT 0 AFTER icon_pixel;

-- 返信先スレッドのルート投稿 ID。NULL は通常投稿。
ALTER TABLE posts
  ADD COLUMN reply_to_id INT UNSIGNED NULL DEFAULT NULL AFTER user_id,
  ADD KEY idx_posts_reply (reply_to_id);
