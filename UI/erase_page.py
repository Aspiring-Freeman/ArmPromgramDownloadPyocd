#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Erase page"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton,
    LineEdit, ComboBox, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, StrongBodyLabel, RadioButton, ProgressBar,
    InfoBar, InfoBarPosition, SpinBox
)

from Core.pyocd_wrapper import ResetType

LOG = logging.getLogger(__name__)


class EraseWorker(QThread):
    """Background erase worker with cooperative cancellation"""
    progress = pyqtSignal(float)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, wrapper, mode, start_addr=None, end_addr=None, sector=None, reset_after=False):
        super().__init__()
        self._wrapper = wrapper
        self._mode = mode
        self._start_addr = start_addr
        self._end_addr = end_addr
        self._sector = sector
        self._reset_after = reset_after
        self._cancelled = False
        
    def cancel(self):
        """Request cancellation - cooperative, not forced"""
        self._cancelled = True
        
    def is_cancelled(self) -> bool:
        return self._cancelled
        
    def run(self):
        try:
            if self._cancelled:
                self.finished.emit(False, "已取消")
                return
                
            def on_progress(p):
                if self._cancelled:
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
            
            if self._cancelled:
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


class ErasePage(QWidget):
    """Chip erase page"""
    
    log_message = pyqtSignal(str)
    operation_started = pyqtSignal()
    operation_finished = pyqtSignal(bool, str)
    
    def __init__(self, wrapper, config, parent=None):
        super().__init__(parent)
        self._wrapper = wrapper
        self._config = config
        self._worker: Optional[EraseWorker] = None
        self._connected = False
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("擦除操作"))
        
        # Mode card
        mode_card = CardWidget()
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.addWidget(StrongBodyLabel("擦除模式"))
        
        self.chip_radio = RadioButton("全片擦除")
        self.chip_radio.setChecked(True)
        self.chip_radio.toggled.connect(self._on_mode_changed)
        mode_layout.addWidget(self.chip_radio)
        
        self.sector_radio = RadioButton("扇区擦除")
        self.sector_radio.toggled.connect(self._on_mode_changed)
        mode_layout.addWidget(self.sector_radio)
        
        self.range_radio = RadioButton("地址范围擦除")
        self.range_radio.toggled.connect(self._on_mode_changed)
        mode_layout.addWidget(self.range_radio)
        
        layout.addWidget(mode_card)
        
        # Sector card
        self.sector_card = CardWidget()
        sector_layout = QVBoxLayout(self.sector_card)
        sector_layout.addWidget(StrongBodyLabel("扇区设置"))
        
        sector_row = QHBoxLayout()
        sector_row.addWidget(BodyLabel("扇区号:"))
        self.sector_spin = SpinBox()
        self.sector_spin.setRange(0, 255)
        sector_row.addWidget(self.sector_spin)
        sector_row.addStretch()
        sector_layout.addLayout(sector_row)
        
        self.sector_card.hide()
        layout.addWidget(self.sector_card)
        
        # Range card
        self.range_card = CardWidget()
        range_layout = QVBoxLayout(self.range_card)
        range_layout.addWidget(StrongBodyLabel("地址范围设置"))
        
        range_row = QHBoxLayout()
        range_row.addWidget(BodyLabel("起始地址:"))
        self.start_edit = LineEdit()
        self.start_edit.setPlaceholderText("0x08000000")
        self.start_edit.setMaximumWidth(150)
        range_row.addWidget(self.start_edit)
        
        range_row.addWidget(BodyLabel("结束地址:"))
        self.end_edit = LineEdit()
        self.end_edit.setPlaceholderText("0x0801FFFF")
        self.end_edit.setMaximumWidth(150)
        range_row.addWidget(self.end_edit)
        range_row.addStretch()
        range_layout.addLayout(range_row)
        
        self.range_card.hide()
        layout.addWidget(self.range_card)
        
        # Options card
        opt_card = CardWidget()
        opt_layout = QVBoxLayout(opt_card)
        opt_layout.addWidget(StrongBodyLabel("擦除选项"))
        
        from qfluentwidgets import CheckBox
        opt_row = QHBoxLayout()
        self.reset_check = CheckBox("擦除后复位")
        opt_row.addWidget(self.reset_check)
        opt_row.addStretch()
        opt_layout.addLayout(opt_row)
        
        layout.addWidget(opt_card)
        
        # Progress card
        prog_card = CardWidget()
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.addWidget(StrongBodyLabel("擦除进度"))
        
        self.progress_bar = ProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.progress_bar)
        
        self.status_label = CaptionLabel("就绪")
        prog_layout.addWidget(self.status_label)
        
        layout.addWidget(prog_card)
        
        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.erase_btn = PrimaryPushButton("开始擦除", icon=FluentIcon.DELETE)
        self.erase_btn.clicked.connect(self._start_erase)
        self.erase_btn.setEnabled(False)
        btn_row.addWidget(self.erase_btn)
        
        self.cancel_btn = PushButton("取消", icon=FluentIcon.CANCEL)
        self.cancel_btn.clicked.connect(self._cancel_erase)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_row)
        layout.addStretch()
        
    def _on_mode_changed(self):
        self.sector_card.setVisible(self.sector_radio.isChecked())
        self.range_card.setVisible(self.range_radio.isChecked())
        
    def set_connected(self, connected: bool):
        self._connected = connected
        self.erase_btn.setEnabled(connected)
        
    def _start_erase(self):
        if self.chip_radio.isChecked():
            mode = "chip"
            start_addr = None
            end_addr = None
            sector = None
        elif self.sector_radio.isChecked():
            mode = "sector"
            start_addr = None
            end_addr = None
            sector = self.sector_spin.value()
        else:
            mode = "range"
            try:
                start_text = self.start_edit.text().strip()
                end_text = self.end_edit.text().strip()
                start_addr = int(start_text, 16) if start_text.startswith('0x') else int(start_text)
                end_addr = int(end_text, 16) if end_text.startswith('0x') else int(end_text)
                sector = None
            except ValueError:
                self.log_message.emit("无效的地址")
                return
                
        self.progress_bar.setValue(0)
        self.erase_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        self._worker = EraseWorker(
            self._wrapper, mode, start_addr, end_addr, sector,
            self.reset_check.isChecked()
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
        
        self.log_message.emit(f"开始擦除 ({mode})")
        self.operation_started.emit()
        
    def _cancel_erase(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()  # Request cooperative cancellation
            self._worker.wait(3000)  # Wait up to 3 seconds
            if self._worker.isRunning():
                # Only terminate as last resort
                LOG.warning("Worker did not respond to cancel, forcing termination")
                self._worker.terminate()
                self._worker.wait()
            self._on_finished(False, "已取消")
            
    def _on_progress(self, value):
        self.progress_bar.setValue(int(value * 100))
        
    def _on_status(self, text):
        self.status_label.setText(text)
        
    def _on_finished(self, success, message):
        self.progress_bar.setValue(100 if success else 0)
        self.status_label.setText(message)
        self.erase_btn.setEnabled(self._connected)
        self.cancel_btn.setEnabled(False)
        
        # Only show error notification - success is handled by StateToolTip
        if not success:
            InfoBar.error("失败", message, position=InfoBarPosition.TOP_RIGHT,
                         parent=self.window(), duration=5000)
        
        self.log_message.emit(message)
        self.operation_finished.emit(success, message)
