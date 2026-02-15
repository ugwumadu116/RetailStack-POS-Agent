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
from src.sync_client import StubSyncClient
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


class POSAgent:
    def __init__(self):
        self.running = False
        self.buffer = TransactionBuffer('retailstack_pos.db')
        self.sync_client = StubSyncClient()
        self.parser = ESCPOSParser()
        self.gap_detector = GapDetector(self.buffer, self._on_gap_detected)
        self.recovery = RecoveryManager(self.buffer, self.sync_client)
        self.interceptor = None
        self.printer_id = 'store-1'
    
    def _on_gap_detected(self, gap_info):
        logger.warning(f"GAP: {gap_info}")
    
    def _on_printer_data(self, data: bytes):
        logger.info(f"Received {len(data)} bytes")
        transaction = self.parser.parse(data)
        self.gap_detector.check_sequence(transaction.receipt_id, self.printer_id)
        
        items = [{'name': i.name, 'quantity': i.quantity, 'unit_price': i.unit_price, 'total': i.total} 
                 for i in transaction.items]
        
        self.buffer.add_transaction(
            transaction.receipt_id, items, transaction.total, 
            transaction.subtotal, transaction.tax, self.printer_id
        )
        logger.info(f"Transaction saved: {transaction.receipt_id} - N{transaction.total:.2f}")
    
    def start(self):
        logger.info("RetailStack POS Agent Starting...")
        self.recovery.on_startup()
        self.gap_detector.load_last_id(self.printer_id)
        
        self.interceptor = PrinterInterceptor(self._on_printer_data)
        self.interceptor.start_network('0.0.0.0', 9100)
        logger.info("Listening on port 9100")
        
        self.running = True
    
    def get_status(self):
        stats = self.buffer.get_stats()
        unsynced = self.buffer.get_unsynced()
        return {'stats': stats, 'unsynced': unsynced[:10]}
    
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
        .status { display: flex; gap: 10px; flex-wrap: wrap; }
        .badge { padding: 8px 16px; border-radius: 20px; font-weight: bold; }
        .green { background: #d4edda; color: #155724; }
        .yellow { background: #fff3cd; color: #856404; }
        .red { background: #f8d7da; color: #721c24; }
        button { background: #007bff; color: white; border: none; padding: 12px 24px; 
                 border-radius: 5px; cursor: pointer; font-size: 16px; margin: 5px; }
        button:hover { background: #0056b3; }
        button.test { background: #28a745; }
        button.test:hover { background: #1e7e34; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
        .log { background: #1e1e1e; color: #00ff00; padding: 15px; border-radius: 5px; 
               font-family: monospace; height: 200px; overflow-y: auto; }
        .instructions { background: #e7f3ff; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; }
    </style>
</head>
<body>
    <h1>🧾 RetailStack POS Agent</h1>
    
    <div class="card">
        <h2>📊 Status</h2>
        <div class="status">
            <div class="badge green">● Running</div>
            <div class="badge">Port: 9100</div>
        </div>
    </div>
    
    <div class="card">
        <h2>🧪 Test</h2>
        <p>Click to simulate a test transaction:</p>
        <button class="test" onclick="runTest()">📤 Send Test Data</button>
        <p id="testResult"></p>
    </div>
    
    <div class="card">
        <h2>📈 Transactions</h2>
        <div id="transactions">Loading...</div>
    </div>
    
    <div class="card">
        <h2>📝 How It Works</h2>
        <div class="instructions">
            <p><strong>What this does:</strong> Listens for receipt printer data and saves transactions.</p>
            <p><strong>For QA Testing:</strong></p>
            <ol>
                <li>Click "Send Test Data" above</li>
                <li>Check if transaction appears in the table</li>
                <li>For real printer: Configure printer to send data to this PC's port 9100</li>
            </ol>
            <p><strong>Logs:</strong> Check logs/retailstack.log</p>
        </div>
    </div>
    
    <script>
        function runTest() {
            fetch('/test').then(r => r.text()).then(d => {
                document.getElementById('testResult').innerHTML = '<strong>✅ ' + d + '</strong>';
                loadTransactions();
            });
        }
        
        function loadTransactions() {
            fetch('/status').then(r => r.json()).then(d => {
                let html = '<table><tr><th>Receipt ID</th><th>Total</th><th>Time</th></tr>';
                d.unsynced.forEach(tx => {
                    html += '<tr><td>' + tx.receipt_id + '</td><td>N' + tx.total + '</td><td>' + tx.timestamp + '</td></tr>';
                });
                html += '</table>';
                if (d.unsynced.length === 0) html = '<p>No transactions yet. Click "Send Test Data"!</p>';
                document.getElementById('transactions').innerHTML = html;
            });
        }
        
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
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        pass  # Suppress logs


def main():
    # Start agent
    agent.start()
    
    # Start web UI
    PORT = 8080
    server = HTTPServer(('', PORT), Handler)
    
    print("=" * 50)
    print("  RetailStack POS Agent")
    print("=" * 50)
    print(f"✅ Agent running on port 9100")
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
