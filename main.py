#!/usr/bin/env python3
"""
RetailStack POS Agent - Desktop App with Web UI
"""

import sys
import os
import logging
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.escpos_parser import ESCPOSParser
from src.transaction_buffer import TransactionBuffer
from src.gap_detector import GapDetector
from src.printer_interceptor import PrinterInterceptor
from src.sync_client import SyncClient, StubSyncClient
from src.recovery_manager import RecoveryManager


# Setup logging
LOG_DIR = Path(os.path.dirname(__file__)) / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'retailstack.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def _load_config():
    config_path = Path(__file__).parent / 'config.json'
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


class POSAgent:
    def __init__(self):
        self.running = False
        config = _load_config()
        self.buffer = TransactionBuffer(config.get('db_path', 'retailstack_pos.db'))
        # Backup API: still save locally, also POST to backend
        server_url = config.get('server_url') or config.get('backup_api_url')
        if server_url:
            self.sync_client = SyncClient(
                server_url,
                api_key=config.get('api_key'),
                transactions_path=config.get('backup_transactions_path', '/api/pos/transactions'),
            )
        else:
            self.sync_client = StubSyncClient()
        self.parser = ESCPOSParser()
        self.gap_detector = GapDetector(self.buffer, self._on_gap_detected)
        self.recovery = RecoveryManager(self.buffer, self.sync_client)
        self.interceptor = None
        self.printer_id = config.get('printer_id', 'store-1')
        self.port = config.get('interceptor_port', 9100)
    
    def _on_gap_detected(self, gap_info):
        logger.warning(f"GAP: {gap_info}")
    
    def _on_printer_data(self, data: bytes):
        logger.info(f"Received {len(data)} bytes")
        transaction = self.parser.parse(data)
        self.gap_detector.check_sequence(transaction.receipt_id, self.printer_id)
        
        items = [{'name': i.name, 'quantity': i.quantity, 'unit_price': i.unit_price, 'total': i.total}
                 for i in transaction.items]
        
        # Save to local DB first
        tx_id = self.buffer.add_transaction(
            transaction.receipt_id, items, transaction.total,
            transaction.subtotal, transaction.tax, self.printer_id
        )
        logger.info(f"Transaction saved locally: {transaction.receipt_id} - N{transaction.total:.2f}")
        
        # Backup: send to remote API. If this fails, nothing breaks; recovery will retry on restart.
        try:
            ts = transaction.timestamp
            timestamp_str = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
            payload = {
                'receipt_id': transaction.receipt_id,
                'printer_id': self.printer_id,
                'items': items,
                'subtotal': transaction.subtotal,
                'tax': transaction.tax,
                'total': transaction.total,
                'timestamp': timestamp_str,
                'replay': False,
            }
            result = self.sync_client.sync_transaction(payload)
            if result.get('success'):
                self.buffer.mark_synced(tx_id, result.get('status_code', 200))
            else:
                logger.warning(f"Backup API sync failed for {transaction.receipt_id}: {result.get('error', 'unknown')}")
        except Exception as e:
            logger.warning(f"Backup API call failed (transaction still saved locally): {e}")
    
    def start(self, port=None):
        if port:
            self.port = port
        logger.info(f"RetailStack POS Agent Starting on port {self.port}...")
        self.recovery.on_startup()
        self.gap_detector.load_last_id(self.printer_id)
        
        self.interceptor = PrinterInterceptor(self._on_printer_data)
        self.interceptor.start_network('0.0.0.0', self.port)
        logger.info(f"Listening on port {self.port}")
        
        self.running = True
    
    def restart(self, new_port):
        logger.info(f"Restarting on port {new_port}...")
        if self.interceptor:
            self.interceptor.stop()
        self.running = False
        self.port = new_port
        self.start()
    
    def get_status(self):
        stats = self.buffer.get_stats()
        unsynced = self.buffer.get_unsynced()
        return {
            'stats': stats, 
            'unsynced': unsynced[:10],
            'port': self.port,
            'running': self.running
        }
    
    def simulate_test_data(self):
        test_data = b"""
        STORE NAME
        123 Test Street
        -------------------
        Item 1         2 x 500
        Item 2            1000
        Item 3    1 x 2500
        -------------------
        TOTAL:           4500
        Receipt #TEST001
        """
        self._on_printer_data(test_data)
        return "Test data sent!"


# Global agent
agent = POSAgent()

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>RetailStack POS Agent</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .card { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .status { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        .badge { padding: 8px 16px; border-radius: 20px; font-weight: bold; }
        .green { background: #d4edda; color: #155724; }
        .yellow { background: #fff3cd; color: #856404; }
        .red { background: #f8d7da; color: #721c24; }
        button { background: #007bff; color: white; border: none; padding: 12px 24px; 
                 border-radius: 5px; cursor: pointer; font-size: 16px; margin: 5px; }
        button:hover { background: #0056b3; }
        button.test { background: #28a745; }
        button.test:hover { background: #1e7e34; }
        button.restart { background: #dc3545; }
        button.restart:hover { background: #c82333; }
        input { padding: 10px; font-size: 16px; border: 1px solid #ddd; border-radius: 5px; width: 100px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
        .instructions { background: #e7f3ff; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; }
        .form-group { display: flex; gap: 10px; align-items: center; margin: 10px 0; }
        .header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
        .header img { width: 48px; height: 48px; object-fit: contain; }
    </style>
</head>
<body>
    <div class="header">
        <img src="/assets/logo.png" alt="RetailStack">
        <h1>RetailStack POS Agent</h1>
    </div>
    
    <div class="card">
        <h2>Status</h2>
        <div class="status">
            <div class="badge green">Running</div>
            <div class="badge">Port: <span id="port">9100</span></div>
        </div>
    </div>
    
    <div class="card">
        <h2>Configuration</h2>
        <div class="form-group">
            <label>Listen Port:</label>
            <input type="number" id="portInput" value="9100" min="1000" max="65535">
            <button onclick="restartPort()">Restart</button>
        </div>
        <p><small>Default is 9100. Most thermal printers use port 9100.</small></p>
    </div>
    
    <div class="card">
        <h2>Test</h2>
        <p>Simulate a test transaction:</p>
        <button class="test" onclick="runTest()">Send Test Data</button>
        <p id="testResult"></p>
    </div>
    
    <div class="card">
        <h2>Transactions</h2>
        <div id="transactions">Loading...</div>
    </div>
    
    <div class="card">
        <h2>How It Works</h2>
        <div class="instructions">
            <p><strong>What this does:</strong> Listens for receipt printer data and saves transactions.</p>
            <p><strong>To test:</strong></p>
            <ol>
                <li>Click Send Test Data. The transaction should appear in the table below.</li>
                <li>For a real printer, send its data to this computer on the port above (default 9100).</li>
                <li>Most thermal printers (Epson, Star, Bixolon) use port 9100.</li>
            </ol>
            <p><strong>Logs:</strong> See logs/retailstack.log</p>
        </div>
    </div>
    
    <script>
        function runTest() {
            fetch('/test').then(r => r.text()).then(d => {
                document.getElementById('testResult').innerHTML = '<strong>' + d + '</strong>';
                loadTransactions();
            });
        }
        
        function restartPort() {
            const port = document.getElementById('portInput').value;
            fetch('/restart?port=' + port).then(r => r.text()).then(d => {
                alert(d);
                loadStatus();
            });
        }
        
        function loadStatus() {
            fetch('/status').then(r => r.json()).then(d => {
                document.getElementById('port').innerText = d.port;
                if (document.getElementById('portInput').value != d.port) {
                    document.getElementById('portInput').value = d.port;
                }
            });
        }
        
        function loadTransactions() {
            fetch('/status').then(r => r.json()).then(d => {
                let html = '<table><tr><th>Receipt ID</th><th>Total</th><th>Time</th></tr>';
                d.unsynced.forEach(tx => {
                    html += '<tr><td>' + tx.receipt_id + '</td><td>N' + tx.total + '</td><td>' + tx.timestamp + '</td></tr>';
                });
                html += '</table>';
                if (d.unsynced.length === 0) html = '<p>No transactions yet. Click Send Test Data above.</p>';
                document.getElementById('transactions').innerHTML = html;
            });
        }
        
        loadStatus();
        loadTransactions();
        setInterval(loadTransactions, 5000);
    </script>
</body>
</html>
"""

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == '/assets/logo.png':
            logo_path = Path(__file__).parent / 'assets' / 'logo.png'
            if logo_path.exists():
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                self.wfile.write(logo_path.read_bytes())
            else:
                self.send_error(404)
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(agent.get_status()).encode())
        elif self.path == '/test':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(agent.simulate_test_data().encode())
        elif self.path.startswith('/restart?port='):
            try:
                port = int(self.path.split('=')[1])
                agent.restart(port)
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Restarted on port {port}".encode())
            except:
                self.send_response(400)
                self.end_headers()
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        pass


def main():
    agent.start()
    
    PORT = 8080
    server = HTTPServer(('', PORT), Handler)
    
    print("=" * 50)
    print("  RetailStack POS Agent")
    print("=" * 50)
    print(f"✅ Agent running on port {agent.port}")
    print(f"🌐 Web UI: http://localhost:{PORT}")
    print(f"📝 Logs: logs/retailstack.log")
    print("=" * 50)
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
        server.shutdown()


if __name__ == '__main__':
    main()
