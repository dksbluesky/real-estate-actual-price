from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    record_id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    district TEXT NOT NULL,
    address TEXT NOT NULL,
    address_normalized TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    transaction_target TEXT,
    total_price INTEGER,
    unit_price_sqm REAL,
    building_area_sqm REAL,
    floor TEXT,
    total_floors TEXT,
    building_type TEXT,
    completion_date TEXT,
    rooms INTEGER,
    halls INTEGER,
    bathrooms INTEGER,
    parking_type TEXT,
    parking_price INTEGER,
    notes TEXT,
    source_period TEXT NOT NULL,
    imported_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transactions_area_date
    ON transactions(city, district, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_address
    ON transactions(address_normalized);
CREATE TABLE IF NOT EXISTS imports (
    source_period TEXT PRIMARY KEY,
    source_url TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    row_count INTEGER NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.executescript(SCHEMA)
    return connection

