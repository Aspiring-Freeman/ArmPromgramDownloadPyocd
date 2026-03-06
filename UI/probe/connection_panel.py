#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Connection Panel - Target connection options and control UI component
"""

import logging
from typing import Optional, List, Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, ComboBox, EditableComboBox,
    BodyLabel, CaptionLabel, StrongBodyLabel, FluentIcon, SearchLineEdit,
    IndeterminateProgressBar, InfoBar, InfoBarPosition
)

from Core.pyocd_wrapper import ConnectMode
from Core.chip_config import ChipConfig
from UI.probe.worker import ConnectWorker
from UI.tooltip_helper import install_tooltip

LOG = logging.getLogger(__name__)


class ConnectionPanel(CardWidget):
    """Connection options and control panel
    
    Provides:
    - Target chip selection with search
    - SWD frequency selection  
    - Connection mode selection
    - Connect/disconnect functionality
    
    Signals:
        connection_changed: Emitted when connection state changes
        target_changed: Emitted when target selection changes
        settings_changed: Emitted when frequency/mode changes
    """
    
    connection_changed = pyqtSignal(bool)
    target_changed = pyqtSignal(str)
    settings_changed = pyqtSignal()
    
    def __init__(self, wrapper, config, parent=None):
        super().__init__(parent)
        self._wrapper = wrapper
        self._config = config
        self._connected = False
        self._connect_worker: Optional[ConnectWorker] = None
        self._all_targets: List[str] = []
        self._base_targets: List[str] = []
        self._on_log_message: Optional[Callable[[str], None]] = None
        self._config_applied_checker: Optional[Callable[[], bool]] = None
        self._probe_id_getter: Optional[Callable[[], Optional[str]]] = None
        self._pack_path_getter: Optional[Callable[[], str]] = None
        
        self._init_ui()
        self._load_targets()
    
    def _init_ui(self):
        """Initialize connection panel UI"""
        layout = QVBoxLayout(self)
        layout.addWidget(StrongBodyLabel("连接选项"))
        
        # Target selection row
        target_row = QHBoxLayout()
        target_row.addWidget(BodyLabel("目标芯片:"))
        
        self.target_search = SearchLineEdit()
        self.target_search.setPlaceholderText("搜索...")
        self.target_search.setMinimumWidth(120)
        self.target_search.textChanged.connect(self._filter_targets)
        target_row.addWidget(self.target_search)
        
        self.target_combo = ComboBox()
        self.target_combo.setMinimumWidth(250)
        self.target_combo.currentTextChanged.connect(self._on_target_changed)
        target_row.addWidget(self.target_combo)
        
        target_row.addStretch()
        layout.addLayout(target_row)
        
        # Frequency and mode row
        opt_row = QHBoxLayout()
        opt_row.addWidget(BodyLabel("SWD频率:"))
        
        self.freq_combo = EditableComboBox()
        self.freq_combo.addItems(["100 kHz", "500 kHz", "1 MHz", "2 MHz", "4 MHz", "8 MHz", "10 MHz"])
        self.freq_combo.setText("1 MHz")
        self.freq_combo.setPlaceholderText("输入或选择频率")
        self.freq_combo.currentTextChanged.connect(self._on_freq_changed)
        opt_row.addWidget(self.freq_combo)
        
        opt_row.addWidget(BodyLabel("连接模式:"))
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["Under Reset", "Halt", "Pre-Reset", "Attach"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        opt_row.addWidget(self.mode_combo)
        
        opt_row.addStretch()
        layout.addLayout(opt_row)
        
        # Connection mode description
        mode_desc = CaptionLabel("💡 Under Reset: 最可靠 | Halt: 暂停CPU | Pre-Reset: 预复位 | Attach: 附加到运行中的程序")
        layout.addWidget(mode_desc)
        
        # Progress bar
        self.connect_progress = IndeterminateProgressBar()
        self.connect_progress.hide()
        layout.addWidget(self.connect_progress)
        
        self.connect_status = CaptionLabel("")
        layout.addWidget(self.connect_status)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.cancel_btn = PushButton("取消", icon=FluentIcon.CANCEL)
        self.cancel_btn.clicked.connect(self._cancel_connect)
        self.cancel_btn.hide()
        btn_row.addWidget(self.cancel_btn)
        
        self.connect_btn = PrimaryPushButton("连接", icon=FluentIcon.LINK)
        self.connect_btn.clicked.connect(self._toggle_connection)
        btn_row.addWidget(self.connect_btn)
        
        layout.addLayout(btn_row)
    
    def set_log_callback(self, callback: Callable[[str], None]):
        """Set callback for log messages"""
        self._on_log_message = callback
    
    def set_config_applied_checker(self, checker: Callable[[], bool]):
        """Set callback to check if config is applied"""
        self._config_applied_checker = checker
    
    def set_probe_id_getter(self, getter: Callable[[], Optional[str]]):
        """Set callback to get selected probe ID"""
        self._probe_id_getter = getter
    
    def set_pack_path_getter(self, getter: Callable[[], str]):
        """Set callback to get pack file path"""
        self._pack_path_getter = getter
    
    def _log(self, message: str):
        """Log message via callback"""
        if self._on_log_message:
            self._on_log_message(message)
    
    def _load_targets(self):
        """Load available targets"""
        self._all_targets = self._wrapper.list_targets()
        self._base_targets = self._all_targets.copy()
        self._update_target_combo(self._all_targets)
        
        # Load last used settings
        last_target = self._config.get_last_target()
        if last_target:
            idx = self.target_combo.findText(last_target)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
        
        last_freq = self._config.get_last_frequency()
        freq_text_map = {
            100000: "100 kHz", 500000: "500 kHz", 1000000: "1 MHz",
            2000000: "2 MHz", 4000000: "4 MHz", 8000000: "8 MHz", 10000000: "10 MHz"
        }
        if last_freq in freq_text_map:
            self.freq_combo.setText(freq_text_map[last_freq])
        elif last_freq:
            if last_freq >= 1000000:
                self.freq_combo.setText(f"{last_freq / 1000000:.1f} MHz")
            elif last_freq >= 1000:
                self.freq_combo.setText(f"{last_freq / 1000} kHz")
    
    def _update_target_combo(self, targets: List[str]):
        """Update target combo box"""
        current = self.target_combo.currentText()
        self.target_combo.clear()
        self.target_combo.addItems(targets)
        idx = self.target_combo.findText(current)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)
    
    def _filter_targets(self, text: str):
        """Filter target list based on search text"""
        if not text:
            self._update_target_combo(self._all_targets)
        else:
            filtered = [t for t in self._all_targets if text.lower() in t.lower()]
            self._update_target_combo(filtered)
    
    def _on_target_changed(self, text: str):
        """Handle target chip selection change"""
        if not text:
            return
        if self._connected:
            self._disconnect()
            self._log("⚠️ 目标芯片已更改，已自动断开连接")
        self.target_changed.emit(text)
        self.settings_changed.emit()
    
    def _on_freq_changed(self, text: str):
        """Handle frequency selection change"""
        if not text:
            return
        if self._connected:
            self._disconnect()
            self._log("⚠️ SWD频率已更改，已自动断开连接")
        self.settings_changed.emit()
    
    def _on_mode_changed(self, text: str):
        """Handle connection mode change"""
        if not text:
            return
        if self._connected:
            self._disconnect()
            self._log("⚠️ 连接模式已更改，已自动断开连接")
    
    def _toggle_connection(self):
        """Toggle connection state"""
        if self._connected:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        """Start connection process"""
        # Check if config is applied
        if self._config_applied_checker and not self._config_applied_checker():
            self._log("⚠️ 请先应用芯片配置")
            InfoBar.warning(
                "未应用配置",
                "请先点击'应用'按钮应用芯片配置后再连接",
                parent=self.window(),
                duration=4000,
                position=InfoBarPosition.TOP_RIGHT
            )
            return
        
        target = self.target_combo.currentText()
        if not target:
            self._log("⚠️ 请选择目标芯片")
            InfoBar.warning(
                "未选择目标",
                "请先选择或应用芯片配置，然后选择目标芯片",
                parent=self.window(),
                duration=4000,
                position=InfoBarPosition.TOP_RIGHT
            )
            return
        
        # Get probe ID
        probe_id = None
        if self._probe_id_getter:
            probe_id = self._probe_id_getter()
        
        # Parse frequency
        freq = self._parse_frequency()
        self._log(f"[DEBUG] 连接频率: {self.freq_combo.text()} -> {freq} Hz ({freq/1000000:.2f} MHz)")
        
        # Get connection mode
        mode_map = {
            0: ConnectMode.UNDER_RESET,
            1: ConnectMode.HALT,
            2: ConnectMode.PRE_RESET,
            3: ConnectMode.ATTACH
        }
        mode = mode_map.get(self.mode_combo.currentIndex(), ConnectMode.UNDER_RESET)
        
        # Get pack path
        pack = None
        if self._pack_path_getter:
            pack = self._pack_path_getter() or None
        
        # Show progress
        self.connect_btn.setEnabled(False)
        self.cancel_btn.show()
        self.connect_progress.show()
        self.connect_status.setText(f"正在连接到 {target}...")
        self._log(f"连接到 {target}...")
        
        # Start connection in background thread
        self._connect_worker = ConnectWorker(
            self._wrapper, target, probe_id, freq, mode, pack
        )
        self._connect_worker.finished.connect(self._on_connect_finished)
        self._connect_worker.start()
        
        # Save settings
        self._config.set_last_target(target)
        self._config.set_last_frequency(freq)
        if pack:
            self._config.set_last_pack(pack)
    
    def _parse_frequency(self) -> int:
        """Parse frequency from text"""
        freq_text = self.freq_combo.text().strip().lower()
        freq = 1000000  # default 1 MHz
        try:
            if 'mhz' in freq_text:
                freq_val = float(freq_text.replace('mhz', '').strip())
                freq = int(freq_val * 1000000)
            elif 'khz' in freq_text:
                freq_val = float(freq_text.replace('khz', '').strip())
                freq = int(freq_val * 1000)
            elif freq_text.isdigit():
                freq = int(freq_text)
        except (ValueError, AttributeError):
            freq = 1000000
        return freq
    
    def _cancel_connect(self):
        """Cancel ongoing connection"""
        if self._connect_worker and self._connect_worker.isRunning():
            self.connect_status.setText("正在取消...")
            self._connect_worker.cancel()
            if not self._connect_worker.wait(2000):
                self._connect_worker.terminate()
                self._connect_worker.wait()
            self._on_connect_finished(False, "连接已取消")
    
    def _on_connect_finished(self, success: bool, message: str):
        """Handle connection completion"""
        self.connect_progress.hide()
        self.cancel_btn.hide()
        self.connect_btn.setEnabled(True)
        
        if success:
            self._connected = True
            self._update_ui_connected(True)
            self.connect_status.setText("已连接")
            
            target = self.target_combo.currentText()
            self._config.add_recent_target(target)
            pack = self._pack_path_getter() if self._pack_path_getter else ""
            if pack:
                self._config.add_recent_pack(pack)
            
            self.connection_changed.emit(True)
        else:
            self.connect_status.setText(f"{message}")
        
        self._log(message)
    
    def _disconnect(self):
        """Disconnect from target"""
        self._wrapper.disconnect()
        self._connected = False
        self._update_ui_connected(False)
        self.connect_status.setText("已断开")
        self.connection_changed.emit(False)
    
    def _update_ui_connected(self, connected: bool):
        """Update UI based on connection state"""
        if connected:
            self.connect_btn.setText("断开")
            self.connect_btn.setIcon(FluentIcon.CANCEL)
        else:
            self.connect_btn.setText("连接")
            self.connect_btn.setIcon(FluentIcon.LINK)
    
    # === Public API ===
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self._connected
    
    def get_target(self) -> str:
        """Get current target name"""
        return self.target_combo.currentText()
    
    def set_target(self, target: str):
        """Set target selection"""
        idx = self.target_combo.findText(target)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)
        else:
            # Try case-insensitive
            target_lower = target.lower()
            for i in range(self.target_combo.count()):
                if self.target_combo.itemText(i).lower() == target_lower:
                    self.target_combo.setCurrentIndex(i)
                    return
            # Not found - filter and select first
            self.target_search.setText(target)
            if self.target_combo.count() > 0:
                self.target_combo.setCurrentIndex(0)
    
    def get_frequency(self) -> int:
        """Get current frequency in Hz"""
        return self._parse_frequency()
    
    def set_frequency(self, freq: int):
        """Set frequency"""
        if freq >= 1000000:
            self.freq_combo.setText(f"{freq // 1000000} MHz")
        else:
            self.freq_combo.setText(f"{freq // 1000} kHz")
    
    def get_connect_mode(self) -> ConnectMode:
        """Get current connection mode"""
        mode_map = {
            0: ConnectMode.UNDER_RESET,
            1: ConnectMode.HALT,
            2: ConnectMode.PRE_RESET,
            3: ConnectMode.ATTACH
        }
        return mode_map.get(self.mode_combo.currentIndex(), ConnectMode.UNDER_RESET)
    
    def set_connect_mode(self, mode: str):
        """Set connection mode"""
        mode_map = {"under-reset": 0, "halt": 1, "pre-reset": 2, "attach": 3}
        mode_idx = mode_map.get(mode.lower(), 0)
        self.mode_combo.setCurrentIndex(mode_idx)
    
    def add_pack_targets(self, pack_info, pack_name: str):
        """Add targets from pack to target combo"""
        if pack_info and pack_info.devices:
            self._all_targets = self._base_targets.copy()
            
            pack_targets = [dev.name.lower() for dev in pack_info.devices]
            current = self.target_combo.currentText()
            self.target_combo.clear()
            
            if pack_targets:
                self.target_combo.addItem(f"── {pack_name} ──")
                for t in pack_targets:
                    if t not in self._all_targets:
                        self._all_targets.append(t)
                    self.target_combo.addItem(t)
                self.target_combo.addItem("── 内置目标 ──")
            
            self.target_combo.addItems(self._base_targets)
            
            idx = self.target_combo.findText(current)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
    
    def disconnect_if_connected(self):
        """Disconnect if currently connected"""
        if self._connected:
            self._disconnect()
