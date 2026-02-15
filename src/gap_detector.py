# Gap Detector - Sequence gap detection for RetailStack POS Agent
# Detects missing receipt IDs and alerts

import re
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta


class GapDetector:
    """Detects sequence gaps in receipt IDs"""
    
    def __init__(self, buffer, alert_callback: Optional[Callable] = None):
        self.buffer = buffer
        self.alert_callback = alert_callback
        self.last_receipt_id = {}
    
    def check_sequence(self, new_receipt_id: str, printer_id: str = None) -> Optional[Dict]:
        """Check if new receipt ID creates a gap"""
        printer_id = printer_id or 'default'
        
        # Try to extract numeric ID
        numeric_id = self._extract_numeric(new_receipt_id)
        
        if numeric_id is None:
            # Can't do numeric gap detection on non-numeric IDs
            self.last_receipt_id[printer_id] = new_receipt_id
            return None
        
        last_id = self.last_receipt_id.get(printer_id)
        
        if last_id is None:
            # First receipt, no gap to check
            self.last_receipt_id[printer_id] = new_receipt_id
            return None
        
        last_numeric = self._extract_numeric(last_id)
        if last_numeric is None:
            # Last wasn't numeric, can't detect gap
            self.last_receipt_id[printer_id] = new_receipt_id
            return None
        
        # Check for gap
        expected = last_numeric + 1
        
        if numeric_id > expected:
            # Gap detected!
            gap_info = {
                'printer_id': printer_id,
                'expected_receipt_id': str(expected),
                'missing_receipt_id': str(numeric_id),
                'last_receipt_id': last_id,
                'new_receipt_id': new_receipt_id,
                'gap_size': numeric_id - expected,
                'detected_at': datetime.now().isoformat()
            }
            
            # Log to database
            self.buffer.log_gap(
                printer_id, 
                str(expected), 
                str(numeric_id)
            )
            
            # Alert if callback
            if self.alert_callback:
                self.alert_callback(gap_info)
            
            self.last_receipt_id[printer_id] = new_receipt_id
            return gap_info
        
        elif numeric_id < expected:
            # Sequence reset (new day?) - just update
            pass
        
        self.last_receipt_id[printer_id] = new_receipt_id
        return None
    
    def _extract_numeric(self, receipt_id: str) -> Optional[int]:
        """Extract numeric portion from receipt ID"""
        if not receipt_id:
            return None
        
        # Try to find trailing numbers
        match = re.search(r'(\d+)$', str(receipt_id))
        if match:
            return int(match.group(1))
        
        # Try to find any numbers
        match = re.search(r'(\d+)', str(receipt_id))
        if match:
            return int(match.group(1))
        
        return None
    
    def check_from_db(self, printer_id: str = None) -> List[Dict]:
        """Check for gaps in existing database"""
        gaps = []
        receipt_ids = self.buffer.get_receipt_ids(printer_id)
        
        for i in range(1, len(receipt_ids)):
            prev_numeric = self._extract_numeric(receipt_ids[i-1])
            curr_numeric = self._extract_numeric(receipt_ids[i])
            
            if prev_numeric and curr_numeric and curr_numeric > prev_numeric + 1:
                gap_info = {
                    'expected': str(prev_numeric + 1),
                    'found': receipt_ids[i],
                    'gap_size': curr_numeric - prev_numeric - 1
                }
                gaps.append(gap_info)
        
        return gaps
    
    def load_last_id(self, printer_id: str = None):
        """Load last known receipt ID from database"""
        printer_id = printer_id or 'default'
        
        # Get most recent receipt
        receipt_ids = self.buffer.get_receipt_ids(printer_id)
        if receipt_ids:
            self.last_receipt_id[printer_id] = receipt_ids[-1]
    
    def reset(self, printer_id: str = None):
        """Reset detection state"""
        printer_id = printer_id or 'default'
        if printer_id in self.last_receipt_id:
            del self.last_receipt_id[printer_id]
    
    def get_status(self) -> Dict:
        """Get detector status"""
        return {
            'last_receipt_ids': self.last_receipt_id,
            'pending_gaps': len(self.buffer.get_pending_gaps())
        }


if __name__ == '__main__':
    # Test with mock buffer
    class MockBuffer:
        def __init__(self):
            self.gaps = []
        
        def log_gap(self, printer_id, expected, missing):
            self.gaps.append({'printer_id': printer_id, 'expected': expected, 'missing': missing})
            print(f"LOG GAP: Expected {expected}, found {missing}")
        
        def get_receipt_ids(self, printer_id=None):
            return ['RCT1045', 'RCT1046', 'RCT1049']  # Missing 1047-1048
        
        def get_pending_gaps(self):
            return self.gaps
    
    buffer = MockBuffer()
    detector = GapDetector(buffer)
    
    # Test sequential
    print("Testing sequential...")
    detector.check_sequence('RCT1050', 'printer1')
    
    # Test gap
    print("\nTesting gap detection...")
    detector.last_receipt_id['printer1'] = 'RCT1046'
    gap = detector.check_sequence('RCT1049', 'printer1')
    print(f"Gap detected: {gap}")
    
    # Test from DB
    print("\nChecking DB for gaps...")
    gaps = detector.check_from_db('printer1')
    print(f"Gaps in DB: {gaps}")
