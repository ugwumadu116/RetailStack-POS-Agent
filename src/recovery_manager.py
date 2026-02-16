# Recovery Manager - Crash recovery for RetailStack POS Agent
# Handles restart recovery and replay of unconfirmed transactions

import logging
from datetime import datetime
from typing import Dict, List, Any
from .transaction_buffer import TransactionBuffer


logger = logging.getLogger(__name__)


class RecoveryManager:
    """Manages crash recovery and transaction replay"""
    
    def __init__(self, buffer: TransactionBuffer, sync_client):
        self.buffer = buffer
        self.sync_client = sync_client
        self.last_sync_time = None
        self.downtime_logged = False
    
    def on_startup(self) -> Dict[str, Any]:
        """Run recovery process on startup"""
        recovery_report = {
            'started_at': datetime.now().isoformat(),
            'transactions_replayed': 0,
            'gaps_found': [],
            'downtime_logged': False
        }
        
        # Load last sync time
        self.last_sync_time = self.buffer.load_state(
            'last_sync_time',
            None
        )
        
        if self.last_sync_time:
            logger.info(f"Last sync was at {self.last_sync_time}")
            self._log_downtime()
            recovery_report['downtime_logged'] = True
        
        # Replay unsynced transactions
        unsynced = self.buffer.get_unsynced()
        
        if unsynced:
            logger.info(f"Found {len(unsynced)} unsynced transactions to replay")
            recovery_report['transactions_replayed'] = len(unsynced)
            
            for tx in unsynced:
                self._replay_transaction(tx)
        
        # Check for gaps
        gaps = self.buffer.get_pending_gaps()
        if gaps:
            recovery_report['gaps_found'] = gaps
            logger.warning(f"Found {len(gaps)} unresolved gaps")
        
        recovery_report['completed_at'] = datetime.now().isoformat()
        
        # Save recovery completion
        self.buffer.save_state('last_recovery', recovery_report)
        
        return recovery_report
    
    def _log_downtime(self):
        """Log downtime window"""
        if self.last_sync_time:
            downtime_info = {
                'last_known_sync': self.last_sync_time,
                'restart_at': datetime.now().isoformat(),
                'message': 'Agent was offline - check for missed transactions'
            }
            
            self.buffer.save_state('downtime_log', downtime_info)
            self.downtime_logged = True
            
            logger.warning(
                f"DOWNTIME: Agent offline since {self.last_sync_time}. "
                "Review transactions during this period."
            )
    
    def _replay_transaction(self, tx: Dict):
        """Replay a single transaction to backup API. Never raises; API failure is logged only."""
        receipt_id = tx.get('receipt_id')
        try:
            import json
            payload = {
                'receipt_id': receipt_id,
                'printer_id': tx.get('printer_id'),
                'items': json.loads(tx.get('items_json', '[]')),
                'subtotal': tx.get('subtotal', 0),
                'tax': tx.get('tax', 0),
                'total': tx.get('total', 0),
                'timestamp': tx.get('timestamp'),
                'replay': True,
            }
            result = self.sync_client.sync_transaction(payload)
            if result.get('success'):
                self.buffer.mark_synced(tx['id'], result.get('status_code', 200))
                logger.info(f"Replayed transaction {receipt_id}")
            else:
                self.buffer.mark_failed(tx['id'], result.get('error', 'Unknown error'))
                logger.warning(f"Failed to replay {receipt_id}: {result.get('error')}")
        except Exception as e:
            logger.warning(f"Backup API replay failed for {receipt_id} (will retry later): {e}")
            self.buffer.mark_failed(tx['id'], str(e))
    
    def on_shutdown(self):
        """Save state before shutdown"""
        # Save current timestamp as last sync time
        self.buffer.save_state('last_sync_time', datetime.now().isoformat())
        
        # Save pending count
        unsynced = self.buffer.get_unsynced()
        self.buffer.save_state('pending_on_shutdown', len(unsynced))
        
        logger.info(f"Shutdown: {len(unsynced)} transactions pending sync")
    
    def force_replay_all(self) -> int:
        """Force replay of all unsynced transactions"""
        unsynced = self.buffer.get_unsynced()
        replayed = 0
        
        for tx in unsynced:
            # Reset retry count
            # (Would need to add this method to buffer)
            self._replay_transaction(tx)
            replayed += 1
        
        return replayed
    
    def get_recovery_status(self) -> Dict:
        """Get current recovery status"""
        return {
            'last_sync_time': self.last_sync_time,
            'downtime_logged': self.downtime_logged,
            'pending_transactions': len(self.buffer.get_unsynced()),
            'pending_gaps': len(self.buffer.get_pending_gaps()),
            'buffer_stats': self.buffer.get_stats()
        }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Test
    buffer = TransactionBuffer('test.db')
    
    class StubClient:
        def sync_transaction(self, tx):
            return {'success': True, 'status_code': 200}
    
    client = StubClient()
    recovery = RecoveryManager(buffer, client)
    
    print("Running startup recovery...")
    report = recovery.on_startup()
    print(f"Recovery report: {report}")
    
    print("\nRecovery status:")
    print(recovery.get_recovery_status())
