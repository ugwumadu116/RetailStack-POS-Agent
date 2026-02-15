# RetailStack POS Agent - Task Breakdown

**Completion summary:** All tasks from 1.2 onward are implemented. Optional: `pyproject.toml` and TASK-spec deps (pywin32/sqlalchemy) per 1.1.

---

## Phase 1: Core Interception & Parsing (This Weekend)

### Task 1.1: Project Setup
- [ ] Initialize Python project with `pyproject.toml`
- [x] Set up virtual environment
- [ ] Install dependencies: `pywin32`, `sqlalchemy`, `requests`, `pytest` — *project uses `requirements.txt` with `requests`, `pytest`, `pyserial`, `python-dateutil` (pywin32 optional for Windows port)*
- [x] Create project structure

### Task 1.2: ESC/POS Parser
- [x] Create `escpos_parser.py`
- [x] Implement byte stream parser for Epson commands
- [x] Handle text extraction (item names, prices)
- [x] Handle quantity extraction
- [x] Extract transaction ID and timestamp
- [x] Add Star and Bixolon variant support
- [x] Graceful handling of unknown commands (log raw bytes)
- [x] Write unit tests with sample ESC/POS dumps

### Task 1.3: Printer Interception
- [x] Create `printer_interceptor.py`
- [x] Implement USB port monitoring (pywin32) — *Windows COM port via pywin32; USB001 falls back to stdin*
- [x] OR create simple virtual printer approach — *network + serial + stdin fallback*
- [x] Capture raw ESC/POS byte stream
- [x] Pass to parser in real-time
- [x] Handle printer disconnection/reconnection — *serial/network reconnect loops; on_disconnect/on_reconnect callbacks*

### Task 1.4: Local Transaction Buffer
- [x] Create `transaction_buffer.py`
- [x] Set up SQLite database schema
- [x] Table: `transactions` (id, items_json, total, timestamp, synced, retry_count)
- [x] Table: `pending_sync` (transaction_id, payload, next_retry)
- [x] Write transaction to buffer immediately
- [x] Implement retry with exponential backoff — *in sync_client + buffer retry_count*

### Task 1.5: Gap Detection
- [x] Create `gap_detector.py`
- [x] Track receipt ID sequence per printer
- [x] Detect missing IDs immediately
- [x] Log alert with time window
- [x] Support multiple printers (scope per terminal)

## Phase 2: Sync & Recovery (Next Week)

### Task 2.1: Sync Client
- [x] Create `sync_client.py`
- [x] REST API client structure
- [x] POST /transactions endpoint — *uses `/api/transactions`*
- [x] Handle 200/400/500 responses
- [x] Confirm successful sync (mark as synced)

### Task 2.2: Crash Recovery
- [x] Create `recovery_manager.py`
- [x] On startup: load last sync timestamp
- [x] Replay unconfirmed transactions
- [x] Log downtime window
- [x] Update sequence tracking

### Task 2.3: Edge Case Handling
- [x] Log incomplete ESC/POS sessions
- [x] Handle voided/refunded transactions
- [x] Fuzzy product name matching stub — *`src/product_matcher.py`*
- [x] Multi-printer support (config file)

## Phase 3: Polish (Later)

### Task 3.1: Admin UI (Basic)
- [x] System tray icon — *`tray_icon.py` (optional: pystray, Pillow)*
- [x] Status display (connected/disconnected) — *`admin.py status` + tray*
- [x] Manual sync trigger — *`admin.py sync-now` + tray*
- [x] View recent transactions — *`admin.py recent` + tray*

### Task 3.2: Logging & Monitoring
- [x] Structured logging (python logging Log files rotation) — *`src/logging_config.py`*
- [x] Error alerting — *ErrorAlertHandler + set_error_alert_callback*

---

## Technical Notes

### ESC/POS Key Commands
- `GS` (0x1D) - Group separator
- `ESC` (0x1B) - Escape
- `LF` (0x0A) - Line feed
- `DLE` (0x10) - Data link escape
- Text between `LF` commands = line items
- Prices often in format: `1,000` or `1000.00`

### Sample ESC/POS Flow
```
ESC @           Initialize
ESC ! 00        Select print mode
ITEM NAME       Item text
1 x 500         Quantity x Price
                Line break
TOTAL: 5000     Total
```

### Database Schema
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    printer_id TEXT,
    receipt_id TEXT,
    items TEXT,  -- JSON array
    total REAL,
    timestamp DATETIME,
    synced BOOLEAN DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY,
    transaction_id INTEGER,
    synced_at DATETIME,
    response_code INTEGER
);
```

---

## Success Criteria This Weekend
1. Can intercept ESC/POS from test printer
2. Parser correctly extracts: item, qty, price, receipt ID
3. Data saved to SQLite
4. Gap detection logs alert
5. No crashes on normal operations
