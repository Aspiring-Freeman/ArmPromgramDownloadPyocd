#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flash programming page"""

from __future__ import annotations

import os
import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, ToolButton,
    LineEdit, ComboBox, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, StrongBodyLabel, CheckBox, ProgressBar, Slider,
    InfoBar, InfoBarPosition, MessageBox
)

from Core.pyocd_wrapper import ResetType
from Core.chip_config import ChipConfig
from UI.workers import FlashWorker

LOG = logging.getLogger(__name__)


class FlashPage(QWidget):
    """Flash programming page"""
    
    log_message = pyqtSignal(str)
    operation_started = pyqtSignal()
    operation_finished = pyqtSignal(bool, str)
    
    def __init__(self, wrapper, config, parent=None):
        super().__init__(parent)
        self._wrapper = wrapper
        self._config = config
        self._worker: FlashWorker | None = None
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
        self.recent_combo.setMinimumWidth(350)
        self.recent_combo.currentIndexChanged.connect(self._on_recent_selected)
        self._recent_files_map = {}  # index -> full path
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
        self.cancel_btn.clicked.connect(self._confirm_cancel_flash)
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
            type_name = {".hex": "Intel HEX", ".bin": "Binary", ".elf": "ELF"}.get(ext, "Unknown")
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
    
    def _confirm_cancel_flash(self):
        """Show confirmation dialog before cancelling flash"""
        if not self._worker or not self._worker.isRunning():
            return
            
        msg = MessageBox(
            "⚠️ 确认取消烧录",
            "烧录过程中取消可能导致固件不完整。\n"
            "建议等待当前操作完成，或取消后重新进行烧录。\n\n"
            "确定要取消吗？",
            self.window()
        )
        msg.yesButton.setText("取消烧录")
        msg.cancelButton.setText("继续等待")
        
        if msg.exec():
            self._cancel_flash()
        
    def _cancel_flash(self):
        """Cancel flash operation with safety handling
        
        Note: We NEVER use terminate() as it can leave USB handles and
        interpreter state corrupted. Instead, we rely on cooperative
        cancellation between page boundaries and inform the user to wait.
        """
        if self._worker and self._worker.isRunning():
            self.log_message.emit("⚠️ 正在请求取消烧录操作...")
            self._worker.cancel()  # Request cooperative cancellation
            
            # Wait for cooperative cancellation (between page boundaries)
            self.log_message.emit("⏳ 等待当前页写入完成（最多30秒）...")
            if not self._worker.wait(30000):  # 30s timeout
                # Worker still running - inform user
                LOG.error("Worker did not respond to cancel request within 30s")
                self.log_message.emit(
                    "⚠️ 烧录操作无法及时取消，建议：\\n"
                    "1. 继续等待操作完成\\n"
                    "2. 重新拔插USB探针\\n"
                    "3. 重启应用程序\\n"
                    "❌ 绝不建议强制关闭 - 可能损坏USB驱动状态"
                )
                # 启用按钮让用户可以重试
                self.flash_btn.setEnabled(False)
                self.cancel_btn.setEnabled(False)
                return
            
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
        
        # Only show error notification - success is handled by StateToolTip
        if not success:
            InfoBar.error("失败", message, position=InfoBarPosition.TOP_RIGHT, 
                         parent=self.window(), duration=5000)
        
        self.log_message.emit(message)
        self.operation_finished.emit(success, message)
        
    def _on_recent_selected(self, index):
        """Handle recent file selection"""
        if index > 0 and index in self._recent_files_map:
            path = self._recent_files_map[index]
            if os.path.exists(path):
                self.file_edit.setText(path)
        
    def _shorten_path(self, path: str, max_len: int = 60) -> str:
        """Shorten path for display, keeping filename and partial directory"""
        if len(path) <= max_len:
            return path
        
        # Get filename and directory
        filename = os.path.basename(path)
        dirname = os.path.dirname(path)
        
        # If filename alone is too long, just truncate
        if len(filename) >= max_len - 5:
            return "..." + filename[-(max_len - 3):]
        
        # Calculate remaining space for directory
        remaining = max_len - len(filename) - 4  # 4 for ".../"
        
        if remaining > 0:
            # Show last part of directory
            return "..." + dirname[-remaining:] + "/" + filename
        else:
            return filename
    
    def _load_config(self):
        # Load recent files into combo
        recent = self._config.get_recent_files()
        self.recent_combo.clear()
        self._recent_files_map = {}
        
        self.recent_combo.addItem("-- 选择最近文件 --")
        
        for idx, f in enumerate(recent, start=1):
            if os.path.exists(f):
                # Show shortened path but store full path
                display_name = self._shorten_path(f)
                self.recent_combo.addItem(display_name)
                self._recent_files_map[idx] = f
        
        # Set last file
        if recent and os.path.exists(recent[0]):
            self.file_edit.setText(recent[0])
            
        # Load flash settings
        self.verify_check.setChecked(self._config.get_flash_verify())
        self.reset_check.setChecked(self._config.get_flash_reset())
        
        # Load last address settings
        last_address = self._config.get_flash_address()
        auto_address = self._config.get_flash_auto_address()
        
        self.addr_auto.setChecked(auto_address)
        self.addr_edit.setEnabled(not auto_address)
        
        if last_address and not auto_address:
            self.addr_edit.setText(last_address)
        
    def _save_config(self):
        """Save current settings"""
        self._config.set_flash_verify(self.verify_check.isChecked())
        self._config.set_flash_reset(self.reset_check.isChecked())
        
        # Save address settings
        self._config.set_flash_address(self.addr_edit.text().strip())
        self._config.set_flash_auto_address(self.addr_auto.isChecked())
    
    def apply_chip_config(self, chip_config: ChipConfig):
        """Apply chip configuration - set flash address and validate
        
        This method is called when a chip config is applied from:
        - Preset selection
        - File import
        - Pack import
        """
        if not chip_config:
            return
            
        messages = []
        
        # 1. Set flash address if available
        if chip_config.flash_start is not None:
            self.addr_edit.setText(f"0x{chip_config.flash_start:08X}")
            self.addr_auto.setChecked(False)
            messages.append(f"起始地址: 0x{chip_config.flash_start:08X}")
            
            # 2. Validate address - warn if unusual
            # Common ARM flash start addresses: 0x08000000 (STM32), 0x00000000 (some chips), 
            # 0x10000000, 0x60000000, etc.
            addr = chip_config.flash_start
            if addr == 0:
                # Address 0 is valid for some chips (e.g., FM33LG04X, Nordic, etc.)
                # but can also indicate a misconfiguration, show info
                InfoBar.info(
                    "提示", 
                    "Flash地址为 0x00000000，请确认是否正确\n"
                    "如需修改，请取消勾选「自动检测」并手动输入地址",
                    parent=self.window(),
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=5000
                )
            elif addr > 0x80000000:
                # Address in upper memory range, might be RAM or peripheral
                InfoBar.warning(
                    "警告",
                    f"Flash地址 0x{addr:08X} 位于高地址区域\n"
                    "请确认这不是RAM或外设地址",
                    parent=self.window(),
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=5000
                )
        
        # 3. Check pack file requirement
        if chip_config.pack_file:
            from Core.chip_config import normalize_pack_path
            import os
            
            pack_path = normalize_pack_path(chip_config.pack_file)
            if os.path.exists(pack_path):
                pack_basename = os.path.basename(pack_path)
                messages.append(f"Pack文件: {pack_basename}")
                InfoBar.info(
                    "Pack 配置",
                    f"此芯片配置需要 Pack 文件:\n{pack_basename}\n"
                    "请确保在「探针连接」页面已加载相应的 Pack",
                    parent=self.window(),
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=6000
                )
            else:
                messages.append(f"⚠ Pack文件未找到: {chip_config.pack_file}")
                InfoBar.warning(
                    "Pack 文件缺失",
                    f"配置指定的 Pack 文件未找到:\n{chip_config.pack_file}\n"
                    "可能导致芯片识别失败",
                    parent=self.window(),
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=6000
                )
        
        # Log summary
        if messages:
            self.log_message.emit(f"已应用配置 [{chip_config.name}]: " + " | ".join(messages))
