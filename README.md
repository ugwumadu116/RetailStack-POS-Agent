# RetailStack POS Agent

Desktop application that intercepts ESC/POS receipt printer data, parses sales transactions, and syncs to Retail Stack servers.

## Quick Install

### Mac / Linux
```bash
curl -fsSL https://raw.githubusercontent.com/ugwumadu116/RetailStack-POS-Agent/main/install.sh | bash
```

### Windows
```powershell
irm https://raw.githubusercontent.com/ugwumadu116/RetailStack-POS-Agent/main/install.ps1 | iex
```

Or manually:
```cmd
cd RetailStackPosAgent
pip install -r requirements.txt
python main.py
```

---

## What It Does

- Intercepts ESC/POS data from thermal receipt printers
- Parses: item names, quantities, prices, totals, receipt IDs
- Stores transactions locally in SQLite
- Detects sequence gaps (missing receipts)
- Crash recovery - replays unsynced data on restart

---

## Testing

Send test data:
```bash
echo "Item 1  2 x 500" | nc localhost 9100
```

---

## Files

- `main.py` - Main application
- `src/` - Source code modules
- `config.json` - Configuration
- `QA.md` - Testing guide for QA team

---

## Support

Contact: Joel Ugwumadu
