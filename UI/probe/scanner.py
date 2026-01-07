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
    
    def __init__(self, wrapper):
        """Initialize scanner
        
        Args:
            wrapper: PyOCDWrapper instance
        """
        super().__init__()
        self._wrapper = wrapper
        self._running = True
        
    def run(self):
        """Main scanner loop"""
        while self._running:
            probes = self._wrapper.list_probes()
            self.probes_found.emit(probes)
            # 2 second interval with early exit support
            for _ in range(20):
                if not self._running:
                    break
                time.sleep(0.1)
                
    def stop(self):
        """Stop the scanner thread"""
        self._running = False
        self.wait()
