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
  -- プロフィールアイコン用のドット絵 (32×32 = 1024 文字の 16 進文字列)。空は未設定。
  icon_pixel    VARCHAR(1024)    NOT NULL DEFAULT '',
  -- 返信の受け付け (0 = オフ / 1 = オン)。既定はオフ＝返信できない。
  allow_replies TINYINT(1)       NOT NULL DEFAULT 0,
  password_hash VARCHAR(255)     NOT NULL DEFAULT '',
  created_at    TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- ディスク (コミュニティ)
-- 1 ディスク = 1 枚のフロッピー。同じ趣味の書き込みを 1 枚に集める。
-- slug は URL (/d/:slug) に使う半角英数字とハイフン。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS disks (
  id          INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  slug        VARCHAR(32)   NOT NULL,
  name        VARCHAR(64)   NOT NULL,
  description VARCHAR(300)  NOT NULL DEFAULT '',
  owner_id    INT UNSIGNED  NOT NULL,
  created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_disks_slug (slug),
  KEY idx_disks_owner (owner_id),
  CONSTRAINT fk_disks_owner FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- API トークン (Bearer 認証)
-- トークンは SHA-256 ハッシュとして保存する (平文は保存しない)。
-- Cookie を使わないため、同一オリジン / クロスオリジンの両方で動く。
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
-- pixel_data: ドット絵キャンバスを 1 マス = 1 桁の 16 進文字 (0-9A-F)
-- で表した文字列。キャンバスは pixel_width × pixel_height。
--   16×16 = 256 文字（クラシック）
--   32×32 = 1024 文字（正方形）
--   32×24 = 768 文字（Miiverse 風 4:3）
-- text_bytes / pixel_bytes / total_bytes は投稿時の実消費バイト数。
-- 容量制限は「1 投稿あたり 1.44MB」。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS posts (
  id           INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  user_id      INT UNSIGNED     NOT NULL,
  -- 返信先スレッドのルート投稿 ID。NULL は通常投稿。
  -- 返信への返信も同じスレッド（ルート）にまとめる（フラットなスレッド）。
  reply_to_id  INT UNSIGNED     NULL DEFAULT NULL,
  -- 書き込み先のディスク (コミュニティ)。NULL はホーム。
  disk_id      INT UNSIGNED     NULL DEFAULT NULL,
  -- 1 投稿あたり最大 1.44MB を保存できるよう MEDIUMTEXT (最大 16MB) を使う
  text         MEDIUMTEXT       NOT NULL,
  -- ドット絵 (最大 64×64 まで拡張できるよう VARCHAR(4096))
  pixel_data   VARCHAR(4096)    NOT NULL,
  pixel_width  SMALLINT UNSIGNED NOT NULL DEFAULT 16,
  pixel_height SMALLINT UNSIGNED NOT NULL DEFAULT 16,
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
  -- 添付フロッピーファイル (実ファイルは backend/uploads/ に保存)
  floppy_path       VARCHAR(255) NOT NULL DEFAULT '',
  floppy_name       VARCHAR(255) NOT NULL DEFAULT '',
  floppy_bytes      INT UNSIGNED NOT NULL DEFAULT 0,
  text_bytes   INT UNSIGNED     NOT NULL DEFAULT 0,
  pixel_bytes  INT UNSIGNED     NOT NULL DEFAULT 256,
  total_bytes  INT UNSIGNED     NOT NULL DEFAULT 0,
  created_at   TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_posts_user    (user_id),
  KEY idx_posts_created (created_at),
  KEY idx_posts_reply   (reply_to_id),
  KEY idx_posts_disk    (disk_id),
  CONSTRAINT fk_posts_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_posts_disk FOREIGN KEY (disk_id) REFERENCES disks (id) ON DELETE SET NULL
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


-- ------------------------------------------------------------
-- いいね
-- 1 ユーザー 1 投稿につき 1 件。投稿が消えれば連動して消える。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS likes (
  post_id    INT UNSIGNED NOT NULL,
  user_id    INT UNSIGNED NOT NULL,
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (post_id, user_id),
  KEY idx_likes_user (user_id),
  CONSTRAINT fk_likes_post FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
  CONSTRAINT fk_likes_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- フォロー
-- follower_id が followee_id をフォローする (1 組 1 件)。
-- どちらかのユーザーが消えれば連動して消える。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS follows (
  follower_id INT UNSIGNED NOT NULL,
  followee_id INT UNSIGNED NOT NULL,
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (follower_id, followee_id),
  KEY idx_follows_followee (followee_id),
  CONSTRAINT fk_follows_follower FOREIGN KEY (follower_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_follows_followee FOREIGN KEY (followee_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- ディスクの参加メンバー
-- 1 ユーザー 1 ディスクにつき 1 件。ディスク / ユーザーが消えれば連動して消える。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS disk_members (
  disk_id    INT UNSIGNED NOT NULL,
  user_id    INT UNSIGNED NOT NULL,
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (disk_id, user_id),
  KEY idx_disk_members_user (user_id),
  CONSTRAINT fk_disk_members_disk FOREIGN KEY (disk_id) REFERENCES disks (id) ON DELETE CASCADE,
  CONSTRAINT fk_disk_members_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
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

-- ------------------------------------------------------------
-- デモディスク (コミュニティ)
-- ------------------------------------------------------------
INSERT IGNORE INTO disks (slug, name, description, owner_id) VALUES
  ('retro-pc', 'レトロPC', '9801、X68000、MSX。実機もエミュレータも歓迎の Old Computer 板。', 1),
  ('pixel-art', 'ドット絵', '16×16 から 32×32 まで。描いたドット絵と制作メモを 1 枚に。', 1),
  ('8bit-music', '8bit音楽', 'チップチューン、MIDI、PC-98 音源。書き出した曲をフロッピーに添えて。', 1);

INSERT IGNORE INTO disk_members (disk_id, user_id)
SELECT id, 1 FROM disks WHERE owner_id = 1;
