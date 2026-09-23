-- ============================================================
-- floppy.io — 1.44MB レトロSNS データベーススキーマ (MySQL 8.x)
-- 文字コード: utf8mb4
-- ============================================================

CREATE DATABASE IF NOT EXISTS floppy_io
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE floppy_io;

-- ------------------------------------------------------------
-- ユーザー
-- パスワードは password_hash() (bcrypt) のハッシュのみ保存する。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id            INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  username      VARCHAR(32)      NOT NULL,
  display_name  VARCHAR(64)      NOT NULL DEFAULT '',
  bio           VARCHAR(300)     NOT NULL DEFAULT '',
  -- プロフィール画像 (backend/uploads/ の実ファイル名)
  avatar_path   VARCHAR(255)     NOT NULL DEFAULT '',
  avatar_mime   VARCHAR(64)      NOT NULL DEFAULT '',
  avatar_bytes  INT UNSIGNED     NOT NULL DEFAULT 0,
  avatar_width  SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  avatar_height SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  password_hash VARCHAR(255)     NOT NULL DEFAULT '',
  created_at    TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- API トークン (Bearer 認証)
-- Cookie を使わないため、Live Server からのクロスオリジンでも動く。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_tokens (
  id         INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  user_id    INT UNSIGNED     NOT NULL,
  token      CHAR(64)         NOT NULL,
  created_at TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tokens_token (token),
  KEY idx_tokens_user (user_id),
  CONSTRAINT fk_tokens_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 投稿
-- pixel_data: 16×16=256 マスを 1 マス = 1 桁の 16 進文字 (0-9A-F)
-- で表した 256 文字の文字列。わずか 256 バイトでドット絵を保存する。
-- text_bytes / pixel_bytes / total_bytes は投稿時の実消費バイト数。
-- 容量制限は「1 投稿あたり 1.44MB」。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS posts (
  id           INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  user_id      INT UNSIGNED     NOT NULL,
  -- 1 投稿あたり最大 1.44MB を保存できるよう MEDIUMTEXT (最大 16MB) を使う
  text         MEDIUMTEXT       NOT NULL,
  -- CHAR の上限は 255 文字のため、256 文字の 16 進文字列は VARCHAR で保持する
  pixel_data   VARCHAR(256)     NOT NULL,
  -- 画像は backend/uploads/ に実ファイルとして保存し、そのファイル名を保持する
  image_path   VARCHAR(255)     NOT NULL DEFAULT '',
  image_mime   VARCHAR(64)      NOT NULL DEFAULT '',
  image_bytes  INT UNSIGNED     NOT NULL DEFAULT 0,
  image_width  SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  image_height SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  -- 本文に YouTube の URL があれば動画 ID とメタ情報を保持する
  youtube_id        VARCHAR(32)  NOT NULL DEFAULT '',
  youtube_title     VARCHAR(255) NOT NULL DEFAULT '',
  youtube_thumbnail VARCHAR(255) NOT NULL DEFAULT '',
  text_bytes   INT UNSIGNED     NOT NULL DEFAULT 0,
  pixel_bytes  INT UNSIGNED     NOT NULL DEFAULT 256,
  total_bytes  INT UNSIGNED     NOT NULL DEFAULT 0,
  created_at   TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_posts_user    (user_id),
  KEY idx_posts_created (created_at),
  CONSTRAINT fk_posts_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- デモユーザー (username: floppy / password: floppy)
-- ------------------------------------------------------------
INSERT IGNORE INTO users (id, username, display_name, bio, password_hash) VALUES (
  1,
  'floppy',
  'floppy.io',
  '1.44MB しか使えない静寂のレトロ SNS。1 投稿＝フロッピー 1 枚。',
  '$2y$12$ut11TeVexp6K4F55U5l8suZ4KGWMWkTTs99vMq32FIYo7W9gwP4mC'
);
