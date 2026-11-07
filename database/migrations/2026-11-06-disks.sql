-- ============================================================
-- floppy.io — ディスク (コミュニティ) 追加マイグレーション
--   「フォロー中」タイムラインを、フロッピー 1 枚に見立てた
--   コミュニティ「ディスク」に置き換える。
--
-- 既存のデータベースに 1 回だけ適用してください:
--   mysql -u root -p < database/migrations/2026-11-06-disks.sql
-- 新規に database/schema.sql から作る場合は不要です。
-- ============================================================

USE floppy_io;

-- ディスク本体
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

-- 参加メンバー
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

-- 投稿の書き込み先（NULL はホーム）
ALTER TABLE posts
  ADD COLUMN disk_id INT UNSIGNED NULL DEFAULT NULL AFTER reply_to_id,
  ADD KEY idx_posts_disk (disk_id),
  ADD CONSTRAINT fk_posts_disk FOREIGN KEY (disk_id) REFERENCES disks (id) ON DELETE SET NULL;

-- デモディスク (任意。不要ならこの 3 行を削除してください)
INSERT IGNORE INTO disks (slug, name, description, owner_id) VALUES
  ('retro-pc', 'レトロPC', '9801、X68000、MSX。実機もエミュレータも歓迎の Old Computer 板。', 1),
  ('pixel-art', 'ドット絵', '16×16 から 32×32 まで。描いたドット絵と制作メモを 1 枚に。', 1),
  ('8bit-music', '8bit音楽', 'チップチューン、MIDI、PC-98 音源。書き出した曲をフロッピーに添えて。', 1);

INSERT IGNORE INTO disk_members (disk_id, user_id)
SELECT id, 1 FROM disks WHERE owner_id = 1;
