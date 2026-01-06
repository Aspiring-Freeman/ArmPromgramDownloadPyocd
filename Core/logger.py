#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logger utilities
"""

import logging
import sys
from typing import Optional, Callable, List
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class CommandLogger:
    """
    Logger that formats operations like command-line PyOCD output.
    Shows equivalent command and detailed results.
    
    Thread-safe singleton implementation.
    """
    
    _instance: Optional['CommandLogger'] = None
    _lock = None  # Will be set on first instantiation
    
    def __new__(cls):
        if cls._instance is None:
            import threading
            if cls._lock is None:
                cls._lock = threading.Lock()
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # Instance variables, not class variables
                    cls._instance._callbacks = []
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'CommandLogger':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def add_callback(self, callback: Callable[[str], None]):
        """Add callback to receive log messages"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str], None]):
        """Remove callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _emit(self, message: str):
        """Emit message to all callbacks"""
        for callback in self._callbacks:
            try:
                callback(message)
            except:
                pass
    
    def log(self, message: str):
        """Log general message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        print(full_msg, flush=True)  # Force flush
        sys.stdout.flush()
        self._emit(full_msg)
    
    def log_command(self, cmd: str, args: List[str]):
        """Log equivalent PyOCD command line"""
        full_cmd = f"pyocd {cmd} {' '.join(args)}"
        py_cmd = f"python -m pyocd {cmd} {' '.join(args)}"
        self.log("")
        self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        self.log("🔧 Equivalent Command:")
        self.log(f"   $ {full_cmd}")
        self.log(f"   or: PYTHONPATH=Driver/pyOCD {py_cmd}")
        self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    def log_probe_info(self, probe_id: str, description: str, vendor: str = '', product: str = ''):
        """Log probe detection info"""
        self.log(f"🔍 Detected probe:")
        self.log(f"   ID:          {probe_id}")
        self.log(f"   Description: {description}")
        if vendor:
            self.log(f"   Vendor:      {vendor}")
        if product:
            self.log(f"   Product:     {product}")
    
    def log_target_info(self, target: str, pack: Optional[str] = None):
        """Log target info"""
        self.log(f"🎯 Target: {target}")
        if pack:
            self.log(f"   Pack:   {pack}")
    
    def log_connection(self, mode: str, frequency: int):
        """Log connection parameters"""
        freq_mhz = frequency / 1_000_000
        freq_khz = frequency / 1_000
        self.log(f"⚙️  Connect mode: {mode}")
        if freq_mhz >= 1:
            self.log(f"   Frequency:    {freq_mhz:.1f} MHz ({frequency:,} Hz)")
        else:
            self.log(f"   Frequency:    {freq_khz:.0f} kHz ({frequency:,} Hz)")
    
    def log_result(self, success: bool, message: str, duration_ms: Optional[float] = None):
        """Log operation result"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.log(f"")
        self.log(f"{status}: {message}")
        if duration_ms is not None:
            if duration_ms < 1000:
                self.log(f"   Duration: {duration_ms:.0f} ms")
            else:
                self.log(f"   Duration: {duration_ms/1000:.2f} s")
    
    def log_flash_info(self, file_path: str, file_size: Optional[int] = None):
        """Log flash file info"""
        self.log(f"📁 File: {file_path}")
        if file_size is not None:
            if file_size < 1024:
                self.log(f"   Size: {file_size} bytes")
            elif file_size < 1024 * 1024:
                self.log(f"   Size: {file_size / 1024:.2f} KB")
            else:
                self.log(f"   Size: {file_size / (1024*1024):.2f} MB")
    
    def log_memory_regions(self, regions: List[dict]):
        """Log memory region info"""
        self.log(f"💾 Memory Regions:")
        for region in regions:
            start = region.get('start', 0)
            size = region.get('size', 0)
            name = region.get('name', 'Unknown')
            self.log(f"   {name}: 0x{start:08X} - 0x{start+size:08X} ({size // 1024} KB)")
    
    def log_error(self, error: str, details: Optional[str] = None):
        """Log error with details"""
        self.log(f"❌ Error: {error}")
        if details:
            for line in details.split('\n'):
                if line.strip():
                    self.log(f"   {line}")
    
    def log_separator(self, char: str = '─', length: int = 60):
        """Log separator line"""
        self.log(char * length)


# Global command logger instance
command_logger = CommandLogger.get_instance()


def setup_logger(name: str = "ArmFlashTool", level: int = logging.DEBUG) -> logging.Logger:
    """Setup logging for application"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    if sys.stdout.isatty():
        formatter = ColoredFormatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', '%H:%M:%S')
    else:
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', '%H:%M:%S')
        
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Also setup pyocd loggers to show detailed output
    for pyocd_logger_name in ['pyocd', 'pyocd.core', 'pyocd.probe', 'pyocd.coresight', 'pyocd.flash']:
        pyocd_log = logging.getLogger(pyocd_logger_name)
        pyocd_log.setLevel(level)
        pyocd_log.handlers.clear()
        pyocd_log.addHandler(handler)
    
    return logger
