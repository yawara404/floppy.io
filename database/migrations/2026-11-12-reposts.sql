-- ============================================================
-- floppy.io — リポスト (mixi 方式の再共有) テーブル追加
-- 適用: mysql -u root -p floppy_io < database/migrations/2026-11-12-reposts.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS reposts (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  post_id    INT UNSIGNED NOT NULL,
  user_id    INT UNSIGNED NOT NULL,
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_reposts_post_user (post_id, user_id),
  KEY idx_reposts_user (user_id),
  KEY idx_reposts_created (created_at),
  CONSTRAINT fk_reposts_post FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
  CONSTRAINT fk_reposts_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
