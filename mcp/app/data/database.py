from contextlib import contextmanager
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from app.core import tenancy
from app.core.config import AppConfig
from app.data.tenants import TenantSchemas, use_space

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
CREATE TABLE IF NOT EXISTS drive_connection (
 singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK(singleton), email TEXT NOT NULL,
 encrypted_refresh_token TEXT NOT NULL, connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS drive_import_jobs (
 job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), folder_id TEXT NOT NULL, folder_name TEXT NOT NULL,
 recursive BOOLEAN NOT NULL DEFAULT TRUE, status TEXT NOT NULL DEFAULT 'queued', total INTEGER NOT NULL DEFAULT 0,
 error TEXT, current_item TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS drive_import_files (
 job_id UUID NOT NULL REFERENCES drive_import_jobs(job_id) ON DELETE CASCADE, file_id TEXT NOT NULL,
 version TEXT, name TEXT NOT NULL, path TEXT, outcome TEXT NOT NULL, added INTEGER NOT NULL DEFAULT 0,
 matched INTEGER NOT NULL DEFAULT 0, rejected INTEGER NOT NULL DEFAULT 0, error TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY(job_id,file_id)
);
CREATE INDEX IF NOT EXISTS drive_import_files_seen_idx ON drive_import_files(file_id,outcome);
"""
class Database:
    def __init__(self, url):
        self.pool=ConnectionPool(url, min_size=1, max_size=AppConfig.DB_POOL_MAX_SIZE, open=False)
        self.tenants=TenantSchemas(self.pool.connection, lambda connection: connection.execute(SCHEMA))
    def open(self): self.pool.open(wait=True)
    def close(self): self.pool.close()
    def initialize(self):
        self.tenants.adopt_public_tables()
    @contextmanager
    def cursor(self):
        user_id=tenancy.current(); self.tenants.ensure(user_id)
        with self.pool.connection() as conn:
            use_space(conn,user_id)
            with conn.cursor(row_factory=dict_row) as cursor:
                yield cursor