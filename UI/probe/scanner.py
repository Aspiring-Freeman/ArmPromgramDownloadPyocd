#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probe Scanner Thread
Background thread for continuous probe detection
"""

import time
from PyQt6.QtCore import QThread, pyqtSignal


class ProbeScanner(QThread):
    """Background probe scanner thread
    
    Continuously scans for connected debug probes and emits
    signals when the probe list changes.
    """
    probes_found = pyqtSignal(list)
    
    def __init__(self, wrapper, scan_interval=10):
        """Initialize scanner
        
        Args:
            wrapper: PyOCDWrapper instance
            scan_interval: 扫描间隔(秒), 默认10秒
        """
        super().__init__()
        self._wrapper = wrapper
        self._running = True
        self._scan_interval = scan_interval
        
    def run(self):
        """Main scanner loop"""
        while self._running:
            try:
                probes = self._wrapper.list_probes()
                self.probes_found.emit(probes)
            except Exception:
                # 忽略列举探针时的错误，继续扫描
                self.probes_found.emit([])
            # 使用配置的扫描间隔，支持早期退出
            sleep_iterations = int(self._scan_interval * 10)
            for _ in range(sleep_iterations):
                if not self._running:
                    break
                time.sleep(0.1)
                
    def stop(self):
        """Stop the scanner thread"""
        self._running = False
        self.wait()
