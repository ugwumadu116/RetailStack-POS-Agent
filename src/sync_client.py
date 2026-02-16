# Sync Client - REST API client for RetailStack POS Agent
# Handles syncing transactions to server

import requests
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class SyncClient:
    """REST API client for syncing transactions to Retail Stack"""
    
    def __init__(self, base_url: str, api_key: str = None, timeout: int = 30,
                 transactions_path: str = '/api/transactions'):
        self.base_url = base_url.rstrip('/')
        self.transactions_path = transactions_path if transactions_path.startswith('/') else '/' + transactions_path
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'RetailStack-POS-Agent/1.0'
        })
        
        # Retry settings
        self.max_retries = 5
        self.retry_delay = 5  # seconds
    
    def sync_transaction(self, transaction: Dict) -> Dict[str, Any]:
        """Sync a single transaction to backup API"""
        endpoint = f"{self.base_url}{self.transactions_path}"
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    endpoint,
                    json=transaction,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    logger.info(f"Transaction {transaction.get('receipt_id')} synced successfully")
                    return {
                        'success': True,
                        'response': response.json(),
                        'status_code': response.status_code
                    }
                
                elif response.status_code == 400:
                    # Bad request - don't retry
                    logger.error(f"Bad request for {transaction.get('receipt_id')}: {response.text}")
                    return {
                        'success': False,
                        'error': response.text,
                        'status_code': response.status_code,
                        'retry': False
                    }
                
                elif response.status_code == 401:
                    logger.error("Authentication failed - check API key")
                    return {
                        'success': False,
                        'error': 'Authentication failed',
                        'status_code': response.status_code,
                        'retry': False
                    }
                
                else:
                    logger.warning(f"Server error {response.status_code}, retry {attempt + 1}/{self.max_retries}")
                    time.sleep(self.retry_delay * (attempt + 1))
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout, retry {attempt + 1}/{self.max_retries}")
                time.sleep(self.retry_delay * (attempt + 1))
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error, retry {attempt + 1}/{self.max_retries}")
                time.sleep(self.retry_delay * (attempt + 1))
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'retry': False
                }
        
        return {
            'success': False,
            'error': 'Max retries exceeded',
            'status_code': 0,
            'retry': True
        }
    
    def sync_batch(self, transactions: list) -> Dict[str, Any]:
        """Sync multiple transactions"""
        endpoint = f"{self.base_url}/api/transactions/batch"
        
        try:
            response = self.session.post(
                endpoint,
                json={'transactions': transactions},
                timeout=self.timeout * 2
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Batch sync: {result.get('synced', 0)}/{len(transactions)} succeeded")
                return {
                    'success': True,
                    'synced': result.get('synced', 0),
                    'failed': result.get('failed', 0),
                    'details': result
                }
            else:
                return {
                    'success': False,
                    'error': response.text,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Batch sync error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_health(self) -> bool:
        """Check if server is reachable"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_status(self) -> Dict:
        """Get client status"""
        return {
            'base_url': self.base_url,
            'connected': self.check_health(),
            'max_retries': self.max_retries
        }


# Stub implementation for testing
class StubSyncClient:
    """Stub client for testing without server"""
    
    def __init__(self, *args, **kwargs):
        self.sync_count = 0
    
    def sync_transaction(self, transaction: Dict) -> Dict:
        self.sync_count += 1
        logger.info(f"[STUB] Synced transaction {transaction.get('receipt_id')}")
        return {
            'success': True,
            'status_code': 200,
            'response': {'id': self.sync_count}
        }
    
    def sync_batch(self, transactions: list) -> Dict:
        self.sync_count += len(transactions)
        return {
            'success': True,
            'synced': len(transactions),
            'failed': 0
        }
    
    def check_health(self) -> bool:
        return True


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Test with stub
    client = StubSyncClient()
    
    tx = {
        'receipt_id': 'RCT001',
        'total': 5000,
        'items': [{'name': 'Test', 'quantity': 1, 'total': 5000}]
    }
    
    result = client.sync_transaction(tx)
    print(f"Result: {result}")
