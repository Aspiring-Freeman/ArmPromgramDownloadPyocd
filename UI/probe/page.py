#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probe Page - Main UI Component
Probe management and connection page
"""

import logging
from typing import Optional, List, Dict

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
from Core.pack_parser import PackParser, PackInfo

from UI.probe.scanner import ProbeScanner
from UI.probe.worker import ConnectWorker
from UI.probe.preset_manager import PresetManagerMixin
from UI.tooltip_helper import install_tooltip

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
        self._pack_info: Optional[PackInfo] = None  # Cached pack info
        self._loaded_pack_path: Optional[str] = None  # Track which pack file is loaded
        self._preset_name_to_key: Dict[str, str] = {}  # Map preset name to key
        self._pack_device_label_to_name: Dict[str, str] = {}  # Map pack device label to name
        self._config_applied = False  # 配置是否已应用的标志
        
        self._init_ui()
        self._install_tooltips()  # Install instant tooltips
        self._load_targets()
        self._load_presets()
        
        # 执行一次初始探针扫描
        self._scan_probes()
        
        # 启动自动扫描（如果启用）
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
        
        # Chip Configuration Card (combines preset and manual config)
        preset_card = self._create_preset_card()
        layout.addWidget(preset_card)
        
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
        
        # 芯片检测按钮
        self.detect_chip_btn = PushButton("检测芯片", icon=FluentIcon.SEARCH)
        self.detect_chip_btn.setToolTip("连接芯片并读取CPU信息，帮助识别芯片型号")
        self.detect_chip_btn.clicked.connect(self._detect_chip)
        header.addWidget(self.detect_chip_btn)
        
        header.addStretch()
        probe_layout.addLayout(header)
        
        self.probe_list = ListWidget()
        self.probe_list.setMaximumHeight(120)
        self.probe_list.hide()  # 初始隐藏，扫描后显示
        probe_layout.addWidget(self.probe_list)
        
        self.no_probe_label = CaptionLabel("未检测到探针，点击刷新按钮扫描")
        probe_layout.addWidget(self.no_probe_label)
        
        return probe_card
    
    def _create_preset_card(self) -> CardWidget:
        """Create the chip configuration card with clear mode selection"""
        preset_card = CardWidget()
        preset_layout = QVBoxLayout(preset_card)
        
        # Header
        preset_header = QHBoxLayout()
        preset_header.addWidget(StrongBodyLabel("芯片配置"))
        preset_header.addStretch()
        preset_layout.addLayout(preset_header)
        
        # === 配置来源选择（三种模式）===
        from qfluentwidgets import RadioButton
        
        source_label = CaptionLabel("选择配置来源:")
        preset_layout.addWidget(source_label)
        
        # 模式1: 从文件导入（用户自定义配置）
        self.source_file_radio = RadioButton("从文件导入 (自定义配置，包含完整的Flash地址等信息)")
        self.source_file_radio.toggled.connect(self._on_source_changed)
        preset_layout.addWidget(self.source_file_radio)
        
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
        preset_layout.addWidget(self.file_widget)
        
        # 模式2: 从预设选择
        self.source_preset_radio = RadioButton("从预设选择 (内置预设或之前保存的用户预设)")
        self.source_preset_radio.setChecked(True)
        self.source_preset_radio.toggled.connect(self._on_source_changed)
        preset_layout.addWidget(self.source_preset_radio)
        
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
        preset_layout.addWidget(self.preset_widget)
        
        # 模式3: 从 Pack 导入
        self.source_pack_radio = RadioButton("从 Pack 导入 (读取芯片信息，Flash地址为芯片默认值)")
        self.source_pack_radio.toggled.connect(self._on_source_changed)
        preset_layout.addWidget(self.source_pack_radio)
        
        self.pack_widget = QWidget()
        pack_inner = QVBoxLayout(self.pack_widget)
        pack_inner.setContentsMargins(20, 5, 0, 5)
        
        pack_row1 = QHBoxLayout()
        pack_row1.addWidget(BodyLabel("Pack文件:"))
        self.pack_edit = LineEdit()
        self.pack_edit.setPlaceholderText("选择 CMSIS-Pack 文件 (.pack)")
        self.pack_edit.setReadOnly(True)  # 只读，防止手动编辑
        pack_row1.addWidget(self.pack_edit, 1)  # stretch=1, 让它占用剩余空间
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
        preset_layout.addWidget(self.pack_widget)
        
        # === 当前配置信息显示 ===
        self.preset_info = CaptionLabel("💡 从预设选择芯片配置")
        preset_layout.addWidget(self.preset_info)
        
        # === 导出/保存按钮 ===
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
        
        preset_layout.addLayout(btn_row)
        
        return preset_card
    
    def _load_presets(self):
        """Load vendors and presets into combo boxes"""
        # Get all presets
        presets = self._chip_config_mgr.get_all_presets()
        
        # Collect vendors (use set to avoid duplicates)
        vendors = set()
        for key, config in presets.items():
            if config.vendor:
                vendors.add(config.vendor)
        
        # Update vendor combo
        self.vendor_combo.blockSignals(True)
        self.vendor_combo.clear()
        self.vendor_combo.addItem("全部")  # "All" option
        for vendor in sorted(vendors):
            self.vendor_combo.addItem(vendor)
        self.vendor_combo.blockSignals(False)
        
        # Load presets for current vendor
        self._update_preset_combo()
    
    def _on_vendor_changed(self, vendor: str):
        """Handle vendor selection change"""
        # 厂商变化时，总是清除应用标志
        self._config_applied = False
        
        # 如果之前已连接，自动断开
        if self._connected:
            self._disconnect()
            self.log_message.emit("⚠️ 厂商已更改，已自动断开连接")
        
        self._update_preset_combo()
    
    def _on_target_changed(self, text: str):
        """Handle target chip selection change"""
        if not text:
            return
        # 目标芯片变化时，如果已连接则断开
        if self._connected:
            self._disconnect()
            self.log_message.emit("⚠️ 目标芯片已更改，已自动断开连接")
    
    def _on_freq_changed(self, text: str):
        """Handle frequency selection change"""
        if not text:
            return
        # 频率变化时，如果已连接则断开
        if self._connected:
            self._disconnect()
            self.log_message.emit("⚠️ SWD频率已更改，已自动断开连接")
    
    def _on_mode_changed(self, text: str):
        """Handle connection mode change"""
        if not text:
            return
        # 连接模式变化时，如果已连接则断开
        if self._connected:
            self._disconnect()
            self.log_message.emit("⚠️ 连接模式已更改，已自动断开连接")
    
    def _on_pack_device_changed(self, text: str):
        """Handle pack device selection change"""
        LOG.debug(f"Pack device changed: '{text}', currentIndex={self.pack_device_combo.currentIndex()}")
        
        if not text:
            return
        
        # Pack设备变化时，总是清除应用标志
        self._config_applied = False
        self.log_message.emit("⚠️ Pack芯片已更改，需要重新应用配置")
        
        # 如果之前已连接，自动断开
        if self._connected:
            self._disconnect()
            self.log_message.emit("⚠️ 已自动断开连接")
        
        # 更新状态提示
        self.preset_info.setText("👁 预览中 - 请点击「应用」按钮确认配置")
    
    def _update_preset_combo(self):
        """Update preset combo based on selected vendor"""
        vendor = self.vendor_combo.currentText()
        presets = self._chip_config_mgr.get_all_presets()
        
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self._preset_name_to_key.clear()  # Clear mapping
        
        for key, config in presets.items():
            # Filter by vendor if not "全部" (All)
            if vendor == "全部" or config.vendor == vendor:
                self.preset_combo.addItem(config.name)
                self._preset_name_to_key[config.name] = key  # Store mapping
        
        self.preset_combo.blockSignals(False)
        
        # Trigger preset info update
        if self.preset_combo.count() > 0:
            self._on_preset_changed(self.preset_combo.currentText())
        else:
            self.preset_info.setText("📋 没有找到匹配的预设")
    
    def _on_preset_changed(self, text: str):
        """Handle preset selection change"""
        LOG.debug(f"Preset changed: '{text}', connected={self._connected}")
        
        # 只要预设选择发生变化，就应该：
        # 1. 清除已应用标志（需要重新应用）
        # 2. 如果已连接，断开连接
        
        # 先处理断开连接和清除标志的逻辑（在检查预设有效性之前）
        if self._connected:
            self._disconnect()
            self.log_message.emit("⚠️ 预设已更改，已自动断开连接")
        
        # 清除已应用标志
        self._config_applied = False
        
        # 然后处理预设预览信息
        name = self.preset_combo.currentText()
        if name:
            key = self._preset_name_to_key.get(name)
            if key:
                config = self._chip_config_mgr.get_preset(key)
                if config:
                    info = f"目标: {config.target} | Flash: 0x{config.flash_start:08X}"
                    if config.pack_file:
                        info += f" | Pack: {config.pack_file.split('/')[-1]}"
                    # 明确显示这是预览，需要点击应用
                    self.preset_info.setText(f"👁 预览: {info} (点击'应用'生效)")
                    return
        
        # 如果没有有效的预设，显示提示
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
            self._current_chip_config = config
            self._apply_config_to_ui(config)
            self.config_applied.emit(config)
            # 设置已应用标志
            self._config_applied = True
            # 更新状态显示为"已应用"
            info = f"目标: {config.target} | Flash: 0x{config.flash_start:08X}"
            self.preset_info.setText(f"✅ 已应用: {config.name} | {info}")
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
        
        config = self._chip_config_mgr.get_preset(key)
        preset_name = config.name if config else name
        
        # Confirm deletion
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
        # 切换配置源时，总是清除应用标志
        self._config_applied = False
        
        # 如果之前已连接，自动断开
        if self._connected:
            self._disconnect()
            self.log_message.emit("⚠️ 配置源已更改，已自动断开连接")
        
        # Hide all
        self.file_widget.hide()
        self.preset_widget.hide()
        self.pack_widget.hide()
        
        # Show selected
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
            
            # 如果文件路径发生变化，清除应用标志并断开连接
            if old_path != path:
                LOG.debug(f"Config file changed: '{old_path}' -> '{path}'")
                self._config_applied = False
                self.preset_info.setText(f"👁 预览: {path.split('/')[-1]} (点击'应用'生效)")
                
                if self._connected:
                    self._disconnect()
                    self.log_message.emit("⚠️ 配置文件已更改，已自动断开连接")
    
    def _apply_file_config(self):
        """Apply configuration from file"""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            InfoBar.warning("提示", "请先选择配置文件", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        # Use existing import logic
        result = self._chip_config_mgr.import_preset(file_path)
        if result:
            self._load_presets()
            config = self._chip_config_mgr.get_preset(result)
            if config:
                self._current_chip_config = config
                self._apply_config_to_ui(config)
                self.config_applied.emit(config)
                # 设置已应用标志
                self._config_applied = True
                info = f"目标: {config.target} | Flash: 0x{config.flash_start:08X}"
                self.preset_info.setText(f"✅ 已应用: {config.name} | {info}")
                InfoBar.success("成功", f"已应用配置: {config.name}", parent=self.window(),
                               position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.error("失败", "导入配置失败", parent=self.window(),
                         position=InfoBarPosition.TOP_RIGHT)
    
    def _apply_pack_config(self):
        """Apply configuration from Pack device selection"""
        if not self._pack_info:
            return
        
        label = self.pack_device_combo.currentText()
        if not label:
            InfoBar.warning("提示", "请先选择芯片", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        # 使用字典获取设备名
        dev_name = self._pack_device_label_to_name.get(label)
        if not dev_name:
            # 备用方案：从标签解析
            dev_name = label.split(" (")[0]
        
        device = self._pack_info.get_device(dev_name)
        if not device:
            InfoBar.warning("提示", f"未找到芯片: {dev_name}", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        # Create config from Pack device
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
        self._apply_config_to_ui(config, skip_pack_parse=True)  # 不重新解析Pack，保持当前选择
        self.config_applied.emit(config)
        
        # 设置已应用标志
        self._config_applied = True
        
        flash_kb = device.flash_size // 1024 if device.flash_size else 0
        self.preset_info.setText(
            f"✅ 已应用: {device.name} | Flash: 0x{device.flash_start:08X} ({flash_kb}KB) | "
            f"⚠ 如需调整Flash地址，请到烧录页面修改"
        )
        InfoBar.success("成功", f"已应用: {device.name}", parent=self.window(),
                       position=InfoBarPosition.TOP_RIGHT)
    
    def _apply_config_to_ui(self, config: ChipConfig, skip_pack_parse: bool = False):
        """Apply config to UI elements (target, freq, mode, pack)
        
        Args:
            config: The chip configuration to apply
            skip_pack_parse: If True, skip re-parsing pack file (used when applying from pack selection)
        """
        self.log_message.emit(f"[DEBUG] 应用配置: target={config.target}, pack={config.pack_file}, skip_pack_parse={skip_pack_parse}")
        
        # 只有在需要时才解析 Pack 文件：
        # 1. 配置包含 pack_file
        # 2. 不是从 Pack 导入模式应用的 (skip_pack_parse=False)
        # 3. Pack 文件存在
        if config.pack_file and not skip_pack_parse:
            from pathlib import Path
            pack_path = Path(config.pack_file)
            self.log_message.emit(f"[DEBUG] Pack路径: {pack_path}, 存在: {pack_path.exists()}")
            if pack_path.exists():
                # 只更新 pack_edit 显示，不改变 pack_device_combo 的选择
                self.pack_edit.setText(config.pack_file)
                
                # 只有当 pack 信息未加载或路径不同时才重新解析
                current_pack = getattr(self, '_loaded_pack_path', None)
                if current_pack != config.pack_file:
                    self._parse_pack_file(str(pack_path))
                    self._loaded_pack_path = config.pack_file
                    
                # Add pack targets to target list if not present
                if self._pack_info and self._pack_info.devices:
                    for dev in self._pack_info.devices:
                        dev_name = dev.name.lower()
                        if dev_name not in self._all_targets:
                            self._all_targets.append(dev_name)
                            self.log_message.emit(f"[DEBUG] 添加Pack目标: {dev_name}")
                    self._update_target_combo(self._all_targets)
        
        # Find and set target - try exact match first
        self.log_message.emit(f"[DEBUG] 目标列表数量: {self.target_combo.count()}")
        target_idx = self.target_combo.findText(config.target)
        self.log_message.emit(f"[DEBUG] 精确匹配: target={config.target}, idx={target_idx}")
        target_found = False
        if target_idx >= 0:
            self.target_combo.setCurrentIndex(target_idx)
            self.log_message.emit(f"[DEBUG] 已选中目标 (精确): {config.target}")
            target_found = True
        else:
            # Try case-insensitive search in all targets
            target_lower = config.target.lower()
            for i in range(self.target_combo.count()):
                item_text = self.target_combo.itemText(i)
                if item_text.lower() == target_lower:
                    self.target_combo.setCurrentIndex(i)
                    target_found = True
                    self.log_message.emit(f"[DEBUG] 已选中目标 (不区分大小写): {item_text}")
                    break
            
            if not target_found:
                self.log_message.emit(f"[DEBUG] 未找到目标 {config.target}，尝试过滤")
                # Filter and select first match
                self.target_search.setText(config.target)
                # After filtering, select the first item if available
                if self.target_combo.count() > 0:
                    self.target_combo.setCurrentIndex(0)
                    self.log_message.emit(f"[DEBUG] 过滤后选中第一个: {self.target_combo.currentText()}")
                    target_found = True
                else:
                    self.log_message.emit(f"⚠️ 目标芯片 '{config.target}' 未在列表中找到，请手动选择或加载对应的 Pack 文件")
                    # Show warning to user
                    InfoBar.warning(
                        "目标未找到", 
                        f"芯片 '{config.target}' 不在当前目标列表中，请确保已加载对应的 Pack 文件",
                        parent=self.window(),
                        duration=5000,
                        position=InfoBarPosition.TOP_RIGHT
                    )
        
        # Set frequency
        freq = config.default_frequency
        if freq >= 1000000:
            self.freq_combo.setText(f"{freq // 1000000} MHz")
        else:
            self.freq_combo.setText(f"{freq // 1000} kHz")
        
        # Set connect mode
        mode_map = {"under-reset": 0, "halt": 1, "pre-reset": 2, "attach": 3}
        mode_idx = mode_map.get(config.connect_mode.lower(), 0)
        self.mode_combo.setCurrentIndex(mode_idx)
    
    def _create_options_card(self) -> CardWidget:
        """Create the connection options card"""
        opt_card = CardWidget()
        opt_layout = QVBoxLayout(opt_card)
        opt_layout.addWidget(StrongBodyLabel("连接选项"))
        
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
        opt_layout.addLayout(target_row)
        
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
        self.reset_help_btn = ToolButton(FluentIcon.QUESTION)
        self.reset_help_btn.setToolTip("点击查看复位类型说明")
        self.reset_help_btn.clicked.connect(self._show_reset_help)
        reset_header.addWidget(self.reset_help_btn)
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
    
    def _install_tooltips(self):
        """Install instant tooltip filters on widgets with tooltips"""
        tooltip_widgets = [
            self.detect_chip_btn,
            self.delete_preset_btn,
            self.export_preset_btn,
            self.save_preset_btn,
            self.reset_combo,
            self.halt_check,
        ]
        
        # Also check if reset_help_btn exists
        if hasattr(self, 'reset_help_btn'):
            tooltip_widgets.append(self.reset_help_btn)
        
        for widget in tooltip_widgets:
            if widget is not None:
                install_tooltip(widget)
        
    def _start_scanning(self):
        """Start background probe scanning"""
        # Check if auto-scanning is enabled in config
        auto_scan = self._config.get('settings.auto_scan_probes', True)
        if not auto_scan:
            LOG.info("自动探针扫描已禁用")
            return
        # 从配置获取扫描间隔，默认10秒
        scan_interval = self._config.get('settings.probe_scan_interval', 10)
        self._scanner = ProbeScanner(self._wrapper, scan_interval)
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
    
    def _detect_chip(self):
        """Open chip detection dialog"""
        from UI.chip_detect_dialog import ChipDetectDialog
        
        # Get current settings
        probe_id = None
        if self.probe_list.currentItem():
            text = self.probe_list.currentItem().text()
            if "[" in text and "]" in text:
                probe_id = text.split("[")[1].split("]")[0].replace("...", "")
        
        # Get pack path from various sources
        pack_path = self.pack_edit.text().strip()
        if not pack_path and self._current_chip_config and self._current_chip_config.pack_file:
            from Core.chip_config import normalize_pack_path
            pack_path = normalize_pack_path(self._current_chip_config.pack_file)
        
        # Get target hint
        target_hint = self.target_combo.currentText() or ""
        
        # Get frequency
        freq_text = self.freq_combo.text().strip().lower()
        frequency = 1000000
        try:
            if 'mhz' in freq_text:
                frequency = int(float(freq_text.replace('mhz', '').strip()) * 1000000)
            elif 'khz' in freq_text:
                frequency = int(float(freq_text.replace('khz', '').strip()) * 1000)
        except:
            pass
        
        # Open dialog
        dialog = ChipDetectDialog(
            self._wrapper,
            parent=self.window(),
            initial_pack=pack_path,
            initial_target=target_hint,
            initial_frequency=frequency,
            probe_id=probe_id
        )
        dialog.exec()
        
        # Log result
        result = dialog.get_result()
        if result and result.success:
            self.log_message.emit(f"芯片检测完成: {result.core_type}")
            if result.matched_targets:
                for t in result.matched_targets:
                    self.log_message.emit(f"  {t}")
        
    def _update_probe_list(self, probes):
        """Update the probe list UI"""
        self.probe_list.clear()
        if probes:
            self.no_probe_label.hide()
            self.probe_list.show()
            for p in probes:
                # 显示格式：产品名 - 厂商 [ID前12位]
                # 让用户更容易根据名字识别探针
                display_name = f"{p.product_name}"
                if p.vendor_name and p.vendor_name != "Unknown":
                    display_name = f"{p.vendor_name} {p.product_name}"
                self.probe_list.addItem(f"{display_name} [{p.unique_id[:12]}...]")
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
            # Parse the pack file to enable device selection
            from pathlib import Path
            if Path(last_pack).exists():
                self._parse_pack_file(last_pack)
            
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
            self._parse_pack_file(path)
    
    def _parse_pack_file(self, pack_path: str):
        """Parse pack file and populate device combo"""
        try:
            parser = PackParser(pack_path)
            self._pack_info = parser.parse()
            
            if self._pack_info and self._pack_info.devices:
                # Store pack devices
                self._pack_devices = {dev.name.lower(): dev for dev in self._pack_info.devices}
                
                # Populate pack device combo
                self.pack_device_combo.blockSignals(True)  # 阻止信号防止触发变化
                self.pack_device_combo.clear()
                self._pack_device_label_to_name.clear()  # 清除映射
                for dev in self._pack_info.devices:
                    flash_kb = dev.flash_size // 1024 if dev.flash_size else 0
                    label = f"{dev.name} (Flash: 0x{dev.flash_start:08X}, {flash_kb}KB)"
                    self.pack_device_combo.addItem(label)
                    self._pack_device_label_to_name[label] = dev.name  # 存储映射
                self.pack_device_combo.blockSignals(False)
                
                self.pack_device_combo.setEnabled(True)
                self.pack_apply_btn.setEnabled(True)
                
                # Also add to target combo for connection
                pack_targets = [dev.name.lower() for dev in self._pack_info.devices]
                current = self.target_combo.currentText()
                self.target_combo.clear()
                
                if pack_targets:
                    self.target_combo.addItem(f"── {self._pack_info.name} ──")
                    for t in pack_targets:
                        self.target_combo.addItem(t)
                    self.target_combo.addItem("── 内置目标 ──")
                
                self.target_combo.addItems(self._all_targets)
                
                # Restore selection
                idx = self.target_combo.findText(current)
                if idx >= 0:
                    self.target_combo.setCurrentIndex(idx)
                
                self.pack_info_label.setText(
                    f"✓ {self._pack_info.vendor}.{self._pack_info.name} v{self._pack_info.version} - "
                    f"包含 {len(self._pack_info.devices)} 个芯片"
                )
                # 记录已加载的 Pack 路径
                self._loaded_pack_path = pack_path
            else:
                self._pack_devices = {}
                self._loaded_pack_path = None
                self.pack_device_combo.clear()
                self.pack_device_combo.setEnabled(False)
                self.pack_apply_btn.setEnabled(False)
                self.pack_info_label.setText("⚠ 无法解析Pack文件或没有设备信息")
                
        except Exception as e:
            LOG.exception(f"Error parsing pack file: {e}")
            self._pack_devices = {}
            self._loaded_pack_path = None
            self.pack_device_combo.clear()
            self.pack_device_combo.setEnabled(False)
            self.pack_apply_btn.setEnabled(False)
            self.pack_info_label.setText(f"⚠ 解析失败: {str(e)}")
            
    def _toggle_connection(self):
        """Toggle connection state"""
        if self._connected:
            self._disconnect()
        else:
            self._connect()
            
    def _connect(self):
        """Start connection process"""
        # 检查是否已应用配置
        LOG.debug(f"_connect called: _config_applied={self._config_applied}")
        
        if not self._config_applied:
            self.log_message.emit("⚠️ 请先应用芯片配置")
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
            self.log_message.emit("⚠️ 请选择目标芯片")
            InfoBar.warning(
                "未选择目标", 
                "请先选择或应用芯片配置，然后选择目标芯片",
                parent=self.window(),
                duration=4000,
                position=InfoBarPosition.TOP_RIGHT
            )
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
