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
    InfoBar, InfoBarPosition, SpinBox, MessageBox
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
        
        # Current chip configuration
        self._flash_start = 0x08000000  # Default STM32
        self._flash_size = 0x20000      # 128KB default
        self._sector_size = 0x800       # 2KB default sector size
        self._target_name = "Unknown"
        self._pack_device = None        # Actual device from pack
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("擦除操作"))
        
        # Chip info card (shows current chip flash info)
        info_card = CardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.addWidget(StrongBodyLabel("当前芯片配置"))
        
        self.chip_info_label = CaptionLabel("未配置芯片，请先在探测页面应用芯片配置")
        self.chip_info_label.setWordWrap(True)
        info_layout.addWidget(self.chip_info_label)
        
        layout.addWidget(info_card)
        
        # Mode card
        mode_card = CardWidget()
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.addWidget(StrongBodyLabel("擦除模式"))
        
        self.chip_radio = RadioButton("全片擦除")
        self.chip_radio.setChecked(True)
        self.chip_radio.toggled.connect(self._on_mode_changed)
        mode_layout.addWidget(self.chip_radio)
        
        # Full chip erase hint
        self.chip_erase_hint = CaptionLabel("")
        self.chip_erase_hint.setStyleSheet("color: #888;")
        mode_layout.addWidget(self.chip_erase_hint)
        
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
        self.sector_spin.valueChanged.connect(self._update_sector_info)
        sector_row.addWidget(self.sector_spin)
        sector_row.addStretch()
        sector_layout.addLayout(sector_row)
        
        # Sector info hint
        self.sector_info_label = CaptionLabel("")
        self.sector_info_label.setWordWrap(True)
        sector_layout.addWidget(self.sector_info_label)
        
        self.sector_card.hide()
        layout.addWidget(self.sector_card)
        
        # Range card
        self.range_card = CardWidget()
        range_layout = QVBoxLayout(self.range_card)
        range_layout.addWidget(StrongBodyLabel("地址范围设置"))
        
        range_row = QHBoxLayout()
        range_row.addWidget(BodyLabel("起始地址:"))
        self.start_edit = LineEdit()
        self.start_edit.setText(f"0x{self._flash_start:08X}")
        self.start_edit.setMaximumWidth(150)
        range_row.addWidget(self.start_edit)
        
        range_row.addWidget(BodyLabel("结束地址:"))
        self.end_edit = LineEdit()
        self.end_edit.setText(f"0x{self._flash_start + self._flash_size - 1:08X}")
        self.end_edit.setMaximumWidth(150)
        range_row.addWidget(self.end_edit)
        range_row.addStretch()
        range_layout.addLayout(range_row)
        
        # Add hint label for address range
        self.range_hint = CaptionLabel("提示: 地址范围将根据当前芯片配置自动更新")
        range_layout.addWidget(self.range_hint)
        
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
        self.cancel_btn.clicked.connect(self._confirm_cancel_erase)
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
    
    def _update_sector_info(self):
        """Update sector info label when sector number changes"""
        sector_num = self.sector_spin.value()
        sector_start = self._flash_start + (sector_num * self._sector_size)
        sector_end = sector_start + self._sector_size - 1
        sector_kb = self._sector_size / 1024
        
        # Check if sector is valid
        max_sector = (self._flash_size // self._sector_size) - 1 if self._sector_size > 0 else 0
        
        if sector_num > max_sector:
            self.sector_info_label.setText(
                f"⚠ 扇区号超出范围！最大扇区号: {max_sector}\n"
                f"当前芯片共 {max_sector + 1} 个扇区"
            )
            self.sector_info_label.setStyleSheet("color: #ff6b6b;")
        else:
            self.sector_info_label.setText(
                f"扇区 {sector_num}: 0x{sector_start:08X} - 0x{sector_end:08X} ({sector_kb:.1f}KB)\n"
                f"有效扇区范围: 0 - {max_sector} (共 {max_sector + 1} 个扇区)"
            )
            self.sector_info_label.setStyleSheet("color: #888;")
    
    def _update_chip_info_display(self):
        """Update all chip-related info displays"""
        flash_kb = self._flash_size // 1024
        flash_end = self._flash_start + self._flash_size - 1
        sector_count = self._flash_size // self._sector_size if self._sector_size > 0 else 0
        sector_kb = self._sector_size / 1024
        
        # Build chip info text
        chip_lines = [f"预设目标: {self._target_name}"]
        if self._pack_device and self._pack_device.lower() != self._target_name.lower():
            chip_lines.append(f"Pack设备: {self._pack_device}")
        chip_lines.append(f"Flash: {flash_kb}KB @ 0x{self._flash_start:08X} - 0x{flash_end:08X}")
        chip_lines.append(f"扇区: {sector_count} 个, 每个 {sector_kb:.1f}KB")
        
        # Update chip info card
        self.chip_info_label.setText("\n".join(chip_lines))
        
        # Update full chip erase hint
        self.chip_erase_hint.setText(
            f"    将擦除整个 Flash: 0x{self._flash_start:08X} - 0x{flash_end:08X} ({flash_kb}KB)"
        )
        
        # Update sector spin range
        max_sector = sector_count - 1 if sector_count > 0 else 0
        self.sector_spin.setRange(0, max(0, max_sector))
        
        # Update sector info
        self._update_sector_info()
        
        # Update range hint
        self.range_hint.setText(f"当前: {self._target_name} | Flash {flash_kb}KB @ 0x{self._flash_start:08X}")
    
    def apply_chip_config(self, chip_config):
        """Apply chip configuration to update address range.
        
        Called when chip configuration changes (from ProbePage or ChipConfigPage).
        
        Args:
            chip_config: ChipConfig dataclass with flash_start, flash_size, etc.
        """
        # Get values from config first
        flash_start = getattr(chip_config, 'flash_start', 0x08000000)
        flash_size = getattr(chip_config, 'flash_size', 0)
        sector_size = 0x800  # Default 2KB
        target_name = getattr(chip_config, 'target', 'Unknown')
        pack_device_name = None  # Actual device name from pack
        
        # Try to get more info from pack
        if hasattr(chip_config, 'pack_file') and chip_config.pack_file:
            try:
                from Core.pack_parser import PackParser
                from Core.chip_config import normalize_pack_path
                pack_path = normalize_pack_path(chip_config.pack_file)
                parser = PackParser(pack_path)
                pack_info = parser.parse()
                if pack_info and pack_info.devices:
                    # First try to find matching device by target name
                    device = pack_info.get_device(target_name)
                    
                    # If not found, try to match by chip_family
                    if device is None:
                        chip_family = getattr(chip_config, 'chip_family', '')
                        if chip_family:
                            device = pack_info.get_device(chip_family)
                    
                    # If still not found, use first device from pack
                    if device is None and pack_info.devices:
                        device = pack_info.devices[0]
                        LOG.info(f"Using first pack device: {device.name}")
                    
                    if device:
                        pack_device_name = device.name
                        # Only override flash_size if config has 0
                        if flash_size == 0:
                            flash_size = device.flash_size
                        # Only override flash_start if config has default STM32 value
                        # and pack has different value (likely correct for this chip)
                        if flash_start == 0x08000000 and device.flash_start != 0x08000000:
                            flash_start = device.flash_start
                        # Get sector size from algorithms if available
                        # FM33 series typically has 512B or 2KB sectors
                        if 'fm33' in device.name.lower():
                            sector_size = 0x200  # 512B for FM33
            except Exception as e:
                LOG.warning(f"Failed to get flash info from pack: {e}")
        
        # Use reasonable defaults if still 0
        if flash_size == 0:
            # Try to estimate from target name
            if '01' in target_name:
                flash_size = 64 * 1024   # 64KB
            elif '02' in target_name:
                flash_size = 128 * 1024  # 128KB
            elif '04' in target_name:
                flash_size = 256 * 1024  # 256KB
            else:
                flash_size = 128 * 1024  # Default 128KB
        
        # Estimate sector size based on flash size if not set from pack
        if sector_size == 0x800:  # Still default
            if flash_size <= 64 * 1024:  # <= 64KB
                sector_size = 0x400  # 1KB
            elif flash_size <= 256 * 1024:  # <= 256KB
                sector_size = 0x800  # 2KB
            elif flash_size <= 1024 * 1024:  # <= 1MB
                sector_size = 0x1000  # 4KB
            else:
                sector_size = 0x4000  # 16KB
        
        self._flash_start = flash_start
        self._flash_size = flash_size
        self._sector_size = sector_size
        self._target_name = target_name
        self._pack_device = pack_device_name
        
        # Update UI
        flash_end = flash_start + flash_size - 1
        self.start_edit.setText(f"0x{flash_start:08X}")
        self.end_edit.setText(f"0x{flash_end:08X}")
        
        # Update all info displays
        self._update_chip_info_display()
        
        LOG.info(f"Erase page config applied: {target_name} Flash 0x{flash_start:08X} ({flash_size // 1024}KB, sector {sector_size}B)")
        
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
            
            # Validate sector number
            max_sector = (self._flash_size // self._sector_size) - 1 if self._sector_size > 0 else 0
            if sector > max_sector:
                InfoBar.error(
                    "扇区号无效", 
                    f"扇区号 {sector} 超出范围，最大扇区号为 {max_sector}",
                    position=InfoBarPosition.TOP_RIGHT,
                    parent=self.window(), duration=5000
                )
                return
        else:
            mode = "range"
            try:
                start_text = self.start_edit.text().strip()
                end_text = self.end_edit.text().strip()
                start_addr = int(start_text, 16) if start_text.startswith('0x') else int(start_text)
                end_addr = int(end_text, 16) if end_text.startswith('0x') else int(end_text)
                sector = None
                
                # Validate address range
                flash_end = self._flash_start + self._flash_size - 1
                if start_addr < self._flash_start or end_addr > flash_end:
                    InfoBar.warning(
                        "地址范围警告", 
                        f"地址范围超出 Flash 区域 (0x{self._flash_start:08X} - 0x{flash_end:08X})",
                        position=InfoBarPosition.TOP_RIGHT,
                        parent=self.window(), duration=5000
                    )
                if start_addr > end_addr:
                    InfoBar.error(
                        "地址无效", 
                        "起始地址不能大于结束地址",
                        position=InfoBarPosition.TOP_RIGHT,
                        parent=self.window(), duration=5000
                    )
                    return
            except ValueError:
                InfoBar.error(
                    "地址格式错误", 
                    "请输入有效的十六进制地址 (如 0x00000000)",
                    position=InfoBarPosition.TOP_RIGHT,
                    parent=self.window(), duration=5000
                )
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
    
    def _confirm_cancel_erase(self):
        """Show confirmation dialog before cancelling erase"""
        if not self._worker or not self._worker.isRunning():
            return
            
        msg = MessageBox(
            "⚠️ 确认取消擦除",
            "擦除过程中取消可能导致Flash处于不一致状态。\n"
            "建议等待当前操作完成，或取消后重新进行全片擦除。\n\n"
            "确定要取消吗？",
            self.window()
        )
        msg.yesButton.setText("取消擦除")
        msg.cancelButton.setText("继续等待")
        
        if msg.exec():
            self._cancel_erase()
        
    def _cancel_erase(self):
        """Cancel erase operation with safety handling
        
        Note: We NEVER use terminate() as it can leave USB handles and
        interpreter state corrupted. Instead, we rely on cooperative
        cancellation between sector boundaries and inform the user to wait.
        """
        if self._worker and self._worker.isRunning():
            self.log_message.emit("⚠️ 正在请求取消擦除操作...")
            self._worker.cancel()  # Request cooperative cancellation
            
            # Wait for cooperative cancellation (between sector boundaries)
            self.log_message.emit("⏳ 等待当前扇区擦除完成（最多30秒）...")
            if not self._worker.wait(30000):  # 30s timeout
                # Worker still running - inform user
                LOG.error("Worker did not respond to cancel request within 30s")
                self.log_message.emit(
                    "⚠️ 擦除操作无法及时取消，建议：\\n"
                    "1. 继续等待操作完成\\n"
                    "2. 重新拔插USB探针\\n"
                    "3. 重启应用程序\\n"
                    "❌ 绝不建议强制关闭 - 可能损坏USB驱动状态"
                )
                # 启用按钮让用户可以重试
                self.erase_btn.setEnabled(False)
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
        self.erase_btn.setEnabled(self._connected)
        self.cancel_btn.setEnabled(False)
        
        # Only show error notification - success is handled by StateToolTip
        if not success:
            InfoBar.error("失败", message, position=InfoBarPosition.TOP_RIGHT,
                         parent=self.window(), duration=5000)
        
        self.log_message.emit(message)
        self.operation_finished.emit(success, message)
