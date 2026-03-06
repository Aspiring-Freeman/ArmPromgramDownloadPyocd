#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chip Configuration Panel - Chip preset and configuration UI component
Handles preset selection, file import, and CMSIS-Pack import modes
"""

import logging
from typing import Optional, Dict, Callable
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog

from qfluentwidgets import (
    CardWidget, PushButton, ToolButton, LineEdit, ComboBox, BodyLabel,
    CaptionLabel, StrongBodyLabel, FluentIcon, RadioButton, InfoBar,
    InfoBarPosition, MessageBox
)

from Core.chip_config import ChipConfigManager, ChipConfig, get_default_flash_start
from Core.pack_parser import PackParser, PackInfo

LOG = logging.getLogger(__name__)


class ChipConfigPanel(CardWidget):
    """Chip configuration panel with three configuration modes
    
    Modes:
    1. File import - Load from JSON config file
    2. Preset selection - Choose from built-in or user presets  
    3. Pack import - Load from CMSIS-Pack file
    
    Signals:
        config_applied: Emitted when a configuration is applied
        config_changed: Emitted when config selection changes (not yet applied)
    """
    
    config_applied = pyqtSignal(object)  # Emits ChipConfig
    config_changed = pyqtSignal()  # Selection changed, needs re-apply
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._chip_config_mgr = ChipConfigManager()
        self._current_chip_config: Optional[ChipConfig] = None
        self._pack_info: Optional[PackInfo] = None
        self._loaded_pack_path: Optional[str] = None
        self._preset_name_to_key: Dict[str, str] = {}
        self._pack_device_label_to_name: Dict[str, str] = {}
        self._config_applied = False
        self._on_log_message: Optional[Callable[[str], None]] = None
        
        self._init_ui()
        self._load_presets()
    
    def _init_ui(self):
        """Initialize chip configuration panel UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        header.addWidget(StrongBodyLabel("芯片配置"))
        header.addStretch()
        layout.addLayout(header)
        
        # === Configuration source selection (3 modes) ===
        source_label = CaptionLabel("选择配置来源:")
        layout.addWidget(source_label)
        
        # Mode 1: File import
        self.source_file_radio = RadioButton("从文件导入 (自定义配置，包含完整的Flash地址等信息)")
        self.source_file_radio.toggled.connect(self._on_source_changed)
        layout.addWidget(self.source_file_radio)
        
        self.file_widget = QWidget()
        file_inner = QHBoxLayout(self.file_widget)
        file_inner.setContentsMargins(20, 5, 0, 5)
        self.file_path_edit = LineEdit()
        self.file_path_edit.setPlaceholderText("选择 JSON 配置文件...")
        self.file_path_edit.setReadOnly(True)
        file_inner.addWidget(self.file_path_edit)
        self.file_browse_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.file_browse_btn.clicked.connect(self._browse_config_file)
        file_inner.addWidget(self.file_browse_btn)
        self.file_apply_btn = PushButton("应用", icon=FluentIcon.ACCEPT)
        self.file_apply_btn.clicked.connect(self._apply_file_config)
        file_inner.addWidget(self.file_apply_btn)
        self.file_widget.hide()
        layout.addWidget(self.file_widget)
        
        # Mode 2: Preset selection
        self.source_preset_radio = RadioButton("从预设选择 (内置预设或之前保存的用户预设)")
        self.source_preset_radio.setChecked(True)
        self.source_preset_radio.toggled.connect(self._on_source_changed)
        layout.addWidget(self.source_preset_radio)
        
        self.preset_widget = QWidget()
        preset_inner = QHBoxLayout(self.preset_widget)
        preset_inner.setContentsMargins(20, 5, 0, 5)
        
        preset_inner.addWidget(BodyLabel("厂商:"))
        self.vendor_combo = ComboBox()
        self.vendor_combo.setMinimumWidth(120)
        self.vendor_combo.currentTextChanged.connect(self._on_vendor_changed)
        preset_inner.addWidget(self.vendor_combo)
        
        preset_inner.addWidget(BodyLabel("预设:"))
        self.preset_combo = ComboBox()
        self.preset_combo.setMinimumWidth(200)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_inner.addWidget(self.preset_combo)
        
        self.apply_preset_btn = PushButton("应用", icon=FluentIcon.ACCEPT)
        self.apply_preset_btn.clicked.connect(self._apply_preset)
        preset_inner.addWidget(self.apply_preset_btn)
        
        self.delete_preset_btn = ToolButton(FluentIcon.DELETE)
        self.delete_preset_btn.setToolTip("删除当前预设")
        self.delete_preset_btn.clicked.connect(self._delete_preset)
        preset_inner.addWidget(self.delete_preset_btn)
        
        preset_inner.addStretch()
        layout.addWidget(self.preset_widget)
        
        # Mode 3: Pack import
        self.source_pack_radio = RadioButton("从 Pack 导入 (读取芯片信息，Flash地址为芯片默认值)")
        self.source_pack_radio.toggled.connect(self._on_source_changed)
        layout.addWidget(self.source_pack_radio)
        
        self.pack_widget = QWidget()
        pack_inner = QVBoxLayout(self.pack_widget)
        pack_inner.setContentsMargins(20, 5, 0, 5)
        
        pack_row1 = QHBoxLayout()
        pack_row1.addWidget(BodyLabel("Pack文件:"))
        self.pack_edit = LineEdit()
        self.pack_edit.setPlaceholderText("选择 CMSIS-Pack 文件 (.pack)")
        self.pack_edit.setReadOnly(True)
        pack_row1.addWidget(self.pack_edit, 1)
        self.pack_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.pack_btn.clicked.connect(self._browse_pack)
        pack_row1.addWidget(self.pack_btn)
        pack_inner.addLayout(pack_row1)
        
        pack_row2 = QHBoxLayout()
        pack_row2.addWidget(BodyLabel("选择芯片:"))
        self.pack_device_combo = ComboBox()
        self.pack_device_combo.setMinimumWidth(250)
        self.pack_device_combo.setPlaceholderText("先浏览Pack文件...")
        self.pack_device_combo.setEnabled(False)
        self.pack_device_combo.currentTextChanged.connect(self._on_pack_device_changed)
        pack_row2.addWidget(self.pack_device_combo)
        self.pack_apply_btn = PushButton("应用", icon=FluentIcon.ACCEPT)
        self.pack_apply_btn.clicked.connect(self._apply_pack_config)
        self.pack_apply_btn.setEnabled(False)
        pack_row2.addWidget(self.pack_apply_btn)
        pack_row2.addStretch()
        pack_inner.addLayout(pack_row2)
        
        self.pack_info_label = CaptionLabel("")
        pack_inner.addWidget(self.pack_info_label)
        
        self.pack_widget.hide()
        layout.addWidget(self.pack_widget)
        
        # === Current configuration info ===
        self.preset_info = CaptionLabel("💡 从预设选择芯片配置")
        layout.addWidget(self.preset_info)
        
        # === Export/Save buttons ===
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.export_preset_btn = PushButton("导出配置", icon=FluentIcon.UP)
        self.export_preset_btn.setToolTip("将当前配置导出到文件")
        self.export_preset_btn.clicked.connect(self._export_preset)
        btn_row.addWidget(self.export_preset_btn)
        
        self.save_preset_btn = PushButton("保存为预设", icon=FluentIcon.SAVE)
        self.save_preset_btn.setToolTip("将当前配置保存为用户预设")
        self.save_preset_btn.clicked.connect(self._save_current_as_preset)
        btn_row.addWidget(self.save_preset_btn)
        
        layout.addLayout(btn_row)
    
    def set_log_callback(self, callback: Callable[[str], None]):
        """Set callback for log messages"""
        self._on_log_message = callback
    
    def _log(self, message: str):
        """Log message via callback"""
        if self._on_log_message:
            self._on_log_message(message)
    
    def _load_presets(self):
        """Load vendors and presets into combo boxes"""
        presets = self._chip_config_mgr.get_all_presets()
        
        vendors = set()
        for key, config in presets.items():
            if config.vendor:
                vendors.add(config.vendor)
        
        self.vendor_combo.blockSignals(True)
        self.vendor_combo.clear()
        self.vendor_combo.addItem("全部")
        for vendor in sorted(vendors):
            self.vendor_combo.addItem(vendor)
        self.vendor_combo.blockSignals(False)
        
        self._update_preset_combo()
    
    def _on_vendor_changed(self, vendor: str):
        """Handle vendor selection change"""
        self._config_applied = False
        self.config_changed.emit()
        self._update_preset_combo()
    
    def _update_preset_combo(self):
        """Update preset combo based on selected vendor"""
        vendor = self.vendor_combo.currentText()
        presets = self._chip_config_mgr.get_all_presets()
        
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self._preset_name_to_key.clear()
        
        for key, config in presets.items():
            if vendor == "全部" or config.vendor == vendor:
                self.preset_combo.addItem(config.name)
                self._preset_name_to_key[config.name] = key
        
        self.preset_combo.blockSignals(False)
        
        if self.preset_combo.count() > 0:
            self._on_preset_changed(self.preset_combo.currentText())
        else:
            self.preset_info.setText("📋 没有找到匹配的预设")
    
    def _on_preset_changed(self, text: str):
        """Handle preset selection change"""
        LOG.debug(f"Preset changed: '{text}'")
        
        self._config_applied = False
        self.config_changed.emit()
        
        name = self.preset_combo.currentText()
        if name:
            key = self._preset_name_to_key.get(name)
            if key:
                config = self._chip_config_mgr.get_preset(key)
                if config:
                    info = f"目标: {config.target} | Flash: 0x{config.flash_start:08X}"
                    if config.pack_file:
                        info += f" | Pack: {config.pack_file.split('/')[-1]}"
                    self.preset_info.setText(f"👁 预览: {info} (点击'应用'生效)")
                    return
        
        self.preset_info.setText("👁 请选择预设并点击'应用'按钮")
    
    def _apply_preset(self):
        """Apply selected preset"""
        name = self.preset_combo.currentText()
        if not name:
            InfoBar.warning("提示", "请先选择预设", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        key = self._preset_name_to_key.get(name)
        if not key:
            InfoBar.warning("提示", f"无效的预设: {name}", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        config = self._chip_config_mgr.get_preset(key)
        if config:
            preserve_freq = (self._current_chip_config is not None and 
                           self._current_chip_config.name == config.name)
            
            self._current_chip_config = config
            self._config_applied = True
            
            info = f"目标: {config.target} | Flash: 0x{config.flash_start:08X}"
            self.preset_info.setText(f"✅ 已应用: {config.name} | {info}")
            
            self.config_applied.emit(config)
            InfoBar.success("成功", f"已应用预设: {config.name}", parent=self.window(),
                           position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.error("失败", "预设加载失败", parent=self.window(),
                         position=InfoBarPosition.TOP_RIGHT)
    
    def _delete_preset(self):
        """Delete selected preset"""
        name = self.preset_combo.currentText()
        if not name:
            return
        
        key = self._preset_name_to_key.get(name)
        if not key:
            return
        
        box = MessageBox("确认删除", f"确定要删除预设 '{name}' 吗？", self.window())
        if box.exec():
            if self._chip_config_mgr.delete_user_preset(key):
                self._load_presets()
                InfoBar.success("成功", f"已删除预设: {name}", parent=self.window(),
                               position=InfoBarPosition.TOP_RIGHT)
            else:
                InfoBar.error("失败", "删除预设失败", parent=self.window(),
                             position=InfoBarPosition.TOP_RIGHT)
    
    def _on_source_changed(self, checked: bool):
        """Handle configuration source change"""
        self._config_applied = False
        self.config_changed.emit()
        
        self.file_widget.hide()
        self.preset_widget.hide()
        self.pack_widget.hide()
        
        if self.source_file_radio.isChecked():
            self.file_widget.show()
            self.preset_info.setText("💡 从文件导入：加载之前导出的完整配置，包含自定义Flash地址")
        elif self.source_preset_radio.isChecked():
            self.preset_widget.show()
            self.preset_info.setText("💡 从预设选择：使用内置或用户保存的预设配置")
        elif self.source_pack_radio.isChecked():
            self.pack_widget.show()
            self.preset_info.setText("💡 从Pack导入：读取芯片默认配置，如需修改Flash地址请到烧录页面调整")
    
    def _browse_config_file(self):
        """Browse for config JSON file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", "", "JSON Files (*.json)")
        if path:
            old_path = self.file_path_edit.text()
            self.file_path_edit.setText(path)
            
            if old_path != path:
                LOG.debug(f"Config file changed: '{old_path}' -> '{path}'")
                self._config_applied = False
                self.preset_info.setText(f"👁 预览: {path.split('/')[-1]} (点击'应用'生效)")
                self.config_changed.emit()
    
    def _apply_file_config(self):
        """Apply configuration from file"""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            InfoBar.warning("提示", "请先选择配置文件", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        result = self._chip_config_mgr.import_preset(file_path)
        if result:
            self._load_presets()
            config = self._chip_config_mgr.get_preset(result)
            if config:
                self._current_chip_config = config
                self._config_applied = True
                
                info = f"目标: {config.target} | Flash: 0x{config.flash_start:08X}"
                self.preset_info.setText(f"✅ 已应用: {config.name} | {info}")
                
                self.config_applied.emit(config)
                InfoBar.success("成功", f"已应用配置: {config.name}", parent=self.window(),
                               position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.error("失败", "导入配置失败", parent=self.window(),
                         position=InfoBarPosition.TOP_RIGHT)
    
    def _browse_pack(self):
        """Browse for CMSIS-Pack file"""
        path, _ = QFileDialog.getOpenFileName(self, "选择 Pack", "", "CMSIS-Pack (*.pack)")
        if path:
            self.pack_edit.setText(path)
            self._parse_pack_file(path)
    
    def _parse_pack_file(self, pack_path: str):
        """Parse pack file and populate device combo"""
        try:
            parser = PackParser(pack_path)
            self._pack_info = parser.parse()
            
            if self._pack_info and self._pack_info.devices:
                self.pack_device_combo.blockSignals(True)
                self.pack_device_combo.clear()
                self._pack_device_label_to_name.clear()
                
                for dev in self._pack_info.devices:
                    flash_kb = dev.flash_size // 1024 if dev.flash_size else 0
                    label = f"{dev.name} (Flash: 0x{dev.flash_start:08X}, {flash_kb}KB)"
                    self.pack_device_combo.addItem(label)
                    self._pack_device_label_to_name[label] = dev.name
                
                self.pack_device_combo.blockSignals(False)
                self.pack_device_combo.setEnabled(True)
                self.pack_apply_btn.setEnabled(True)
                
                self.pack_info_label.setText(
                    f"✓ {self._pack_info.vendor}.{self._pack_info.name} v{self._pack_info.version} - "
                    f"包含 {len(self._pack_info.devices)} 个芯片"
                )
                self._loaded_pack_path = pack_path
            else:
                self._loaded_pack_path = None
                self.pack_device_combo.clear()
                self.pack_device_combo.setEnabled(False)
                self.pack_apply_btn.setEnabled(False)
                self.pack_info_label.setText("⚠ 无法解析Pack文件或没有设备信息")
                
        except Exception as e:
            LOG.exception(f"Error parsing pack file: {e}")
            self._loaded_pack_path = None
            self.pack_device_combo.clear()
            self.pack_device_combo.setEnabled(False)
            self.pack_apply_btn.setEnabled(False)
            self.pack_info_label.setText(f"⚠ 解析失败: {str(e)}")
    
    def _on_pack_device_changed(self, text: str):
        """Handle pack device selection change"""
        LOG.debug(f"Pack device changed: '{text}'")
        
        if not text:
            return
        
        self._config_applied = False
        self._log("⚠️ Pack芯片已更改，需要重新应用配置")
        self.config_changed.emit()
        self.preset_info.setText("👁 预览中 - 请点击「应用」按钮确认配置")
    
    def _apply_pack_config(self):
        """Apply configuration from Pack device selection"""
        if not self._pack_info:
            return
        
        label = self.pack_device_combo.currentText()
        if not label:
            InfoBar.warning("提示", "请先选择芯片", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        dev_name = self._pack_device_label_to_name.get(label)
        if not dev_name:
            dev_name = label.split(" (")[0]
        
        device = self._pack_info.get_device(dev_name)
        if not device:
            InfoBar.warning("提示", f"未找到芯片: {dev_name}", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        config = ChipConfig(
            name=f"{device.name} (从Pack)",
            vendor=self._pack_info.vendor,
            chip_family=device.family or device.name[:8],
            target=device.name.lower(),
            flash_start=device.flash_start or 0,
            flash_size=device.flash_size or 0,
            ram_start=device.ram_start or 0x20000000,
            ram_size=device.ram_size or 0,
            default_frequency=device.debug_clock or 1000000,
            connect_mode="under-reset",
            pack_file=self.pack_edit.text(),
        )
        
        self._current_chip_config = config
        self._config_applied = True
        
        flash_kb = device.flash_size // 1024 if device.flash_size else 0
        self.preset_info.setText(
            f"✅ 已应用: {device.name} | Flash: 0x{device.flash_start:08X} ({flash_kb}KB) | "
            f"⚠ 如需调整Flash地址，请到烧录页面修改"
        )
        
        self.config_applied.emit(config)
        InfoBar.success("成功", f"已应用: {device.name}", parent=self.window(),
                       position=InfoBarPosition.TOP_RIGHT)
    
    def _export_preset(self):
        """Export current configuration to file"""
        if not self._current_chip_config:
            InfoBar.warning("提示", "请先应用配置", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", f"{self._current_chip_config.name}.json", "JSON Files (*.json)")
        if path:
            if self._chip_config_mgr.export_preset(self._current_chip_config, path):
                InfoBar.success("成功", f"配置已导出到: {path}", parent=self.window(),
                               position=InfoBarPosition.TOP_RIGHT)
            else:
                InfoBar.error("失败", "导出配置失败", parent=self.window(),
                             position=InfoBarPosition.TOP_RIGHT)
    
    def _save_current_as_preset(self):
        """Save current configuration as user preset"""
        if not self._current_chip_config:
            InfoBar.warning("提示", "请先应用配置", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        from UI.save_preset_dialog import SavePresetDialog
        dialog = SavePresetDialog(self._current_chip_config, parent=self.window())
        if dialog.exec():
            new_name = dialog.get_preset_name()
            if new_name:
                config = ChipConfig(
                    name=new_name,
                    vendor=self._current_chip_config.vendor,
                    chip_family=self._current_chip_config.chip_family,
                    target=self._current_chip_config.target,
                    flash_start=self._current_chip_config.flash_start,
                    flash_size=self._current_chip_config.flash_size,
                    ram_start=self._current_chip_config.ram_start,
                    ram_size=self._current_chip_config.ram_size,
                    default_frequency=self._current_chip_config.default_frequency,
                    connect_mode=self._current_chip_config.connect_mode,
                    pack_file=self._current_chip_config.pack_file,
                )
                if self._chip_config_mgr.save_user_preset(config):
                    self._load_presets()
                    InfoBar.success("成功", f"已保存预设: {new_name}", parent=self.window(),
                                   position=InfoBarPosition.TOP_RIGHT)
                else:
                    InfoBar.error("失败", "保存预设失败", parent=self.window(),
                                 position=InfoBarPosition.TOP_RIGHT)
    
    # === Public API ===
    
    @property
    def is_config_applied(self) -> bool:
        """Check if configuration has been applied"""
        return self._config_applied
    
    @property
    def current_config(self) -> Optional[ChipConfig]:
        """Get current applied configuration"""
        return self._current_chip_config
    
    @property
    def pack_info(self) -> Optional[PackInfo]:
        """Get current pack info"""
        return self._pack_info
    
    @property
    def loaded_pack_path(self) -> Optional[str]:
        """Get loaded pack file path"""
        return self._loaded_pack_path
    
    def get_pack_path(self) -> str:
        """Get pack file path from UI"""
        return self.pack_edit.text()
    
    def set_pack_path(self, path: str):
        """Set pack file path in UI"""
        self.pack_edit.setText(path)
        if path and Path(path).exists():
            self._parse_pack_file(path)
    
    def clear_applied_flag(self):
        """Clear the config applied flag"""
        self._config_applied = False
    
    def reload_presets(self):
        """Reload presets from disk"""
        self._load_presets()
