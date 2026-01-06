#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe connection page"""

import logging
from typing import Optional, List

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem, QFileDialog

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, ToolButton,
    LineEdit, ComboBox, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, StrongBodyLabel, SearchLineEdit, ListWidget,
    InfoBadge, CheckBox, IndeterminateProgressBar, InfoBar, InfoBarPosition
)

from Core.pyocd_wrapper import ConnectMode, ResetType
from Core.chip_config import ChipConfigManager, ChipConfig, get_default_flash_start

LOG = logging.getLogger(__name__)


class ProbeScanner(QThread):
    """Background probe scanner"""
    probes_found = pyqtSignal(list)
    
    def __init__(self, wrapper):
        super().__init__()
        self._wrapper = wrapper
        self._running = True
        
    def run(self):
        import time
        while self._running:
            probes = self._wrapper.list_probes()
            self.probes_found.emit(probes)
            for _ in range(20):  # 2 second interval
                if not self._running:
                    break
                time.sleep(0.1)
                
    def stop(self):
        self._running = False
        self.wait()


class ConnectWorker(QThread):
    """Background connection worker"""
    finished = pyqtSignal(bool, str)
    
    def __init__(self, wrapper, target, probe_id, frequency, connect_mode, pack_path):
        super().__init__()
        self._wrapper = wrapper
        self._target = target
        self._probe_id = probe_id
        self._frequency = frequency
        self._connect_mode = connect_mode
        self._pack_path = pack_path
        self._cancelled = False
        
    def cancel(self):
        """Request cancellation"""
        self._cancelled = True
        # Force disconnect to interrupt any blocking operation
        try:
            self._wrapper.disconnect()
        except:
            pass
        
    def run(self):
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


class ProbePage(QWidget):
    """Probe management and connection page"""
    
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("探针与连接"))
        
        # Probe card
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
        
        layout.addWidget(probe_card)
        
        # ========== Chip Preset Card (NEW) ==========
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
        
        layout.addWidget(preset_card)
        
        # Target card
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
        
        layout.addWidget(target_card)
        
        # Options card
        opt_card = CardWidget()
        opt_layout = QVBoxLayout(opt_card)
        opt_layout.addWidget(StrongBodyLabel("连接选项"))
        
        opt_row = QHBoxLayout()
        opt_row.addWidget(BodyLabel("SWD频率:"))
        self.freq_combo = ComboBox()
        self.freq_combo.addItems(["100 kHz", "500 kHz", "1 MHz", "2 MHz", "4 MHz", "8 MHz", "10 MHz"])
        self.freq_combo.setCurrentIndex(0)  # 默认 100 kHz (最稳定)
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
        
        layout.addWidget(opt_card)
        
        # Reset card
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
        layout.addWidget(reset_card)
        
        layout.addStretch()
        
    def _start_scanning(self):
        self._scanner = ProbeScanner(self._wrapper)
        self._scanner.probes_found.connect(self._update_probe_list)
        self._scanner.start()
        
    def stop_scanning(self):
        if self._scanner:
            self._scanner.stop()
            
    def _scan_probes(self):
        probes = self._wrapper.list_probes()
        self._update_probe_list(probes)
        self.log_message.emit(f"发现 {len(probes)} 个探针")
        
    def _update_probe_list(self, probes):
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
        freq_map = {100000: 0, 500000: 1, 1000000: 2, 2000000: 3, 4000000: 4, 8000000: 5, 10000000: 6}
        self.freq_combo.setCurrentIndex(freq_map.get(last_freq, 2))  # 默认 1 MHz
        
    def _update_target_combo(self, targets):
        current = self.target_combo.currentText()
        self.target_combo.clear()
        self.target_combo.addItems(targets)
        idx = self.target_combo.findText(current)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)
            
    def _filter_targets(self, text):
        if not text:
            self._update_target_combo(self._all_targets)
        else:
            filtered = [t for t in self._all_targets if text.lower() in t.lower()]
            self._update_target_combo(filtered)
    
    # ========== Preset Management Methods ==========
    
    def _load_presets(self):
        """Load chip presets into UI"""
        # Load vendors
        vendors = self._chip_config_mgr.get_vendors()
        self.vendor_combo.clear()
        self.vendor_combo.addItem("全部厂商")
        self.vendor_combo.addItems(vendors)
        
        # Load all presets
        self._update_preset_combo()
    
    def _update_preset_combo(self):
        """Update preset combo based on selected vendor"""
        vendor = self.vendor_combo.currentText()
        
        if vendor == "全部厂商" or not vendor:
            presets = self._chip_config_mgr.get_all_presets()
        else:
            presets = self._chip_config_mgr.get_presets_by_vendor(vendor)
        
        self.preset_combo.clear()
        self.preset_combo.addItem("-- 选择预设 --")
        
        for key, cfg in sorted(presets.items(), key=lambda x: x[1].name):
            self.preset_combo.addItem(f"{cfg.name} ({cfg.target})", key)
    
    def _on_vendor_changed(self, vendor: str):
        """Handle vendor selection change"""
        self._update_preset_combo()
    
    def _on_preset_changed(self, text: str):
        """Handle preset selection change - show info"""
        if not text or text.startswith("--"):
            self.preset_info.setText("")
            self._current_chip_config = None
            return
        
        # Get preset key from combo data
        idx = self.preset_combo.currentIndex()
        if idx <= 0:
            return
            
        key = self.preset_combo.itemData(idx)
        if not key:
            return
            
        config = self._chip_config_mgr.get_preset(key)
        if config:
            self._current_chip_config = config
            # Show preset info
            info_parts = [
                f"目标: {config.target}",
                f"Flash: 0x{config.flash_start:08X}",
                f"频率: {config.default_frequency // 1000}kHz",
                f"模式: {config.connect_mode}",
            ]
            if config.description:
                info_parts.append(config.description)
            if config.notes:
                info_parts.append(f"备注: {config.notes}")
            self.preset_info.setText(" | ".join(info_parts))
    
    def _apply_preset(self):
        """Apply selected preset to current settings"""
        if not self._current_chip_config:
            InfoBar.warning("提示", "请先选择一个预设", parent=self.window(), 
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        config = self._current_chip_config
        
        # Apply target
        idx = self.target_combo.findText(config.target)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)
        else:
            # Target not in list, try to search
            self.target_search.setText(config.target)
            idx = self.target_combo.findText(config.target)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
        
        # Apply frequency
        freq_map = {100000: 0, 500000: 1, 1000000: 2, 2000000: 3, 4000000: 4, 8000000: 5, 10000000: 6}
        freq_idx = freq_map.get(config.default_frequency, 2)
        self.freq_combo.setCurrentIndex(freq_idx)
        
        # Apply connect mode
        mode_map = {"under-reset": 0, "halt": 1, "pre-reset": 2, "attach": 3}
        mode_idx = mode_map.get(config.connect_mode.lower(), 0)
        self.mode_combo.setCurrentIndex(mode_idx)
        
        # Apply pack file if specified
        if config.pack_file:
            self.pack_edit.setText(config.pack_file)
        
        # Emit signal for other components (e.g., flash page to update address)
        self.config_applied.emit(config)
        
        self.log_message.emit(f"已应用预设: {config.name}")
        InfoBar.success("成功", f"已应用预设: {config.name}", parent=self.window(),
                       position=InfoBarPosition.TOP_RIGHT)
    
    def _save_current_as_preset(self):
        """Save current settings as a new preset with enhanced dialog"""
        from UI.save_preset_dialog import SavePresetDialog
        
        target = self.target_combo.currentText()
        if not target:
            InfoBar.warning("提示", "请先选择目标芯片", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        # Get current settings to pre-fill dialog
        freq_map = {0: 100000, 1: 500000, 2: 1000000, 3: 2000000, 4: 4000000, 5: 8000000, 6: 10000000}
        freq = freq_map.get(self.freq_combo.currentIndex(), 1000000)
        
        mode_map = {0: "under-reset", 1: "halt", 2: "pre-reset", 3: "attach"}
        mode = mode_map.get(self.mode_combo.currentIndex(), "under-reset")
        
        # Determine vendor from target name
        vendor = "Unknown"
        target_lower = target.lower()
        if target_lower.startswith("stm32"):
            vendor = "STMicroelectronics"
        elif target_lower.startswith("gd32"):
            vendor = "GigaDevice"
        elif target_lower.startswith("mm32"):
            vendor = "MindMotion"
        elif target_lower.startswith("nrf"):
            vendor = "Nordic"
        elif target_lower.startswith("lpc") or target_lower.startswith("mimx"):
            vendor = "NXP"
        elif target_lower.startswith("at32"):
            vendor = "Artery"
        elif target_lower.startswith("apm32"):
            vendor = "APM/Geehy"
        elif target_lower.startswith("ch32"):
            vendor = "WCH"
        
        # Build initial data for dialog
        initial_data = {
            'name': f"{target.upper()} Custom",
            'target': target,
            'vendor': vendor,
            'chip_family': target[:5].upper() if len(target) >= 5 else target.upper(),
            'flash_start': hex(get_default_flash_start(target)),
            'frequency': freq,
            'connect_mode': mode,
            'pack_file': self.pack_edit.text(),
            'description': f"用户自定义预设 - {target}"
        }
        
        # Show dialog
        dialog = SavePresetDialog(self, initial_data)
        if dialog.exec() != 1:  # QDialog.Accepted
            return
        
        preset_data = dialog.get_preset_data()
        export_path = dialog.get_export_path()
        
        # Create config
        config = self._chip_config_mgr.create_config_from_current(
            name=preset_data['name'],
            target=preset_data['target'],
            vendor=preset_data['vendor'],
            flash_start=int(preset_data['flash_start'], 16) if preset_data['flash_start'].startswith('0x') else int(preset_data['flash_start']),
            frequency=preset_data['frequency'],
            connect_mode=preset_data['connect_mode'],
            pack_file=preset_data.get('pack_file', ''),
            description=preset_data.get('description', '')
        )
        
        # Save to user presets
        key = f"user_{preset_data['target']}_{preset_data['name']}".lower().replace(" ", "_")
        self._chip_config_mgr.add_user_preset(key, config)
        
        # Also export to file if user selected export option
        if dialog.should_export_to_file() and export_path:
            import json
            try:
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
                self.log_message.emit(f"预设已导出到: {export_path}")
            except Exception as e:
                self.log_message.emit(f"导出文件失败: {e}")
        
        # Refresh combo
        self._update_preset_combo()
        
        self.log_message.emit(f"已保存预设: {preset_data['name']}")
        InfoBar.success("成功", f"已保存预设: {preset_data['name']}", parent=self.window(),
                       position=InfoBarPosition.TOP_RIGHT)
    
    def _import_preset(self):
        """Import preset from JSON file"""
        from Core.config import config
        from pathlib import Path
        import os
        
        # Get last import dir or default to Doc/ChipConfigs
        last_import_dir = config.get('last_preset_import_dir', '')
        if not last_import_dir or not os.path.isdir(last_import_dir):
            project_root = Path(__file__).parent.parent
            chip_configs_dir = project_root / "Doc" / "ChipConfigs"
            if chip_configs_dir.exists():
                last_import_dir = str(chip_configs_dir)
            else:
                last_import_dir = ""
        
        path, _ = QFileDialog.getOpenFileName(
            self, "导入芯片预设", last_import_dir, "JSON Files (*.json)")
        if not path:
            return
        
        # Remember directory
        config.set('last_preset_import_dir', os.path.dirname(path))
        
        result = self._chip_config_mgr.import_preset(Path(path))
        if result:
            self._update_preset_combo()
            self.log_message.emit(f"已导入预设: {result}")
            InfoBar.success("成功", f"已导入预设", parent=self.window(),
                           position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.error("失败", "导入预设失败", parent=self.window(),
                         position=InfoBarPosition.TOP_RIGHT)
    
    def _export_preset(self):
        """Export current preset to JSON file with enhanced path selection"""
        if not self._current_chip_config:
            InfoBar.warning("提示", "请先选择一个预设", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        from UI.save_preset_dialog import SavePresetDialog
        
        config = self._current_chip_config
        
        # Build initial data from current config
        initial_data = {
            'name': config.name,
            'target': config.target,
            'vendor': config.vendor,
            'chip_family': config.chip_family,
            'flash_start': hex(config.flash_start),
            'frequency': config.frequency,
            'connect_mode': config.connect_mode,
            'pack_file': config.pack_file or '',
            'description': config.description or ''
        }
        
        # Show dialog
        dialog = SavePresetDialog(self, initial_data, export_only=True)
        dialog.setWindowTitle("导出芯片预设")
        if dialog.exec() != 1:  # QDialog.Accepted
            return
        
        export_path = dialog.get_export_path()
        if not export_path:
            return
        
        import json
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            self.log_message.emit(f"已导出预设: {export_path}")
            InfoBar.success("成功", f"已导出预设到: {export_path}", parent=self.window(),
                           position=InfoBarPosition.TOP_RIGHT)
        except Exception as e:
            self.log_message.emit(f"导出失败: {e}")
            InfoBar.error("失败", f"导出失败: {e}", parent=self.window(),
                         position=InfoBarPosition.TOP_RIGHT)
    
    def get_current_chip_config(self) -> Optional[ChipConfig]:
        """Get currently selected/applied chip config"""
        return self._current_chip_config
            
    def _browse_pack(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Pack", "", "CMSIS-Pack (*.pack)")
        if path:
            self.pack_edit.setText(path)
            
    def _toggle_connection(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()
            
    def _connect(self):
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
            
        freq_map = {0: 100000, 1: 500000, 2: 1000000, 3: 2000000, 4: 4000000, 5: 8000000, 6: 10000000}
        freq = freq_map.get(self.freq_combo.currentIndex(), 1000000)
        
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
        self._wrapper.disconnect()
        self._connected = False
        self._update_ui_connected(False)
        self.connect_status.setText("已断开")
        self.connection_changed.emit(False)
        
    def _update_ui_connected(self, connected):
        if connected:
            self.connect_btn.setText("断开")
            self.connect_btn.setIcon(FluentIcon.CANCEL)
            self.reset_btn.setEnabled(True)
        else:
            self.connect_btn.setText("连接")
            self.connect_btn.setIcon(FluentIcon.LINK)
            self.reset_btn.setEnabled(False)
            
    def _do_reset(self):
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
        from qfluentwidgets import MessageBox
        
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
