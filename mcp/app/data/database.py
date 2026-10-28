from contextlib import contextmanager
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from app.core.config import AppConfig

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
 id BIGSERIAL PRIMARY KEY, occurred_at TIMESTAMPTZ NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
 amount NUMERIC(14,2) NOT NULL CHECK(amount > 0), currency CHAR(3) NOT NULL DEFAULT 'INR',
 merchant TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Uncategorized',
 account TEXT, notes TEXT, source TEXT NOT NULL DEFAULT 'manual',
 external_id TEXT UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS transactions_occurred_idx ON transactions(occurred_at);
CREATE TABLE IF NOT EXISTS commitments (
 id BIGSERIAL PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('emi','sip')),
 name TEXT NOT NULL, amount NUMERIC(14,2) NOT NULL CHECK(amount > 0),
 day_of_month SMALLINT NOT NULL CHECK(day_of_month BETWEEN 1 AND 31),
 start_date DATE NOT NULL, end_date DATE, active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS goals (
 id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, target_amount NUMERIC(14,2) NOT NULL,
 current_amount NUMERIC(14,2) NOT NULL DEFAULT 0, target_date DATE NOT NULL,
 priority TEXT NOT NULL DEFAULT 'medium', notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS reminders (
 id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, due_at TIMESTAMPTZ NOT NULL,
 recurrence TEXT NOT NULL DEFAULT 'none', entity_type TEXT NOT NULL DEFAULT 'general',
 entity_id BIGINT, completed BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS gmail_connections (
 email TEXT PRIMARY KEY, encrypted_refresh_token TEXT NOT NULL,
 last_history_id TEXT, last_sync_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS gmail_imports (
 message_id TEXT PRIMARY KEY, email TEXT NOT NULL, subject TEXT, sender TEXT,
 received_at TIMESTAMPTZ, status TEXT NOT NULL, excerpt TEXT,
 transaction_id BIGINT REFERENCES transactions(id) ON DELETE SET NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""
class Database:
    def __init__(self, url):
        self.pool=ConnectionPool(url, min_size=1, max_size=AppConfig.DB_POOL_MAX_SIZE, open=False)
    def open(self): self.pool.open(wait=True)
    def close(self): self.pool.close()
    def initialize(self):
        with self.cursor() as c: c.execute(SCHEMA)
    @contextmanager
    def cursor(self):
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                yield cursor