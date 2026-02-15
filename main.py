#!/usr/bin/env python3
"""
RetailStack POS Agent - Desktop App
Intercepts ESC/POS from thermal printers and syncs to Retail Stack
"""

import sys
import os
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.escpos_parser import ESCPOSParser
from src.transaction_buffer import TransactionBuffer
from src.gap_detector import GapDetector
from src.printer_interceptor import PrinterInterceptor
from src.sync_client import StubSyncClient
from src.recovery_manager import RecoveryManager


# Setup logging to file
LOG_DIR = Path(os.path.dirname(__file__)) / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'retailstack.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
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
        
        # Load config
        self.printer_id = 'store-1'
        self.interceptor_mode = 'network'
        self.interceptor_port = 9100
    
    def _on_gap_detected(self, gap_info):
        logger.warning(f"GAP DETECTED: {gap_info}")
    
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
        
        # Show popup notification (Windows)
        try:
            from win32api import shell
            shell.SHOTUNDOWNOTIFY(0, "RetailStack", f"Transaction: {transaction.receipt_id}")
        except:
            pass
    
    def start(self):
        logger.info("=" * 50)
        logger.info("RetailStack POS Agent Starting...")
        logger.info("=" * 50)
        
        # Run recovery
        self.recovery.on_startup()
        self.gap_detector.load_last_id(self.printer_id)
        
        # Start interceptor
        self.interceptor = PrinterInterceptor(self._on_printer_data)
        
        if self.interceptor_mode == 'network':
            self.interceptor.start_network('0.0.0.0', self.interceptor_port)
            logger.info(f"Listening on port {self.interceptor_port}")
        else:
            self.interceptor.start_serial('COM3')
        
        self.running = True
        logger.info("Agent running - Waiting for printer data...")
        
        # Keep running
        import time
        while self.running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
    
    def stop(self):
        self.running = False
        if self.interceptor:
            self.interceptor.stop()
        self.recovery.on_shutdown()
        logger.info("Agent stopped")


def main():
    try:
        agent = POSAgent()
        agent.start()
    except Exception as e:
        logger.error(f"Error: {e}")
        input("Press Enter to exit...")


if __name__ == '__main__':
    main()
