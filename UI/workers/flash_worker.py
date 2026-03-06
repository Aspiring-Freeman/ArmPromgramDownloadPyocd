#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flash Worker - Background flash programming thread
"""

from __future__ import annotations

import os
import logging
import threading

from PyQt6.QtCore import pyqtSignal, QThread

from Core.pyocd_wrapper import ResetType

LOG = logging.getLogger(__name__)


class FlashWorker(QThread):
    """Background flash worker with cooperative cancellation
    
    Signals:
        progress: Emitted with progress value (0.0 to 1.0)
        status: Emitted with status message string
        finished: Emitted with (success: bool, message: str) when complete
    """
    progress = pyqtSignal(float)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, wrapper, file_path: str, address: int, verify: bool = True, reset_after: bool = False):
        """Initialize flash worker
        
        Args:
            wrapper: PyOCDWrapper instance
            file_path: Path to firmware file (.hex, .bin, .elf)
            address: Flash base address for binary files
            verify: Whether to verify after programming
            reset_after: Whether to reset target after programming
        """
        super().__init__()
        self._wrapper = wrapper
        self._file_path = file_path
        self._address = address
        self._verify = verify
        self._reset_after = reset_after
        self._cancel_event = threading.Event()
        
    def cancel(self):
        """Request cancellation - cooperative, not forced"""
        self._cancel_event.set()
        
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested"""
        return self._cancel_event.is_set()
        
    def run(self):
        """Execute flash programming in background thread"""
        try:
            if self.is_cancelled():
                self.finished.emit(False, "已取消")
                return
                
            self.status.emit(f"正在烧录: {os.path.basename(self._file_path)}")
            
            def on_progress(p):
                if self.is_cancelled():
                    return False  # Signal to stop
                self.progress.emit(p)
                return True
                
            success = self._wrapper.flash_file(
                self._file_path,
                self._address,
                verify=self._verify,
                progress_callback=on_progress
            )
            
            if self.is_cancelled():
                self.finished.emit(False, "已取消")
                return
            
            if success and self._reset_after:
                self.status.emit("烧录完成，正在复位...")
                self._wrapper.reset(ResetType.DEFAULT, halt=False)
                
            if success:
                self.finished.emit(True, "烧录成功")
            else:
                self.finished.emit(False, "烧录失败")
                
        except Exception as e:
            LOG.exception("Flash error")
            self.finished.emit(False, str(e))
