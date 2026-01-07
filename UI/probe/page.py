#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probe Page - Main UI Component
Probe management and connection page
"""

import logging
from typing import Optional, List

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem, QFileDialog

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, ToolButton,
    LineEdit, ComboBox, EditableComboBox, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, StrongBodyLabel, SearchLineEdit, ListWidget,
    InfoBadge, CheckBox, IndeterminateProgressBar, InfoBar, InfoBarPosition,
    MessageBox
)

from Core.pyocd_wrapper import ConnectMode, ResetType
from Core.chip_config import ChipConfigManager, ChipConfig, get_default_flash_start

from UI.probe.scanner import ProbeScanner
from UI.probe.worker import ConnectWorker
from UI.probe.preset_manager import PresetManagerMixin

LOG = logging.getLogger(__name__)


class ProbePage(PresetManagerMixin, QWidget):
    """Probe management and connection page
    
    This page provides:
    - Debug probe detection and selection
    - Target chip selection and configuration
    - Chip preset management (load, save, import, export)
    - Connection options (frequency, mode)
    - Target reset controls
    """
    
    connection_changed = pyqtSignal(bool)
    log_message = pyqtSignal(str)
    config_applied = pyqtSignal(object)  # Emits ChipConfig when preset is applied
    
    def __init__(self, wrapper, config, parent=None):
        super().__init__(parent)
        self._wrapper = wrapper
        self._config = config
        self._connected = False
        self._scanner: Optional[ProbeScanner] = None
        self._connect_worker: Optional[ConnectWorker] = None
        self._all_targets: List[str] = []
        
        # Chip config manager
        self._chip_config_mgr = ChipConfigManager()
        self._current_chip_config: Optional[ChipConfig] = None
        
        self._init_ui()
        self._load_targets()
        self._load_presets()
        self._start_scanning()
        
    def _init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("探针与连接"))
        
        # Probe card
        probe_card = self._create_probe_card()
        layout.addWidget(probe_card)
        
        # Chip Preset Card
        preset_card = self._create_preset_card()
        layout.addWidget(preset_card)
        
        # Target card
        target_card = self._create_target_card()
        layout.addWidget(target_card)
        
        # Options card
        opt_card = self._create_options_card()
        layout.addWidget(opt_card)
        
        # Reset card
        reset_card = self._create_reset_card()
        layout.addWidget(reset_card)
        
        layout.addStretch()
    
    def _create_probe_card(self) -> CardWidget:
        """Create the probe detection card"""
        probe_card = CardWidget()
        probe_layout = QVBoxLayout(probe_card)
        
        header = QHBoxLayout()
        header.addWidget(StrongBodyLabel("检测到的探针"))
        self.scan_btn = ToolButton(FluentIcon.SYNC)
        self.scan_btn.clicked.connect(self._scan_probes)
        header.addWidget(self.scan_btn)
        header.addStretch()
        probe_layout.addLayout(header)
        
        self.probe_list = ListWidget()
        self.probe_list.setMaximumHeight(120)
        probe_layout.addWidget(self.probe_list)
        
        self.no_probe_label = CaptionLabel("未检测到探针")
        probe_layout.addWidget(self.no_probe_label)
        
        return probe_card
    
    def _create_preset_card(self) -> CardWidget:
        """Create the chip preset management card"""
        preset_card = CardWidget()
        preset_layout = QVBoxLayout(preset_card)
        
        preset_header = QHBoxLayout()
        preset_header.addWidget(StrongBodyLabel("芯片预设配置"))
        
        self.import_preset_btn = ToolButton(FluentIcon.DOWNLOAD)
        self.import_preset_btn.setToolTip("导入预设")
        self.import_preset_btn.clicked.connect(self._import_preset)
        preset_header.addWidget(self.import_preset_btn)
        
        self.export_preset_btn = ToolButton(FluentIcon.UP)
        self.export_preset_btn.setToolTip("导出预设")
        self.export_preset_btn.clicked.connect(self._export_preset)
        preset_header.addWidget(self.export_preset_btn)
        
        self.save_preset_btn = ToolButton(FluentIcon.SAVE)
        self.save_preset_btn.setToolTip("保存当前设置为预设")
        self.save_preset_btn.clicked.connect(self._save_current_as_preset)
        preset_header.addWidget(self.save_preset_btn)
        
        preset_header.addStretch()
        preset_layout.addLayout(preset_header)
        
        # Vendor filter
        vendor_row = QHBoxLayout()
        vendor_row.addWidget(BodyLabel("厂商:"))
        self.vendor_combo = ComboBox()
        self.vendor_combo.setMinimumWidth(150)
        self.vendor_combo.currentTextChanged.connect(self._on_vendor_changed)
        vendor_row.addWidget(self.vendor_combo)
        
        vendor_row.addWidget(BodyLabel("预设:"))
        self.preset_combo = ComboBox()
        self.preset_combo.setMinimumWidth(250)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        vendor_row.addWidget(self.preset_combo)
        
        self.apply_preset_btn = PushButton("应用预设", icon=FluentIcon.ACCEPT)
        self.apply_preset_btn.clicked.connect(self._apply_preset)
        vendor_row.addWidget(self.apply_preset_btn)
        vendor_row.addStretch()
        preset_layout.addLayout(vendor_row)
        
        # Preset info label
        self.preset_info = CaptionLabel("")
        preset_layout.addWidget(self.preset_info)
        
        return preset_card
    
    def _create_target_card(self) -> CardWidget:
        """Create the target chip selection card"""
        target_card = CardWidget()
        target_layout = QVBoxLayout(target_card)
        target_layout.addWidget(StrongBodyLabel("目标芯片"))
        
        self.target_search = SearchLineEdit()
        self.target_search.setPlaceholderText("搜索芯片...")
        self.target_search.textChanged.connect(self._filter_targets)
        target_layout.addWidget(self.target_search)
        
        row = QHBoxLayout()
        self.target_combo = ComboBox()
        self.target_combo.setMinimumWidth(300)
        row.addWidget(self.target_combo)
        row.addStretch()
        target_layout.addLayout(row)
        
        # Pack file
        pack_row = QHBoxLayout()
        pack_row.addWidget(BodyLabel("CMSIS-Pack:"))
        self.pack_edit = LineEdit()
        self.pack_edit.setPlaceholderText("可选: .pack 文件")
        pack_row.addWidget(self.pack_edit)
        self.pack_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.pack_btn.clicked.connect(self._browse_pack)
        pack_row.addWidget(self.pack_btn)
        target_layout.addLayout(pack_row)
        
        return target_card
    
    def _create_options_card(self) -> CardWidget:
        """Create the connection options card"""
        opt_card = CardWidget()
        opt_layout = QVBoxLayout(opt_card)
        opt_layout.addWidget(StrongBodyLabel("连接选项"))
        
        opt_row = QHBoxLayout()
        opt_row.addWidget(BodyLabel("SWD频率:"))
        self.freq_combo = EditableComboBox()
        self.freq_combo.addItems(["100 kHz", "500 kHz", "1 MHz", "2 MHz", "4 MHz", "8 MHz", "10 MHz"])
        self.freq_combo.setText("100 kHz")  # 默认 100 kHz (最稳定)
        self.freq_combo.setPlaceholderText("输入或选择频率")
        opt_row.addWidget(self.freq_combo)
        
        opt_row.addWidget(BodyLabel("连接模式:"))
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["Under Reset", "Halt", "Pre-Reset", "Attach"])
        opt_row.addWidget(self.mode_combo)
        opt_row.addStretch()
        opt_layout.addLayout(opt_row)
        
        # Connection mode tooltip/description
        mode_desc = CaptionLabel("💡 Under Reset: 最可靠 | Halt: 暂停CPU | Pre-Reset: 预复位 | Attach: 附加到运行中的程序")
        opt_layout.addWidget(mode_desc)
        
        # Progress bar (hidden by default)
        self.connect_progress = IndeterminateProgressBar()
        self.connect_progress.hide()
        opt_layout.addWidget(self.connect_progress)
        
        self.connect_status = CaptionLabel("")
        opt_layout.addWidget(self.connect_status)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.cancel_btn = PushButton("取消", icon=FluentIcon.CANCEL)
        self.cancel_btn.clicked.connect(self._cancel_connect)
        self.cancel_btn.hide()
        btn_row.addWidget(self.cancel_btn)
        
        self.connect_btn = PrimaryPushButton("连接", icon=FluentIcon.LINK)
        self.connect_btn.clicked.connect(self._toggle_connection)
        btn_row.addWidget(self.connect_btn)
        opt_layout.addLayout(btn_row)
        
        return opt_card
    
    def _create_reset_card(self) -> CardWidget:
        """Create the reset control card"""
        reset_card = CardWidget()
        reset_layout = QVBoxLayout(reset_card)
        
        reset_header = QHBoxLayout()
        reset_header.addWidget(StrongBodyLabel("复位控制"))
        reset_help_btn = ToolButton(FluentIcon.QUESTION)
        reset_help_btn.setToolTip("点击查看复位类型说明")
        reset_help_btn.clicked.connect(self._show_reset_help)
        reset_header.addWidget(reset_help_btn)
        reset_header.addStretch()
        reset_layout.addLayout(reset_header)
        
        reset_row = QHBoxLayout()
        reset_row.addWidget(BodyLabel("复位类型:"))
        self.reset_combo = ComboBox()
        self.reset_combo.addItems(["Default", "Hardware", "Software", "SYSRESETREQ"])
        self.reset_combo.setToolTip(
            "Default: 默认复位方式\n"
            "Hardware: 硬件复位(需RESET引脚)\n"
            "Software: 软件复位(AIRCR寄存器)\n"
            "SYSRESETREQ: 系统复位请求"
        )
        reset_row.addWidget(self.reset_combo)
        
        self.halt_check = CheckBox("复位后暂停")
        self.halt_check.setToolTip("复位后暂停CPU执行，用于调试")
        reset_row.addWidget(self.halt_check)
        reset_row.addStretch()
        
        self.reset_btn = PushButton("复位", icon=FluentIcon.UPDATE)
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._do_reset)
        reset_row.addWidget(self.reset_btn)
        
        reset_layout.addLayout(reset_row)
        
        # Reset type description
        reset_desc = CaptionLabel("💡 Default: 通用 | Hardware: 最彻底(需RESET线) | Software: 仅复位CPU | SYSRESETREQ: 系统级")
        reset_layout.addWidget(reset_desc)
        
        return reset_card
        
    def _start_scanning(self):
        """Start background probe scanning"""
        self._scanner = ProbeScanner(self._wrapper)
        self._scanner.probes_found.connect(self._update_probe_list)
        self._scanner.start()
        
    def stop_scanning(self):
        """Stop background probe scanning"""
        if self._scanner:
            self._scanner.stop()
            
    def _scan_probes(self):
        """Manually trigger probe scan"""
        probes = self._wrapper.list_probes()
        self._update_probe_list(probes)
        self.log_message.emit(f"发现 {len(probes)} 个探针")
        
    def _update_probe_list(self, probes):
        """Update the probe list UI"""
        self.probe_list.clear()
        if probes:
            self.no_probe_label.hide()
            self.probe_list.show()
            for p in probes:
                self.probe_list.addItem(f"{p.description} [{p.unique_id[:12]}...]")
        else:
            self.no_probe_label.show()
            self.probe_list.hide()
            
    def _load_targets(self):
        """Load available targets"""
        self._all_targets = self._wrapper.list_targets()
        self._update_target_combo(self._all_targets)
        
        # Load last used settings
        last_target = self._config.get_last_target()
        if last_target:
            idx = self.target_combo.findText(last_target)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
                
        last_pack = self._config.get_last_pack()
        if last_pack:
            self.pack_edit.setText(last_pack)
            
        last_freq = self._config.get_last_frequency()
        freq_text_map = {100000: "100 kHz", 500000: "500 kHz", 1000000: "1 MHz", 
                        2000000: "2 MHz", 4000000: "4 MHz", 8000000: "8 MHz", 10000000: "10 MHz"}
        if last_freq in freq_text_map:
            self.freq_combo.setText(freq_text_map[last_freq])
        else:
            # Custom frequency - format nicely
            if last_freq >= 1000000:
                self.freq_combo.setText(f"{last_freq / 1000000:.1f} MHz")
            elif last_freq >= 1000:
                self.freq_combo.setText(f"{last_freq / 1000} kHz")
            else:
                self.freq_combo.setText("1 MHz")  # default
        
    def _update_target_combo(self, targets):
        """Update target combo box"""
        current = self.target_combo.currentText()
        self.target_combo.clear()
        self.target_combo.addItems(targets)
        idx = self.target_combo.findText(current)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)
            
    def _filter_targets(self, text):
        """Filter target list based on search text"""
        if not text:
            self._update_target_combo(self._all_targets)
        else:
            filtered = [t for t in self._all_targets if text.lower() in t.lower()]
            self._update_target_combo(filtered)
            
    def _browse_pack(self):
        """Browse for CMSIS-Pack file"""
        path, _ = QFileDialog.getOpenFileName(self, "选择 Pack", "", "CMSIS-Pack (*.pack)")
        if path:
            self.pack_edit.setText(path)
            
    def _toggle_connection(self):
        """Toggle connection state"""
        if self._connected:
            self._disconnect()
        else:
            self._connect()
            
    def _connect(self):
        """Start connection process"""
        target = self.target_combo.currentText()
        if not target:
            self.log_message.emit("请选择目标芯片")
            return
            
        # Get selected probe
        probe_id = None
        selected_items = self.probe_list.selectedItems()
        if selected_items:
            # Extract probe ID from list item text
            text = selected_items[0].text()
            if '[' in text and ']' in text:
                probe_id = text.split('[')[1].split(']')[0].replace('...', '')
            
        # Parse frequency from text (EditableComboBox)
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
        
        mode_map = {0: ConnectMode.UNDER_RESET, 1: ConnectMode.HALT, 2: ConnectMode.PRE_RESET, 3: ConnectMode.ATTACH}
        mode = mode_map.get(self.mode_combo.currentIndex(), ConnectMode.UNDER_RESET)
        
        pack = self.pack_edit.text() or None
        
        # Show progress
        self.connect_btn.setEnabled(False)
        self.cancel_btn.show()
        self.connect_progress.show()
        self.connect_status.setText(f"正在连接到 {target}...")
        self.log_message.emit(f"连接到 {target}...")
        
        # Start connection in background thread
        self._connect_worker = ConnectWorker(
            self._wrapper, target, probe_id, freq, mode, pack
        )
        self._connect_worker.finished.connect(self._on_connect_finished)
        self._connect_worker.start()
        
        # Save settings for next time
        self._config.set_last_target(target)
        self._config.set_last_frequency(freq)
        if pack:
            self._config.set_last_pack(pack)
    
    def _cancel_connect(self):
        """Cancel ongoing connection"""
        if self._connect_worker and self._connect_worker.isRunning():
            self.connect_status.setText("正在取消...")
            self._connect_worker.cancel()
            # Force terminate after timeout
            if not self._connect_worker.wait(2000):  # 2 second timeout
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
            
            # Save to history
            target = self.target_combo.currentText()
            self._config.add_recent_target(target)
            pack = self.pack_edit.text()
            if pack:
                self._config.add_recent_pack(pack)
                
            self.connection_changed.emit(True)
        else:
            self.connect_status.setText(f"{message}")
            
        self.log_message.emit(message)
            
    def _disconnect(self):
        """Disconnect from target"""
        self._wrapper.disconnect()
        self._connected = False
        self._update_ui_connected(False)
        self.connect_status.setText("已断开")
        self.connection_changed.emit(False)
        
    def _update_ui_connected(self, connected):
        """Update UI based on connection state"""
        if connected:
            self.connect_btn.setText("断开")
            self.connect_btn.setIcon(FluentIcon.CANCEL)
            self.reset_btn.setEnabled(True)
        else:
            self.connect_btn.setText("连接")
            self.connect_btn.setIcon(FluentIcon.LINK)
            self.reset_btn.setEnabled(False)
            
    def _do_reset(self):
        """Execute reset operation"""
        if not self._connected:
            return
        types = [ResetType.DEFAULT, ResetType.HARDWARE, ResetType.SOFTWARE, ResetType.SYSRESET]
        reset_type = types[self.reset_combo.currentIndex()]
        halt = self.halt_check.isChecked()
        
        if self._wrapper.reset(reset_type, halt):
            self.log_message.emit("复位完成")
        else:
            self.log_message.emit("复位失败")
    
    def _show_reset_help(self):
        """Show reset type help dialog"""
        help_text = """【复位类型说明】

• Default (默认复位)
  使用目标芯片的默认复位方式，最安全的选择。

• Hardware (硬件复位)
  通过 nRST 引脚触发硬件复位。
  需要调试器连接到目标板的 RESET 引脚。
  最彻底的复位方式，会复位所有外设。

• Software (软件复位)
  通过 AIRCR 寄存器触发软件复位。
  不需要 RESET 引脚连接。
  只复位 CPU 核心，部分外设状态可能保留。

• SYSRESETREQ (系统复位请求)
  通过 AIRCR.SYSRESETREQ 位触发。
  请求系统级复位，复位范围取决于芯片实现。

【复位后暂停】
勾选后，复位完成时 CPU 会停止在复位向量处，
便于调试启动代码。"""
        
        box = MessageBox("复位类型帮助", help_text, self.window())
        box.exec()
