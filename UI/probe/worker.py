#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Connection Worker Thread
Background thread for establishing probe connections
"""

import logging
from PyQt6.QtCore import QThread, pyqtSignal

LOG = logging.getLogger(__name__)


class ConnectWorker(QThread):
    """Background connection worker thread
    
    Handles the potentially long-running connection process
    in a background thread to keep the UI responsive.
    """
    finished = pyqtSignal(bool, str)
    
    def __init__(self, wrapper, target, probe_id, frequency, connect_mode, pack_path):
        """Initialize worker
        
        Args:
            wrapper: PyOCDWrapper instance
            target: Target chip name
            probe_id: Probe unique ID (optional)
            frequency: SWD frequency in Hz
            connect_mode: ConnectMode enum value
            pack_path: Path to CMSIS-Pack file (optional)
        """
        super().__init__()
        self._wrapper = wrapper
        self._target = target
        self._probe_id = probe_id
        self._frequency = frequency
        self._connect_mode = connect_mode
        self._pack_path = pack_path
        self._cancelled = False
        
    def cancel(self):
        """Request cancellation of the connection attempt"""
        self._cancelled = True
        # Force disconnect to interrupt any blocking operation
        try:
            self._wrapper.disconnect(force=True)
        except Exception:
            pass
        
    def run(self):
        """Execute connection attempt"""
        try:
            if self._cancelled:
                self.finished.emit(False, "已取消")
                return
                
            success = self._wrapper.connect(
                self._target,
                probe_id=self._probe_id,
                frequency=self._frequency,
                connect_mode=self._connect_mode,
                pack_path=self._pack_path
            )
            
            if self._cancelled:
                self._wrapper.disconnect()
                self.finished.emit(False, "已取消")
                return
                
            if success:
                self.finished.emit(True, f"已连接到 {self._target}")
            else:
                self.finished.emit(False, "连接失败 - 请检查硬件连接")
        except Exception as e:
            LOG.exception("Connection error")
            self.finished.emit(False, f"连接错误: {str(e)}")
