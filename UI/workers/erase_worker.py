#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Erase Worker - Background erase operation thread
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from PyQt6.QtCore import pyqtSignal, QThread

from Core.pyocd_wrapper import ResetType

LOG = logging.getLogger(__name__)


class EraseWorker(QThread):
    """Background erase worker with cooperative cancellation
    
    Supports three erase modes:
    - chip: Full chip/mass erase
    - sector: Single sector erase
    - range: Address range erase
    
    Signals:
        progress: Emitted with progress value (0.0 to 1.0)
        status: Emitted with status message string
        finished: Emitted with (success: bool, message: str) when complete
    """
    progress = pyqtSignal(float)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(
        self,
        wrapper,
        mode: str,
        start_addr: Optional[int] = None,
        end_addr: Optional[int] = None,
        sector: Optional[int] = None,
        reset_after: bool = False
    ):
        """Initialize erase worker
        
        Args:
            wrapper: PyOCDWrapper instance
            mode: Erase mode - "chip", "sector", or "range"
            start_addr: Start address for range erase
            end_addr: End address for range erase
            sector: Sector number for sector erase
            reset_after: Whether to reset target after erase
        """
        super().__init__()
        self._wrapper = wrapper
        self._mode = mode
        self._start_addr = start_addr
        self._end_addr = end_addr
        self._sector = sector
        self._reset_after = reset_after
        self._cancel_event = threading.Event()
        
    def cancel(self):
        """Request cancellation - cooperative, not forced"""
        self._cancel_event.set()
        
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested"""
        return self._cancel_event.is_set()
        
    def run(self):
        """Execute erase operation in background thread"""
        try:
            if self.is_cancelled():
                self.finished.emit(False, "已取消")
                return
                
            def on_progress(p):
                if self.is_cancelled():
                    return False  # Signal to stop
                self.progress.emit(p)
                return True
                
            if self._mode == "chip":
                self.status.emit("正在全片擦除...")
                success = self._wrapper.mass_erase(progress_callback=on_progress)
            elif self._mode == "sector" and self._sector is not None:
                self.status.emit(f"正在擦除扇区 {self._sector}...")
                success = self._wrapper.erase_sector(self._sector, progress_callback=on_progress)
            elif self._mode == "range" and self._start_addr is not None:
                self.status.emit(f"正在擦除地址范围 0x{self._start_addr:08X}...")
                success = self._wrapper.erase_range(self._start_addr, self._end_addr, progress_callback=on_progress)
            else:
                self.finished.emit(False, "无效的擦除参数")
                return
            
            if self.is_cancelled():
                self.finished.emit(False, "已取消")
                return
                
            if success and self._reset_after:
                self.status.emit("擦除完成，正在复位...")
                self._wrapper.reset(ResetType.DEFAULT, halt=False)
                
            if success:
                self.finished.emit(True, "擦除成功")
            else:
                self.finished.emit(False, "擦除失败")
                
        except Exception as e:
            LOG.exception("Erase error")
            self.finished.emit(False, str(e))
