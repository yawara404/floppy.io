CREATE TABLE IF NOT EXISTS steam_accounts (
  user_id INT UNSIGNED PRIMARY KEY,
  steam_id CHAR(17) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  show_in_disks BOOLEAN NOT NULL DEFAULT FALSE,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS steam_link_states (
  state_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  browser_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  user_id INT UNSIGNED NOT NULL,
  steam_id CHAR(17) CHARACTER SET ascii COLLATE ascii_bin NULL,
  expires_at DATETIME NOT NULL,
  KEY idx_steam_states_expiry (expires_at),
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;
