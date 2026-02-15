# Tests for ESC/POS Parser

import pytest
from src.escpos_parser import ESCPOSParser, Transaction, LineItem


class TestESCPOSParser:
    """Test ESC/POS parser"""
    
    def setup_method(self):
        self.parser = ESCPOSParser()
    
    def test_parse_simple_receipt(self):
        """Test parsing a simple receipt"""
        data = b"""
        Store Name
        123 Main St
        -------------------
        Item 1         2 x 500
        Item 2            1000
        -------------------
        TOTAL:           2000
        Receipt #1001
        """
        
        result = self.parser.parse(data)
        
        assert result.receipt_id == '1001'
        assert result.total == 2000.0
        assert len(result.items) >= 1
    
    def test_extract_quantity_price(self):
        """Test quantity x price extraction"""
        data = b"Product ABC    3 x 1500"
        
        result = self.parser.parse(data)
        
        assert any(item.quantity == 3 for item in result.items)
    
    def test_extract_total(self):
        """Test total extraction"""
        data = b"""
        Item 1              500
        TOTAL: 5000
        """
        
        result = self.parser.parse(data)
        
        assert result.total == 5000.0
    
    def test_detect_printer_epson(self):
        """Test printer detection - Epson"""
        data = b"ESC @ ESC ! test"
        
        printer = self.parser.detect_printer(data)
        
        assert printer == 'epson'
    
    def test_detect_printer_star(self):
        """Test printer detection - Star"""
        data = b"STAR TSP test"
        
        printer = self.parser.detect_printer(data)
        
        assert printer == 'star'
    
    def test_parse_nigerian_prices(self):
        """Test parsing Nigerian naira prices"""
        data = b"Item Name         1,500"
        
        result = self.parser.parse(data)
        
        # Should handle comma as thousand separator
        assert any(item.unit_price >= 1500 for item in result.items)


class TestTransactionBuffer:
    """Test transaction buffer"""
    
    def test_add_transaction(self):
        """Test adding transaction"""
        from src.transaction_buffer import TransactionBuffer
        import os
        
        # Use test db
        db_path = 'test_buffer.db'
        if os.path.exists(db_path):
            os.remove(db_path)
        
        buffer = TransactionBuffer(db_path)
        
        items = [
            {'name': 'Item 1', 'quantity': 2, 'unit_price': 500, 'total': 1000}
        ]
        
        tx_id = buffer.add_transaction('RCT001', items, 1000)
        
        assert tx_id > 0
        
        # Cleanup
        os.remove(db_path)
    
    def test_get_unsynced(self):
        """Test getting unsynced transactions"""
        from src.transaction_buffer import TransactionBuffer
        import os
        
        db_path = 'test_unsynced.db'
        if os.path.exists(db_path):
            os.remove(db_path)
        
        buffer = TransactionBuffer(db_path)
        
        # Add transactions
        items = [{'name': 'Test', 'quantity': 1, 'unit_price': 100, 'total': 100}]
        buffer.add_transaction('RCT001', items, 100)
        buffer.add_transaction('RCT002', items, 100)
        
        unsynced = buffer.get_unsynced()
        
        assert len(unsynced) == 2
        
        # Cleanup
        os.remove(db_path)


class TestGapDetector:
    """Test gap detection"""
    
    def test_sequential_no_gap(self):
        """Test sequential receipts - no gap"""
        from src.gap_detector import GapDetector
        
        class MockBuffer:
            def __init__(self):
                self.gaps = []
            
            def log_gap(self, p, e, m):
                self.gaps.append({'expected': e, 'missing': m})
        
        buffer = MockBuffer()
        detector = GapDetector(buffer)
        
        # No gap
        result = detector.check_sequence('RCT1001', 'p1')
        
        assert result is None
        assert len(buffer.gaps) == 0
    
    def test_detect_gap(self):
        """Test gap detection"""
        from src.gap_detector import GapDetector
        
        class MockBuffer:
            def __init__(self):
                self.gaps = []
            
            def log_gap(self, p, e, m):
                self.gaps.append({'expected': e, 'missing': m})
        
        buffer = MockBuffer()
        detector = GapDetector(buffer)
        
        # First receipt
        detector.check_sequence('RCT1001', 'p1')
        
        # Gap! Next receipt is 1004 so expected was 1002
        detector.last_receipt_id['p1'] = 'RCT1001'
        result = detector.check_sequence('RCT1004', 'p1')
        
        assert result is not None
        assert result['expected_receipt_id'] == '1002'
        assert result['new_receipt_id'] == 'RCT1004'
        assert result['gap_size'] == 2
        assert len(buffer.gaps) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
