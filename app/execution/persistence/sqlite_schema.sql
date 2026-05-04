-- SQLite schema for Execution Engine persistence
-- Run once to initialize the DB (e.g., sqlite3 execution.db < sqlite_schema.sql)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,               -- internal order_id (UUID)
    client_order_id TEXT,              -- optional idempotency key
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    type TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL,
    stop_price REAL,
    time_in_force TEXT,
    strategy TEXT,
    status TEXT NOT NULL,
    filled_qty REAL DEFAULT 0.0,
    remaining_qty REAL DEFAULT 0.0,
    created_at INTEGER NOT NULL,       -- epoch seconds
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_client_order_id ON orders(client_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    filled_qty REAL NOT NULL,
    fill_price REAL NOT NULL,
    fee REAL NOT NULL,
    timestamp INTEGER NOT NULL,
    raw_payload TEXT,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fills_order_id ON fills(order_id);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    event_payload TEXT NOT NULL,       -- JSON string
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    mid_price REAL NOT NULL,
    avg_depth REAL NOT NULL,
    timestamp INTEGER NOT NULL
);

-- Optional: simple key-value config table for runtime flags
CREATE TABLE IF NOT EXISTS kv_store (
    key TEXT PRIMARY KEY,
    value TEXT
);
