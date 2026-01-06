#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flash programming page"""

import os
import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, ToolButton,
    LineEdit, ComboBox, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, StrongBodyLabel, CheckBox, ProgressBar, Slider,
    InfoBar, InfoBarPosition, SpinBox
)

from Core.pyocd_wrapper import ResetType
from Core.chip_config import ChipConfig

LOG = logging.getLogger(__name__)


class FlashWorker(QThread):
    """Background flash worker"""
    progress = pyqtSignal(float)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, wrapper, file_path, address, verify, reset_after):
        super().__init__()
        self._wrapper = wrapper
        self._file_path = file_path
        self._address = address
        self._verify = verify
        self._reset_after = reset_after
        
    def run(self):
        try:
            self.status.emit(f"正在烧录: {os.path.basename(self._file_path)}")
            
            def on_progress(p):
                self.progress.emit(p)
                
            success = self._wrapper.flash_file(
                self._file_path,
                self._address,
                verify=self._verify,
                progress_callback=on_progress
            )
            
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


class FlashPage(QWidget):
    """Flash programming page"""
    
    log_message = pyqtSignal(str)
    operation_started = pyqtSignal()
    operation_finished = pyqtSignal(bool, str)
    
    def __init__(self, wrapper, config, parent=None):
        super().__init__(parent)
        self._wrapper = wrapper
        self._config = config
        self._worker: Optional[FlashWorker] = None
        self._connected = False
        
        self._init_ui()
        self._load_config()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("烧录程序"))
        
        # File card
        file_card = CardWidget()
        file_layout = QVBoxLayout(file_card)
        file_layout.addWidget(StrongBodyLabel("固件文件"))
        
        # Recent files combo
        recent_row = QHBoxLayout()
        recent_row.addWidget(BodyLabel("最近文件:"))
        self.recent_combo = ComboBox()
        self.recent_combo.setMinimumWidth(400)
        self.recent_combo.currentTextChanged.connect(self._on_recent_selected)
        recent_row.addWidget(self.recent_combo)
        recent_row.addStretch()
        file_layout.addLayout(recent_row)
        
        row = QHBoxLayout()
        self.file_edit = LineEdit()
        self.file_edit.setPlaceholderText("选择 .hex / .bin / .elf 文件")
        self.file_edit.textChanged.connect(self._update_file_info)
        row.addWidget(self.file_edit)
        
        self.file_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.file_btn.clicked.connect(self._browse_file)
        row.addWidget(self.file_btn)
        file_layout.addLayout(row)
        
        self.file_info = CaptionLabel("")
        file_layout.addWidget(self.file_info)
        
        layout.addWidget(file_card)
        
        # Address card
        addr_card = CardWidget()
        addr_layout = QVBoxLayout(addr_card)
        addr_layout.addWidget(StrongBodyLabel("地址设置"))
        
        addr_row = QHBoxLayout()
        addr_row.addWidget(BodyLabel("起始地址:"))
        self.addr_edit = LineEdit()
        self.addr_edit.setPlaceholderText("0x08000000 (HEX/ELF自动识别)")
        self.addr_edit.setMaximumWidth(200)
        addr_row.addWidget(self.addr_edit)
        
        self.addr_auto = CheckBox("自动 (HEX/ELF)")
        self.addr_auto.setChecked(True)
        self.addr_auto.stateChanged.connect(self._on_addr_auto_changed)
        addr_row.addWidget(self.addr_auto)
        addr_row.addStretch()
        addr_layout.addLayout(addr_row)
        
        layout.addWidget(addr_card)
        
        # Options card
        opt_card = CardWidget()
        opt_layout = QVBoxLayout(opt_card)
        opt_layout.addWidget(StrongBodyLabel("烧录选项"))
        
        opt_row1 = QHBoxLayout()
        self.verify_check = CheckBox("烧录后校验")
        self.verify_check.setChecked(True)
        opt_row1.addWidget(self.verify_check)
        
        self.reset_check = CheckBox("烧录后复位")
        self.reset_check.setChecked(True)
        opt_row1.addWidget(self.reset_check)
        
        self.erase_check = CheckBox("烧录前擦除")
        self.erase_check.setChecked(True)
        opt_row1.addWidget(self.erase_check)
        opt_row1.addStretch()
        opt_layout.addLayout(opt_row1)
        
        layout.addWidget(opt_card)
        
        # Progress card
        prog_card = CardWidget()
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.addWidget(StrongBodyLabel("烧录进度"))
        
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
        
        self.flash_btn = PrimaryPushButton("开始烧录", icon=FluentIcon.DOWNLOAD)
        self.flash_btn.clicked.connect(self._start_flash)
        self.flash_btn.setEnabled(False)
        btn_row.addWidget(self.flash_btn)
        
        self.cancel_btn = PushButton("取消", icon=FluentIcon.CANCEL)
        self.cancel_btn.clicked.connect(self._cancel_flash)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_row)
        layout.addStretch()
        
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择固件文件", "",
            "Firmware Files (*.hex *.bin *.elf);;Intel HEX (*.hex);;Binary (*.bin);;ELF (*.elf)"
        )
        if path:
            self.file_edit.setText(path)
            
    def _update_file_info(self, path):
        if path and os.path.exists(path):
            size = os.path.getsize(path)
            ext = os.path.splitext(path)[1].lower()
            type_name = {"hex": "Intel HEX", ".bin": "Binary", ".elf": "ELF"}.get(ext, "Unknown")
            self.file_info.setText(f"{type_name} - {size:,} 字节")
            self.flash_btn.setEnabled(self._connected)
        else:
            self.file_info.setText("")
            self.flash_btn.setEnabled(False)
            
    def _on_addr_auto_changed(self, state):
        self.addr_edit.setEnabled(not state)
        
    def set_connected(self, connected: bool):
        self._connected = connected
        has_file = bool(self.file_edit.text() and os.path.exists(self.file_edit.text()))
        self.flash_btn.setEnabled(connected and has_file)
        
    def _start_flash(self):
        file_path = self.file_edit.text()
        if not file_path or not os.path.exists(file_path):
            self.log_message.emit("请选择有效的固件文件")
            return
            
        address = None
        if not self.addr_auto.isChecked():
            try:
                addr_text = self.addr_edit.text().strip()
                address = int(addr_text, 16) if addr_text.startswith('0x') else int(addr_text)
            except ValueError:
                self.log_message.emit("无效的起始地址")
                return
                
        self.progress_bar.setValue(0)
        self.flash_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        self._worker = FlashWorker(
            self._wrapper,
            file_path,
            address,
            self.verify_check.isChecked(),
            self.reset_check.isChecked()
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
        
        self._config.add_recent_file(file_path)
        self.log_message.emit(f"开始烧录: {file_path}")
        self.operation_started.emit()
        
    def _cancel_flash(self):
        if self._worker and self._worker.isRunning():
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
        self.flash_btn.setEnabled(self._connected)
        self.cancel_btn.setEnabled(False)
        
        if success:
            InfoBar.success("成功", message, position=InfoBarPosition.TOP_RIGHT, parent=self.window())
        else:
            InfoBar.error("失败", message, position=InfoBarPosition.TOP_RIGHT, parent=self.window())
            
        self.log_message.emit(message)
        self.operation_finished.emit(success, message)
        
    def _on_recent_selected(self, path):
        """Handle recent file selection"""
        if path and os.path.exists(path):
            self.file_edit.setText(path)
        
    def _load_config(self):
        # Load recent files into combo
        recent = self._config.get_recent_files()
        self.recent_combo.clear()
        self.recent_combo.addItem("-- 选择最近文件 --")
        for f in recent:
            if os.path.exists(f):
                self.recent_combo.addItem(f)
        
        # Set last file
        if recent and os.path.exists(recent[0]):
            self.file_edit.setText(recent[0])
            
        # Load flash settings
        self.verify_check.setChecked(self._config.get_flash_verify())
        self.reset_check.setChecked(self._config.get_flash_reset())
        
    def _save_config(self):
        """Save current settings"""
        self._config.set_flash_verify(self.verify_check.isChecked())
        self._config.set_flash_reset(self.reset_check.isChecked())
    
    def apply_chip_config(self, chip_config: ChipConfig):
        """Apply chip configuration - set flash address"""
        if chip_config and chip_config.flash_start:
            self.addr_edit.setText(f"0x{chip_config.flash_start:08X}")
            self.addr_auto.setChecked(False)
            self.log_message.emit(f"已设置起始地址: 0x{chip_config.flash_start:08X} ({chip_config.name})")
