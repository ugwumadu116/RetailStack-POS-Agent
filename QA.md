# QA Testing Guide - RetailStack POS Agent

## Quick Setup (Mac)

### Option 1: Run directly
```bash
# 1. Install Python if not installed
python3 --version  # Should show 3.9+

# 2. Clone or download project
cd RetailStackPosAgent

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python main.py
```

### Option 2: Build .app (double-click to run)
```bash
cd RetailStackPosAgent
pip install pyinstaller
pyinstaller build.spec --clean
# App will be in dist/ folder
```

---

## Quick Setup (Windows)

### Option 1: Run directly
```cmd
:: 1. Install Python (download from python.org)
python --version  :: Should show 3.9+

:: 2. Download project and extract
cd RetailStackPosAgent

:: 3. Install dependencies
pip install -r requirements.txt

:: 4. Run the app
python main.py
```

### Option 2: Build .exe
```cmd
cd RetailStackPosAgent
pip install pyinstaller
pyinstaller --onefile --windowed main.py
:: .exe will be in dist/ folder
```

---

## Testing the Agent

### Method 1: Simulate printer data
```bash
# Send test receipt data to the agent
echo "Item 1  2 x 500" | nc localhost 9100
```

### Method 2: Check the database
The agent creates `retailstack_pos.db` with all captured transactions.

### Method 3: View logs
- Mac: `logs/retailstack.log`
- Windows: Same folder as the .exe

---

## Troubleshooting

**"Module not found" error:**
```bash
pip install pyserial requests python-dateutil
```

**"Port already in use":**
Another app is using port 9100. Close it or change port in config.json.

**No data captured:**
- Check firewall isn't blocking port 9100
- Verify printer is configured to print to this PC
- For testing, use the `nc` command above

---

## What to Test

1. ✅ Agent starts without errors
2. ✅ Shows "Listening on port 9100"
3. ✅ When test data sent, it creates transaction in DB
4. ✅ Multiple transactions work
5. ✅ Check database has correct data (receipt ID, items, total)
6. ✅ Agent survives closing and reopening

---

## Need Help?

Contact: Joel Ugwumadu
