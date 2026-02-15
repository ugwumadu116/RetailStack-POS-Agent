# QA Testing Guide - RetailStack POS Agent

## Quick Setup (Mac)

### Option 1: Run directly
```bash
python3 --version   # Use 3.9 or newer
cd RetailStackPosAgent
pip install -r requirements.txt
python main.py
```

### Option 2: Build .app (double-click to run)
```bash
cd RetailStackPosAgent
pip install pyinstaller
pyinstaller build.spec --clean
# Output is in the dist/ folder
```

---

## Quick Setup (Windows)

### Option 1: Run directly
```cmd
python --version
cd RetailStackPosAgent
pip install -r requirements.txt
python main.py
```

### Option 2: Build .exe
```cmd
cd RetailStackPosAgent
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

---

## Testing the Agent

**Send test data:**
```bash
echo "Item 1  2 x 500" | nc localhost 9100
```

**Check the database:** The agent writes transactions to `retailstack_pos.db`.

**View logs:** Open `logs/retailstack.log` (same folder as the app on Windows).

---

## Troubleshooting

**Module not found:** Run `pip install pyserial requests python-dateutil`

**Port already in use:** Another app is using port 9100. Close it or change the port in config.json.

**No data captured:** Allow port 9100 in the firewall. For a real printer, send its output to this computer on port 9100. For testing, use the command above.

---

## What to Test

1. Agent starts without errors
2. Screen shows "Listening on port 9100"
3. Sending test data creates a transaction
4. Multiple transactions are stored correctly
5. Database has correct receipt ID, items, and total
6. Agent still works after restart

---

## Support

Contact: Joel Ugwumadu
