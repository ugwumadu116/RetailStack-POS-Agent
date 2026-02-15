# Printer Interceptor - Windows printer port monitoring for RetailStack POS Agent
# Intercepts ESC/POS data from thermal printers

import socket
import threading
import time
import logging
import sys
from typing import Optional, Callable
from queue import Queue
import serial

# USB support - optional
try:
    import usb.core
    import usb.util
    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False

# Windows port monitoring - optional (pywin32)
WIN32_AVAILABLE = False
if sys.platform == 'win32':
    try:
        import win32print
        import win32file
        WIN32_AVAILABLE = True
    except ImportError:
        pass

logger = logging.getLogger(__name__)


class PrinterInterceptor:
    """Intercepts ESC/POS data from thermal printers"""
    
    def __init__(self, on_data_callback: Callable[[bytes], None],
                 on_disconnect: Optional[Callable[[str], None]] = None,
                 on_reconnect: Optional[Callable[[str], None]] = None):
        self.on_data_callback = on_data_callback
        self.on_disconnect = on_disconnect
        self.on_reconnect = on_reconnect
        self.running = False
        self.thread = None
        self.mode = None  # 'usb', 'serial', 'network', 'virtual'
        self._reconnect_delay = 5
        self._reconnect_max_delay = 60
        
        # Configuration
        self.printer_config = {
            'vendor_id': None,  # USB vendor ID
            'product_id': None,  # USB product ID  
            'port': 'USB001',  # Windows printer port
            'serial_port': 'COM3',  # Serial port
            'network_host': None,  # Printer IP
            'network_port': 9100,  # Standard printer port
        }
    
    def start_usb(self, vendor_id: int = None, product_id: int = None):
        """Start USB interception"""
        self.mode = 'usb'
        self.printer_config['vendor_id'] = vendor_id
        self.printer_config['product_id'] = product_id
        
        self.running = True
        self.thread = threading.Thread(target=self._usb_listener, daemon=True)
        self.thread.start()
        logger.info("USB interception started")
    
    def start_serial(self, port: str = 'COM3', baudrate: int = 9600):
        """Start serial port interception"""
        self.mode = 'serial'
        self.printer_config['serial_port'] = port
        
        self.running = True
        self.thread = threading.Thread(
            target=self._serial_listener, 
            args=(port, baudrate),
            daemon=True
        )
        self.thread.start()
        logger.info(f"Serial interception started on {port}")
    
    def start_network(self, host: str, port: int = 9100):
        """Start network (TCP/IP) interception"""
        self.mode = 'network'
        self.printer_config['network_host'] = host
        self.printer_config['network_port'] = port
        
        self.running = True
        self.thread = threading.Thread(
            target=self._network_listener,
            args=(host, port),
            daemon=True
        )
        self.thread.start()
        logger.info(f"Network interception started on {host}:{port}")
    
    def start_windows_port(self, port: str = 'USB001'):
        """Start Windows printer port monitoring (pywin32) or fallback to stdin"""
        self.mode = 'windows_port'
        self.printer_config['port'] = port
        
        if WIN32_AVAILABLE:
            self.running = True
            self.thread = threading.Thread(
                target=self._windows_port_listener,
                args=(port,),
                daemon=True
            )
            self.thread.start()
            logger.info("Windows port monitoring started (pywin32) for %s", port)
        else:
            logger.warning("pywin32 not installed. Using stdin fallback.")
            self.running = True
            self.thread = threading.Thread(target=self._stdin_listener, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop interception"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Interception stopped")
    
    def _usb_listener(self):
        """USB listener - simplified version"""
        # Full USB implementation requires pywin32 or libusb
        logger.info("USB listener started (stub - requires configuration)")
        
        # In production, use:
        # dev = usb.core.find(idVendor=self.printer_config['vendor_id'], ...)
        # while self.running:
        #     data = dev.read(EP_IN, 1024)
        #     if data:
        #         self.on_data_callback(bytes(data))
        
        while self.running:
            time.sleep(1)
    
    def _serial_listener(self, port: str, baudrate: int):
        """Serial port listener with disconnect/reconnect"""
        delay = self._reconnect_delay
        while self.running:
            try:
                ser = serial.Serial(port, baudrate, timeout=1)
                delay = self._reconnect_delay
                if self.on_reconnect:
                    self.on_reconnect(f"serial:{port}")
                logger.info("Serial port %s opened", port)
                
                buffer = b''
                
                while self.running:
                    try:
                        if ser.in_waiting:
                            data = ser.read(ser.in_waiting)
                            buffer += data
                            if b'\x0a' in buffer or b'\x1d\x56' in buffer:
                                self.on_data_callback(buffer)
                                buffer = b''
                        else:
                            time.sleep(0.1)
                    except serial.SerialException as e:
                        logger.warning("Serial connection lost: %s", e)
                        if self.on_disconnect:
                            self.on_disconnect(f"serial:{port}")
                        break
                
                ser.close()
            except serial.SerialException as e:
                logger.error("Serial error: %s", e)
                if self.on_disconnect:
                    self.on_disconnect(f"serial:{port}")
            except Exception as e:
                logger.error("Error in serial listener: %s", e)
            
            if self.running:
                logger.info("Reconnecting to serial %s in %s seconds...", port, delay)
                time.sleep(delay)
                delay = min(delay * 2, self._reconnect_max_delay)
    
    def _network_listener(self, host: str, port: int):
        """Network TCP listener; handles client disconnect and accepts new connections"""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
            server.listen(1)
            logger.info("Network server listening on %s:%s", host, port)
            
            while self.running:
                try:
                    server.settimeout(1)
                    conn, addr = server.accept()
                    if self.on_reconnect:
                        self.on_reconnect(f"network:{host}:{port}")
                    logger.info("Connection from %s", addr)
                    
                    buffer = b''
                    while self.running:
                        try:
                            data = conn.recv(4096)
                            if not data:
                                logger.debug("Client disconnected")
                                if self.on_disconnect:
                                    self.on_disconnect(f"network:{addr[0]}:{addr[1]}")
                                break
                            buffer += data
                            if b'\x0a' in buffer or b'\x1d\x56' in buffer:
                                self.on_data_callback(buffer)
                                buffer = b''
                        except (ConnectionResetError, BrokenPipeError, OSError) as e:
                            logger.warning("Connection lost: %s", e)
                            if self.on_disconnect:
                                self.on_disconnect(f"network:{addr[0]}:{addr[1]}")
                            break
                    
                    conn.close()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error("Connection error: %s", e)
            
            server.close()
            
        except Exception as e:
            logger.error("Network server error: %s", e)
    
    def _windows_port_listener(self, port: str):
        """Windows port listener using pywin32 (COM-style ports only)"""
        if not WIN32_AVAILABLE:
            logger.warning("pywin32 not available; falling back to stdin")
            self._stdin_listener()
            return
        # Support COM port names: COM3 -> \\.\COM3
        if port.upper().startswith('COM'):
            port_path = '\\\\.\\' + port
        else:
            # USB001 etc. - Windows does not expose these for raw read; use network redirect
            logger.warning(
                "Port %s is not a COM port. On Windows, use network mode (printer to 127.0.0.1:9100) or a COM port.",
                port,
            )
            self._stdin_listener()
            return
        delay = self._reconnect_delay
        while self.running:
            try:
                handle = win32file.CreateFile(
                    port_path,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None,
                )
                delay = self._reconnect_delay
                if self.on_reconnect:
                    self.on_reconnect(f"windows:{port}")
                logger.info("Windows port %s opened", port)
                buffer = b''
                while self.running:
                    try:
                        err, data = win32file.ReadFile(handle, 4096)
                        if data:
                            buffer += data
                            if b'\x0a' in buffer or b'\x1d\x56' in buffer:
                                self.on_data_callback(buffer)
                                buffer = b''
                    except Exception as e:
                        logger.warning("Windows port read error: %s", e)
                        if self.on_disconnect:
                            self.on_disconnect(f"windows:{port}")
                        break
                try:
                    handle.Close()
                except Exception:
                    pass
            except Exception as e:
                logger.error("Windows port open error: %s", e)
                if self.on_disconnect:
                    self.on_disconnect(f"windows:{port}")
            if self.running:
                logger.info("Reconnecting to %s in %s seconds...", port, delay)
                time.sleep(delay)
                delay = min(delay * 2, self._reconnect_max_delay)

    def _stdin_listener(self):
        """Fallback: Read from stdin (for pipe-based setup)"""
        logger.info("Stdin listener started")
        
        import sys
        buffer = b''
        
        while self.running:
            try:
                data = sys.stdin.buffer.read(1024)
                if data:
                    buffer += data
                    if b'\x0a' in buffer:
                        self.on_data_callback(buffer)
                        buffer = b''
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Stdin error: {e}")
                break
    
    def get_status(self) -> dict:
        """Get interceptor status"""
        return {
            'running': self.running,
            'mode': self.mode,
            'config': self.printer_config
        }


class VirtualPrinterSetup:
    """Helper to set up Windows virtual printer"""
    
    @staticmethod
    def create_port_monitor_script():
        """Generate a PowerShell script to set up port monitor"""
        # This would need admin rights to run
        script = '''
# Run as Administrator
# Creates a local port for interception

$PortName = "RETAILSTACK_INTERCEPT"

# Add TCP/IP port
Add-PrinterPort -Name $PortName -PrinterHostAddress "127.0.0.1" -PortNumber 9100

Write-Host "Port $PortName created"
Write-Host "Now install a printer using this port"
'''
        return script


# Test
if __name__ == '__main__':
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    def on_data(data):
        print(f"Received {len(data)} bytes")
        print(f"First 100 bytes: {data[:100]}")
    
    interceptor = PrinterInterceptor(on_data)
    
    # For testing, start network listener on localhost
    print("Starting test network listener on port 9100...")
    interceptor.start_network('127.0.0.1', 9100)
    
    print("Interceptor running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        interceptor.stop()
