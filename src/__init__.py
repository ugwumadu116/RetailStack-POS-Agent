# RetailStack POS Agent
# ESC/POS Receipt Interception and Sync

__version__ = '0.1.0'

from .escpos_parser import ESCPOSParser, Transaction, LineItem
from .transaction_buffer import TransactionBuffer
from .gap_detector import GapDetector
from .printer_interceptor import PrinterInterceptor, VirtualPrinterSetup
from .sync_client import SyncClient, StubSyncClient
from .recovery_manager import RecoveryManager

__all__ = [
    'ESCPOSParser',
    'Transaction',
    'LineItem', 
    'TransactionBuffer',
    'GapDetector',
    'PrinterInterceptor',
    'VirtualPrinterSetup',
    'SyncClient',
    'StubSyncClient',
    'RecoveryManager',
]
