-- ============================================================
-- floppy.io — ドット絵キャンバス拡張マイグレーション
--   16×16 → 32×32（正方形）/ 32×24（Miiverse 風）に対応する
--
-- 既存のデータベースに 1 回だけ適用してください:
--   mysql -u root -p < database/migrations/2026-11-06-canvas.sql
-- 新規に database/schema.sql から作る場合は不要です。
-- ============================================================

USE floppy_io;

ALTER TABLE posts
  MODIFY COLUMN pixel_data VARCHAR(4096) NOT NULL,
  ADD COLUMN pixel_width SMALLINT UNSIGNED NOT NULL DEFAULT 16 AFTER pixel_data,
  ADD COLUMN pixel_height SMALLINT UNSIGNED NOT NULL DEFAULT 16 AFTER pixel_width;
