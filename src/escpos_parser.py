# ESC/POS Parser for RetailStack POS Agent
# Parses receipt printer byte streams

import re
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LineItem:
    """Represents a single line item on a receipt"""
    name: str
    quantity: int
    unit_price: float
    total: float


@dataclass
class Transaction:
    """Represents a parsed transaction"""
    receipt_id: str
    items: List[LineItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: str = ""
    # Edge-case flags
    is_incomplete: bool = False  # True if session lacked total/receipt_id/items
    transaction_type: str = "sale"  # 'sale' | 'void' | 'refund'


class ESCPOSParser:
    """Parser for ESC/POS byte streams"""
    
    # ESC/POS command constants
    ESC = b'\x1b'
    GS = b'\x1d'
    LF = b'\x0a'
    CR = b'\x0d'
    DLE = b'\x10'
    FS = b'\x1c'
    
    # Common command patterns
    CMD_INITIALIZE = ESC + b'@'  # Initialize printer
    CMD_CUT = GS + b'V'  # Cut paper
    CMD_FEED = LF  # Line feed
    
    # Known manufacturers
    SUPPORTED_PRINTERS = ['epson', 'star', 'bixolon']
    
    # Known ESC/POS command prefixes (ESC/GS + next byte or more) - we don't log these as unknown
    KNOWN_ESC_SEQUENCES = {
        (0x1B, 0x40),   # ESC @ Initialize
        (0x1B, 0x21),   # ESC ! Print mode
        (0x1B, 0x2D),   # ESC - Underline
        (0x1B, 0x45),   # ESC E Bold
        (0x1B, 0x61),   # ESC a Alignment
        (0x1B, 0x64),   # ESC d Feed
        (0x1B, 0x69),   # ESC i Partial cut
        (0x1B, 0x4A),   # ESC J Feed
        (0x1B, 0x6D),   # ESC m
        (0x1D, 0x56),   # GS V Cut
        (0x1D, 0x21),   # GS ! Character size
        (0x1D, 0x48),   # GS H
        (0x1D, 0x77),   # GS w
        (0x1D, 0x6B),   # GS k Barcode
        (0x10, 0x04),   # DLE EOT
    }
    
    def __init__(self, log_unknown_commands: bool = True):
        self.manufacturer = 'epson'  # Default
        self.unknown_commands = []
        self.log_unknown_commands = log_unknown_commands
    
    def _collect_unknown_commands(self, raw_data: bytes) -> None:
        """Scan raw byte stream for ESC/GS/DLE commands; record unknown ones as hex."""
        i = 0
        data = bytearray(raw_data)
        while i < len(data):
            if data[i] == 0x1B or data[i] == 0x1D or data[i] == 0x10:
                lead = data[i]
                # Two-byte command
                if i + 1 < len(data):
                    key = (lead, data[i + 1])
                    if key not in self.KNOWN_ESC_SEQUENCES:
                        cmd_hex = ' '.join(f'{b:02X}' for b in data[i:i+2])
                        entry = f"raw[{i}]: {cmd_hex}"
                        if entry not in self.unknown_commands:
                            self.unknown_commands.append(entry)
                        if self.log_unknown_commands:
                            logger.debug("Unknown ESC/POS command: %s", cmd_hex)
                    i += 2
                    continue
                else:
                    self.unknown_commands.append(f"raw[{i}]: {lead:02X} (incomplete)")
                    if self.log_unknown_commands:
                        logger.debug("Incomplete command at end: %02X", lead)
            i += 1
    
    def parse(self, raw_data: bytes) -> Transaction:
        """Parse ESC/POS byte stream into Transaction"""
        self.unknown_commands = []
        self._collect_unknown_commands(raw_data)
        
        # Decode to string, handling common encodings
        try:
            text = raw_data.decode('cp1252')  # Windows default
        except Exception:
            try:
                text = raw_data.decode('latin-1')
            except Exception:
                text = raw_data.decode('utf-8', errors='ignore')
        
        receipt_id = self._extract_receipt_id(text)
        transaction = Transaction(receipt_id=receipt_id, raw_data=text[:200])
        
        # Extract line items
        transaction.items = self._extract_items(text)
        
        # Extract totals
        transaction.total = self._extract_total(text)
        transaction.subtotal = self._extract_subtotal(text)
        
        # Incomplete session: no total, or no items, or receipt_id was generated
        transaction.is_incomplete = (
            (transaction.total == 0.0 and len(transaction.items) == 0)
            or (transaction.receipt_id or "").startswith("RX-")
        )
        # Void/refund detection
        transaction.transaction_type = self._detect_transaction_type(text)
        
        if self.unknown_commands and self.log_unknown_commands:
            logger.info(
                "Parsed receipt with %d unknown command(s); raw bytes: %s",
                len(self.unknown_commands),
                "; ".join(self.unknown_commands[:5]),
            )
        return transaction
    
    def _extract_receipt_id(self, text: str) -> str:
        """Extract receipt/transaction ID"""
        patterns = [
            r'(?:receipt|receipt No|receipt#|RCT)[\s:]*(\w+)',
            r'(?:inv|invoice)[\s:#]*(\w+)',
            r'#(\d{4,})',  # 4+ digit number
            r'TRX[_\s]*(\w+)',
            r'(\d{10,})',  # Timestamp-like ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return f"RX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _extract_items(self, text: str) -> List[LineItem]:
        """Extract line items from receipt"""
        items = []
        lines = text.split('\n')
        
        # Patterns for quantity x price format
        item_patterns = [
            r'(\d+)\s*[xX×]\s*([\d,]+\.?\d*)',  # "2 x 500" or "2×500"
            r'(.+?)\s+([\d,]+\.?\d*)\s*$',  # Item name followed by price
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip header/footer lines
            skip_words = ['total', 'subtotal', 'tax', 'change', 'cash', 'card', 
                         'thank', 'welcome', 'please', 'receipt', 'invoice',
                         '========================', '------------------']
            if any(word in line.lower() for word in skip_words):
                continue
            
            # Try quantity x price pattern
            match = re.search(r'(\d+)\s*[xX×]\s*([\d,]+\.?\d*)', line)
            if match:
                qty = int(match.group(1))
                price = self._parse_price(match.group(2))
                # Try to get item name
                name_part = line[:match.start()].strip()
                if name_part:
                    items.append(LineItem(
                        name=name_part,
                        quantity=qty,
                        unit_price=price,
                        total=qty * price
                    ))
                continue
            
            # Try price at end pattern (with or without decimals, e.g. 1,500 or 1000.00)
            match = re.search(r'(.+?)\s+([\d,]+\.?\d*)\s*$', line)
            if match:
                name = match.group(1).strip()
                price = self._parse_price(match.group(2))
                if name and price > 0 and not any(c in name.lower() for c in ['total', 'tax', 'sub']):
                    items.append(LineItem(
                        name=name,
                        quantity=1,
                        unit_price=price,
                        total=price
                    ))
        
        return items
    
    def _extract_total(self, text: str) -> float:
        """Extract total amount"""
        patterns = [
            r'(?:grand\s*)?total[\s:]*([\d,]+\.?\d*)',
            r'amount[\s:]*([\d,]+\.?\d*)',
            r'due[\s:]*([\d,]+\.?\d*)',
            r'[\* ]+\s*([\d,]+\.?\d{2})',
        ]
        
        # Look for largest number near "total" or at end
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return self._parse_price(matches[-1])  # Last match usually total
        
        # Fallback: find largest currency-like number
        numbers = re.findall(r'[\d,]+\.?\d{2}', text)
        if numbers:
            return max(self._parse_price(n) for n in numbers)
        
        return 0.0
    
    def _extract_subtotal(self, text: str) -> float:
        """Extract subtotal"""
        patterns = [
            r'subtotal[\s:]*([\d,]+\.?\d*)',
            r'sub[\s-]*total[\s:]*([\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_price(match.group(1))
        
        return 0.0
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float"""
        # Remove commas and clean
        price_str = price_str.replace(',', '').strip()
        try:
            return float(price_str)
        except Exception:
            return 0.0
    
    def _detect_transaction_type(self, text: str) -> str:
        """Detect void/refund from receipt text."""
        lower = text.lower()
        if any(k in lower for k in ('void', 'voided', 'cancelled', 'cancel')):
            return 'void'
        if any(k in lower for k in ('refund', 'return', 'reversed')):
            return 'refund'
        return 'sale'
    
    def detect_printer(self, raw_data: bytes) -> str:
        """Detect printer manufacturer"""
        data_str = str(raw_data)
        
        if b'ST' in raw_data or 'STAR' in data_str:
            return 'star'
        elif b'BIX' in raw_data or 'BIXOLON' in data_str:
            return 'bixolon'
        elif b'ESC' in raw_data or 'EPSON' in data_str:
            return 'epson'
        
        return 'unknown'
    
    def get_unknown_commands(self) -> List[str]:
        """Return list of unknown commands encountered"""
        return self.unknown_commands


# Test function
if __name__ == '__main__':
    # Sample ESC/POS data (simplified)
    sample = b"""
    ESC @ ESC ! 00
    Store Name
    123 Main Street
    -------------------
    Item 1         2 x 500
    Item 2             1000
    Item 3    1 x 2500
    -------------------
    Subtotal:        4000
    Tax (5%):         200
    ===================
    TOTAL:           4200
    ===================
    Receipt #1047
    2026-02-15 10:30:00
    """
    
    parser = ESCPOSParser()
    result = parser.parse(sample)
    
    print(f"Receipt ID: {result.receipt_id}")
    print(f"Total: {result.total}")
    print(f"Items: {len(result.items)}")
    for item in result.items:
        print(f"  - {item.name}: {item.quantity} x {item.unit_price}")
