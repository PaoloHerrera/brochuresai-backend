PRAGMA foreign_keys = ON;

-- Create brochure analytics table for usage insights
CREATE TABLE IF NOT EXISTS brochure_analytics (
  id INTEGER PRIMARY KEY,
  anon_id TEXT NOT NULL,
  url_domain TEXT NOT NULL,
  company_name TEXT,
  company_name_length INTEGER DEFAULT 0,
  brochure_type TEXT NOT NULL,
  language TEXT NOT NULL,
  success BOOLEAN NOT NULL DEFAULT 0,
  processing_time_ms INTEGER,
  error_type TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (anon_id) REFERENCES users (anon_id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_analytics_anon_id ON brochure_analytics (anon_id);
CREATE INDEX IF NOT EXISTS idx_analytics_domain ON brochure_analytics (url_domain);
CREATE INDEX IF NOT EXISTS idx_analytics_success ON brochure_analytics (success);
CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON brochure_analytics (created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_type_lang ON brochure_analytics (brochure_type, language);