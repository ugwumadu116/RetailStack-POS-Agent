# RetailStack POS Agent

Desktop app that receives receipt printer data, parses sales (items, quantities, prices, totals, receipt IDs), stores them in SQLite, and can sync to Retail Stack. It also detects missing receipt numbers and replays unsynced data after a restart.

## Install

**Download ZIP:** Get the project from GitHub, extract it, open a terminal in the folder, then run `bash install.sh`.

**Or clone:**
```bash
git clone https://github.com/ugwumadu116/RetailStack-POS-Agent.git
cd RetailStack-POS-Agent
bash install.sh
```

## Run

```bash
python main.py
```

Then open the Web UI at http://localhost:8080 and use **Send Test Data** to create a test transaction.

## Test with real data

Send test receipt data to the agent:
```bash
echo "Item 1  2 x 500" | nc localhost 9100
```

## Logs

Logs are in `logs/retailstack.log`.

## Support

Contact: Joel Ugwumadu
