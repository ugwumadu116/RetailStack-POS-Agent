# Transaction Buffer - SQLite storage for RetailStack POS Agent
# Handles local storage with retry logic

import sqlite3
import json
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import asdict
import os


class TransactionBuffer:
    """SQLite-backed transaction buffer with retry logic"""
    
    DB_PATH = "retailstack_pos.db"
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_PATH
        self.lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id TEXT NOT NULL,
                    printer_id TEXT,
                    items_json TEXT,
                    subtotal REAL,
                    tax REAL,
                    total REAL,
                    timestamp TEXT,
                    synced INTEGER DEFAULT 0,
                    sync_error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    transaction_type TEXT DEFAULT 'sale',
                    is_incomplete INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Add new columns if table already existed (migration)
            for col, typ in [('transaction_type', 'TEXT'), ('is_incomplete', 'INTEGER')]:
                try:
                    cursor.execute(f'ALTER TABLE transactions ADD COLUMN {col} {typ}')
                except sqlite3.OperationalError:
                    pass  # column exists
            
            # Sync log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER,
                    synced_at TEXT,
                    response_code INTEGER,
                    response_body TEXT,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
                )
            ''')
            
            # Gap log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    printer_id TEXT,
                    expected_receipt_id TEXT,
                    missing_receipt_id TEXT,
                    detected_at TEXT,
                    resolved INTEGER DEFAULT 0,
                    resolution_note TEXT
                )
            ''')
            
            # State table for recovery
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            ''')
            
            # Pending sync queue (transaction_id, payload JSON, next_retry timestamp)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_sync (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    next_retry TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
                )
            ''')
            
            conn.commit()
            conn.close()
    
    def add_transaction(self, receipt_id: str, items: List[Dict],
                       total: float, subtotal: float = 0, tax: float = 0,
                       printer_id: str = None, transaction_type: str = 'sale',
                       is_incomplete: bool = False) -> int:
        """Add transaction to buffer"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            items_json = json.dumps(items)
            timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO transactions 
                (receipt_id, printer_id, items_json, subtotal, tax, total, timestamp,
                 transaction_type, is_incomplete)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (receipt_id, printer_id, items_json, subtotal, tax, total, timestamp,
                  transaction_type, 1 if is_incomplete else 0))
            
            tx_id = cursor.lastrowid
            # Enqueue to pending_sync for retry scheduling
            next_retry = datetime.now().isoformat()
            payload = json.dumps({
                'receipt_id': receipt_id, 'printer_id': printer_id,
                'items': items, 'subtotal': subtotal, 'tax': tax, 'total': total,
                'timestamp': timestamp,
            })
            cursor.execute('''
                INSERT INTO pending_sync (transaction_id, payload, next_retry)
                VALUES (?, ?, ?)
            ''', (tx_id, payload, next_retry))
            conn.commit()
            conn.close()
            
            return tx_id
    
    def get_pending_sync_queue(self, limit: int = 100) -> List[Dict]:
        """Get pending_sync rows due for retry (next_retry <= now)."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM pending_sync
                WHERE next_retry <= ?
                ORDER BY next_retry ASC
                LIMIT ?
            ''', (datetime.now().isoformat(), limit))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    def update_pending_sync_retry(self, pending_id: int, next_retry: str, increment: bool = True):
        """Update next_retry (and optionally increment retry_count) for a pending_sync row."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if increment:
                cursor.execute('''
                    UPDATE pending_sync
                    SET next_retry = ?, retry_count = retry_count + 1
                    WHERE id = ?
                ''', (next_retry, pending_id))
            else:
                cursor.execute('''
                    UPDATE pending_sync SET next_retry = ? WHERE id = ?
                ''', (next_retry, pending_id))
            conn.commit()
            conn.close()
    
    def remove_pending_sync(self, pending_id: int):
        """Remove a row from pending_sync (after successful sync)."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM pending_sync WHERE id = ?', (pending_id,))
            conn.commit()
            conn.close()
    
    def get_unsynced(self) -> List[Dict]:
        """Get all unsynced transactions"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM transactions 
                WHERE synced = 0 AND retry_count < 5
                ORDER BY created_at ASC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
    
    def mark_synced(self, tx_id: int, response_code: int = 200):
        """Mark transaction as synced"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE transactions SET synced = 1 WHERE id = ?
            ''', (tx_id,))
            
            # Log sync
            cursor.execute('''
                INSERT INTO sync_log (transaction_id, synced_at, response_code)
                VALUES (?, ?, ?)
            ''', (tx_id, datetime.now().isoformat(), response_code))
            # Remove from pending_sync when synced
            cursor.execute('DELETE FROM pending_sync WHERE transaction_id = ?', (tx_id,))
            conn.commit()
            conn.close()
    
    def mark_failed(self, tx_id: int, error: str):
        """Mark transaction as failed, increment retry count"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE transactions 
                SET sync_error = ?, retry_count = retry_count + 1 
                WHERE id = ?
            ''', (error, tx_id))
            
            conn.commit()
            conn.close()
    
    def get_receipt_ids(self, printer_id: str = None) -> List[str]:
        """Get all receipt IDs for gap detection"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if printer_id:
                cursor.execute('''
                    SELECT receipt_id FROM transactions 
                    WHERE printer_id = ? ORDER BY timestamp ASC
                ''', (printer_id,))
            else:
                cursor.execute('''
                    SELECT receipt_id FROM transactions ORDER BY timestamp ASC
                ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in rows]
    
    def log_gap(self, printer_id: str, expected: str, missing: str):
        """Log a sequence gap"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO gaps (printer_id, expected_receipt_id, missing_receipt_id, detected_at)
                VALUES (?, ?, ?, ?)
            ''', (printer_id, expected, missing, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
    
    def get_pending_gaps(self) -> List[Dict]:
        """Get unresolved gaps"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM gaps WHERE resolved = 0')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
    
    def resolve_gap(self, gap_id: int, note: str):
        """Mark gap as resolved"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE gaps SET resolved = 1, resolution_note = ? WHERE id = ?
            ''', (note, gap_id))
            
            conn.commit()
            conn.close()
    
    def save_state(self, key: str, value: Any):
        """Save state key-value"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO state (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, json.dumps(value), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
    
    def load_state(self, key: str, default: Any = None) -> Any:
        """Load state value"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM state WHERE key = ?', (key,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                try:
                    return json.loads(row[0])
                except:
                    return row[0]
            return default
    
    def get_stats(self) -> Dict:
        """Get buffer statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute('SELECT COUNT(*) FROM transactions')
            stats['total_transactions'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM transactions WHERE synced = 0')
            stats['pending_sync'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM pending_sync')
            stats['pending_sync_queue'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM gaps WHERE resolved = 0')
            stats['open_gaps'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT MAX(timestamp) FROM transactions WHERE synced = 1')
            stats['last_sync'] = cursor.fetchone()[0]
            
            conn.close()
            return stats


if __name__ == '__main__':
    # Test
    buffer = TransactionBuffer('test.db')
    
    # Add test transaction
    items = [
        {'name': 'Item 1', 'quantity': 2, 'unit_price': 500, 'total': 1000},
        {'name': 'Item 2', 'quantity': 1, 'unit_price': 1500, 'total': 1500}
    ]
    
    tx_id = buffer.add_transaction('RCT001', items, 2500, 2500, 0)
    print(f"Added transaction {tx_id}")
    
    # Get stats
    print(buffer.get_stats())
    
    # Get unsynced
    print(buffer.get_unsynced())
