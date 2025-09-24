PRAGMA foreign_keys = ON;

-- Create example table 'users'
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  ip_address TEXT,
  anon_id TEXT,
  brochures_count INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

-- Helpful index for lookups
CREATE INDEX IF NOT EXISTS idx_users_anon_id ON users (anon_id);
CREATE INDEX IF NOT EXISTS idx_users_ip_address ON users (ip_address);