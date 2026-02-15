# RetailStack POS Agent

Desktop application that intercepts ESC/POS receipt printer data, parses sales transactions, and syncs to Retail Stack servers.

## Quick Install

### Option 1: Download ZIP (Recommended)
1. Go to: https://github.com/ugwumadu116/RetailStack-POS-Agent/archive/refs/heads/main.zip
2. Download and extract the ZIP
3. Open terminal in the extracted folder
4. Run: `bash install.sh`

### Option 2: Clone with Git
```bash
git clone https://github.com/ugwumadu116/RetailStack-POS-Agent.git
cd RetailStack-POS-Agent
bash install.sh
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

## Logs

Logs are saved to: `logs/retailstack.log`

---

## Support

Contact: Joel Ugwumadu
