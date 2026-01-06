#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chip Configuration Management Page
Provides UI for managing chip presets
"""

import logging
from typing import Optional
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
    QTableWidget, QTableWidgetItem, QFileDialog, QAbstractItemView,
    QDialog, QDialogButtonBox
)

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, ToolButton,
    LineEdit, ComboBox, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, StrongBodyLabel, CheckBox, SpinBox,
    InfoBar, InfoBarPosition, SearchLineEdit, TableWidget,
    Dialog, MessageBox
)

from Core.chip_config import ChipConfigManager, ChipConfig, BUILTIN_PRESETS, get_default_flash_start

LOG = logging.getLogger(__name__)


class EditPresetDialog(QDialog):
    """Dialog for editing/creating chip preset"""
    
    def __init__(self, config: Optional[ChipConfig] = None, parent=None):
        super().__init__(parent)
        self._config = config
        self._is_new = config is None
        
        title = "新建芯片预设" if self._is_new else f"编辑预设: {config.name}"
        self.setWindowTitle(title)
        
        self._init_content()
        
        if config:
            self._load_config(config)
    
    def _init_content(self):
        """Initialize dialog content"""
        layout = QVBoxLayout()
        
        # Name
        name_row = QHBoxLayout()
        name_row.addWidget(BodyLabel("名称:"))
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("如: STM32H503 开发板")
        name_row.addWidget(self.name_edit)
        layout.addLayout(name_row)
        
        # Vendor
        vendor_row = QHBoxLayout()
        vendor_row.addWidget(BodyLabel("厂商:"))
        self.vendor_combo = ComboBox()
        self.vendor_combo.addItems([
            "STMicroelectronics", "GigaDevice", "MindMotion", "NXP", "Nordic",
            "Artery", "APM/Geehy", "WCH", "Microchip", "Infineon", "Nuvoton", "Unknown"
        ])
        vendor_row.addWidget(self.vendor_combo)
        
        vendor_row.addWidget(BodyLabel("系列:"))
        self.family_edit = LineEdit()
        self.family_edit.setPlaceholderText("如: STM32H5")
        vendor_row.addWidget(self.family_edit)
        layout.addLayout(vendor_row)
        
        # Target
        target_row = QHBoxLayout()
        target_row.addWidget(BodyLabel("目标芯片:"))
        self.target_edit = LineEdit()
        self.target_edit.setPlaceholderText("PyOCD目标名称, 如: stm32h503cbtx")
        target_row.addWidget(self.target_edit)
        layout.addLayout(target_row)
        
        # Flash address
        flash_row = QHBoxLayout()
        flash_row.addWidget(BodyLabel("Flash起始:"))
        self.flash_edit = LineEdit()
        self.flash_edit.setPlaceholderText("0x08000000")
        self.flash_edit.setMaximumWidth(150)
        flash_row.addWidget(self.flash_edit)
        
        flash_row.addWidget(BodyLabel("RAM起始:"))
        self.ram_edit = LineEdit()
        self.ram_edit.setPlaceholderText("0x20000000")
        self.ram_edit.setMaximumWidth(150)
        flash_row.addWidget(self.ram_edit)
        flash_row.addStretch()
        layout.addLayout(flash_row)
        
        # Connection settings
        conn_row = QHBoxLayout()
        conn_row.addWidget(BodyLabel("频率:"))
        self.freq_combo = ComboBox()
        self.freq_combo.addItems(["100 kHz", "500 kHz", "1 MHz", "2 MHz", "4 MHz"])
        conn_row.addWidget(self.freq_combo)
        
        conn_row.addWidget(BodyLabel("连接模式:"))
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["under-reset", "halt", "pre-reset", "attach"])
        conn_row.addWidget(self.mode_combo)
        conn_row.addStretch()
        layout.addLayout(conn_row)
        
        # Pack file
        pack_row = QHBoxLayout()
        pack_row.addWidget(BodyLabel("Pack文件:"))
        self.pack_edit = LineEdit()
        self.pack_edit.setPlaceholderText("可选 .pack 文件路径")
        pack_row.addWidget(self.pack_edit)
        self.pack_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.pack_btn.clicked.connect(self._browse_pack)
        pack_row.addWidget(self.pack_btn)
        layout.addLayout(pack_row)
        
        # Description
        desc_row = QHBoxLayout()
        desc_row.addWidget(BodyLabel("描述:"))
        self.desc_edit = LineEdit()
        self.desc_edit.setPlaceholderText("简短描述")
        desc_row.addWidget(self.desc_edit)
        layout.addLayout(desc_row)
        
        # Notes
        notes_row = QHBoxLayout()
        notes_row.addWidget(BodyLabel("备注:"))
        self.notes_edit = LineEdit()
        self.notes_edit.setPlaceholderText("使用注意事项")
        notes_row.addWidget(self.notes_edit)
        layout.addLayout(notes_row)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)
        
        self.ok_btn = PushButton("确定", icon=FluentIcon.ACCEPT)
        self.ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.ok_btn)
        
        layout.addLayout(btn_row)
        
        # Set layout
        self.setLayout(layout)
        
        # Default width
        self.setMinimumWidth(600)
    
    def _browse_pack(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Pack", "", "CMSIS-Pack (*.pack)")
        if path:
            self.pack_edit.setText(path)
    
    def _load_config(self, config: ChipConfig):
        """Load config into form"""
        self.name_edit.setText(config.name)
        
        idx = self.vendor_combo.findText(config.vendor)
        if idx >= 0:
            self.vendor_combo.setCurrentIndex(idx)
        
        self.family_edit.setText(config.chip_family)
        self.target_edit.setText(config.target)
        self.flash_edit.setText(f"0x{config.flash_start:08X}")
        self.ram_edit.setText(f"0x{config.ram_start:08X}")
        
        # Frequency
        freq_map = {100000: 0, 500000: 1, 1000000: 2, 2000000: 3, 4000000: 4}
        self.freq_combo.setCurrentIndex(freq_map.get(config.default_frequency, 2))
        
        idx = self.mode_combo.findText(config.connect_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        
        self.pack_edit.setText(config.pack_file)
        self.desc_edit.setText(config.description)
        self.notes_edit.setText(config.notes)
    
    def get_config(self) -> Optional[ChipConfig]:
        """Get config from form"""
        name = self.name_edit.text().strip()
        target = self.target_edit.text().strip()
        
        if not name or not target:
            return None
        
        try:
            flash_text = self.flash_edit.text().strip()
            flash_start = int(flash_text, 16) if flash_text else 0x08000000
            
            ram_text = self.ram_edit.text().strip()
            ram_start = int(ram_text, 16) if ram_text else 0x20000000
        except ValueError:
            return None
        
        freq_map = {0: 100000, 1: 500000, 2: 1000000, 3: 2000000, 4: 4000000}
        
        return ChipConfig(
            name=name,
            vendor=self.vendor_combo.currentText(),
            chip_family=self.family_edit.text().strip() or target[:8],
            target=target,
            flash_start=flash_start,
            ram_start=ram_start,
            default_frequency=freq_map.get(self.freq_combo.currentIndex(), 1000000),
            connect_mode=self.mode_combo.currentText(),
            pack_file=self.pack_edit.text().strip(),
            description=self.desc_edit.text().strip(),
            notes=self.notes_edit.text().strip(),
        )


class ChipConfigPage(QWidget):
    """Chip configuration management page"""
    
    log_message = pyqtSignal(str)
    preset_selected = pyqtSignal(object)  # Emits ChipConfig
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._chip_mgr = ChipConfigManager()
        
        self._init_ui()
        self._load_presets()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("芯片配置管理"))
        
        # Toolbar card
        toolbar_card = CardWidget()
        toolbar_layout = QHBoxLayout(toolbar_card)
        
        # Search
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("搜索预设...")
        self.search_edit.textChanged.connect(self._filter_presets)
        toolbar_layout.addWidget(self.search_edit)
        
        # Vendor filter
        toolbar_layout.addWidget(BodyLabel("厂商:"))
        self.vendor_filter = ComboBox()
        self.vendor_filter.setMinimumWidth(150)
        self.vendor_filter.currentTextChanged.connect(self._filter_presets)
        toolbar_layout.addWidget(self.vendor_filter)
        
        toolbar_layout.addStretch()
        
        # Buttons
        self.new_btn = PushButton("新建", icon=FluentIcon.ADD)
        self.new_btn.clicked.connect(self._new_preset)
        toolbar_layout.addWidget(self.new_btn)
        
        self.edit_btn = PushButton("编辑", icon=FluentIcon.EDIT)
        self.edit_btn.clicked.connect(self._edit_preset)
        self.edit_btn.setEnabled(False)
        toolbar_layout.addWidget(self.edit_btn)
        
        self.delete_btn = PushButton("删除", icon=FluentIcon.DELETE)
        self.delete_btn.clicked.connect(self._delete_preset)
        self.delete_btn.setEnabled(False)
        toolbar_layout.addWidget(self.delete_btn)
        
        layout.addWidget(toolbar_card)
        
        # Table card
        table_card = CardWidget()
        table_layout = QVBoxLayout(table_card)
        table_layout.addWidget(StrongBodyLabel("预设列表"))
        
        self.preset_table = TableWidget()
        self.preset_table.setColumnCount(7)
        self.preset_table.setHorizontalHeaderLabels([
            "名称", "厂商", "系列", "目标芯片", "Flash地址", "频率", "类型"
        ])
        self.preset_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preset_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.preset_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preset_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.preset_table.itemDoubleClicked.connect(self._on_double_click)
        
        # Adjust column widths
        header = self.preset_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        table_layout.addWidget(self.preset_table)
        layout.addWidget(table_card)
        
        # Import/Export card
        io_card = CardWidget()
        io_layout = QHBoxLayout(io_card)
        io_layout.addWidget(StrongBodyLabel("导入/导出"))
        io_layout.addStretch()
        
        self.import_btn = PushButton("导入预设", icon=FluentIcon.DOWNLOAD)
        self.import_btn.clicked.connect(self._import_presets)
        io_layout.addWidget(self.import_btn)
        
        self.export_btn = PushButton("导出选中", icon=FluentIcon.UP)
        self.export_btn.clicked.connect(self._export_preset)
        self.export_btn.setEnabled(False)
        io_layout.addWidget(self.export_btn)
        
        self.export_all_btn = PushButton("导出全部用户预设", icon=FluentIcon.FOLDER)
        self.export_all_btn.clicked.connect(self._export_all)
        io_layout.addWidget(self.export_all_btn)
        
        layout.addWidget(io_card)
        
        # Action buttons
        action_row = QHBoxLayout()
        action_row.addStretch()
        
        self.apply_btn = PrimaryPushButton("应用选中预设", icon=FluentIcon.ACCEPT)
        self.apply_btn.clicked.connect(self._apply_preset)
        self.apply_btn.setEnabled(False)
        action_row.addWidget(self.apply_btn)
        
        layout.addLayout(action_row)
    
    def _load_presets(self):
        """Load all presets into table"""
        # Load vendor filter
        vendors = self._chip_mgr.get_vendors()
        self.vendor_filter.clear()
        self.vendor_filter.addItem("全部")
        self.vendor_filter.addItems(vendors)
        
        self._update_table()
    
    def _update_table(self):
        """Update preset table"""
        vendor = self.vendor_filter.currentText()
        search = self.search_edit.text().lower()
        
        # Get presets
        if vendor == "全部" or not vendor:
            builtin = self._chip_mgr.get_builtin_presets()
            user = self._chip_mgr.get_user_presets()
        else:
            builtin = {k: v for k, v in self._chip_mgr.get_builtin_presets().items()
                      if v.vendor == vendor}
            user = {k: v for k, v in self._chip_mgr.get_user_presets().items()
                   if v.vendor == vendor}
        
        # Filter by search
        if search:
            builtin = {k: v for k, v in builtin.items()
                      if search in v.name.lower() or search in v.target.lower()}
            user = {k: v for k, v in user.items()
                   if search in v.name.lower() or search in v.target.lower()}
        
        # Clear table
        self.preset_table.setRowCount(0)
        
        # Add builtin presets
        for key, cfg in sorted(builtin.items(), key=lambda x: x[1].name):
            self._add_table_row(key, cfg, is_builtin=True)
        
        # Add user presets
        for key, cfg in sorted(user.items(), key=lambda x: x[1].name):
            self._add_table_row(key, cfg, is_builtin=False)
    
    def _add_table_row(self, key: str, cfg: ChipConfig, is_builtin: bool):
        """Add a row to preset table"""
        row = self.preset_table.rowCount()
        self.preset_table.insertRow(row)
        
        self.preset_table.setItem(row, 0, QTableWidgetItem(cfg.name))
        self.preset_table.setItem(row, 1, QTableWidgetItem(cfg.vendor))
        self.preset_table.setItem(row, 2, QTableWidgetItem(cfg.chip_family))
        self.preset_table.setItem(row, 3, QTableWidgetItem(cfg.target))
        self.preset_table.setItem(row, 4, QTableWidgetItem(f"0x{cfg.flash_start:08X}"))
        self.preset_table.setItem(row, 5, QTableWidgetItem(f"{cfg.default_frequency // 1000} kHz"))
        self.preset_table.setItem(row, 6, QTableWidgetItem("内置" if is_builtin else "用户"))
        
        # Store key in first column
        self.preset_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, key)
        self.preset_table.item(row, 0).setData(Qt.ItemDataRole.UserRole + 1, is_builtin)
    
    def _filter_presets(self):
        """Filter presets based on search and vendor"""
        self._update_table()
    
    def _on_selection_changed(self):
        """Handle table selection change"""
        selected = self.preset_table.selectedItems()
        has_selection = len(selected) > 0
        
        self.apply_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)
        
        # Check if user preset for edit/delete
        if has_selection:
            row = self.preset_table.currentRow()
            is_builtin = self.preset_table.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)
            self.edit_btn.setEnabled(not is_builtin)
            self.delete_btn.setEnabled(not is_builtin)
        else:
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
    
    def _on_double_click(self, item):
        """Handle double click - apply preset"""
        self._apply_preset()
    
    def _get_selected_key(self) -> Optional[str]:
        """Get key of selected preset"""
        row = self.preset_table.currentRow()
        if row < 0:
            return None
        return self.preset_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
    
    def _new_preset(self):
        """Create new preset"""
        dialog = EditPresetDialog(None, self)
        if dialog.exec():
            config = dialog.get_config()
            if config:
                key = f"user_{config.target}".lower().replace(" ", "_")
                self._chip_mgr.add_user_preset(key, config)
                self._update_table()
                self.log_message.emit(f"已创建预设: {config.name}")
                InfoBar.success("成功", f"已创建预设: {config.name}",
                              parent=self.window(), position=InfoBarPosition.TOP_RIGHT)
    
    def _edit_preset(self):
        """Edit selected preset"""
        key = self._get_selected_key()
        if not key:
            return
        
        config = self._chip_mgr.get_preset(key)
        if not config:
            return
        
        dialog = EditPresetDialog(config, self)
        if dialog.exec():
            new_config = dialog.get_config()
            if new_config:
                self._chip_mgr.add_user_preset(key, new_config)
                self._update_table()
                self.log_message.emit(f"已更新预设: {new_config.name}")
    
    def _delete_preset(self):
        """Delete selected user preset"""
        key = self._get_selected_key()
        if not key:
            return
        
        config = self._chip_mgr.get_preset(key)
        if not config:
            return
        
        # Confirm
        box = MessageBox("确认删除", f"确定要删除预设 \"{config.name}\" 吗？", self)
        if box.exec():
            if self._chip_mgr.delete_user_preset(key):
                self._update_table()
                self.log_message.emit(f"已删除预设: {config.name}")
    
    def _apply_preset(self):
        """Apply selected preset"""
        key = self._get_selected_key()
        if not key:
            return
        
        config = self._chip_mgr.get_preset(key)
        if config:
            self.preset_selected.emit(config)
            self.log_message.emit(f"已选择预设: {config.name}")
            InfoBar.success("成功", f"已选择预设: {config.name}",
                          parent=self.window(), position=InfoBarPosition.TOP_RIGHT)
    
    def _import_presets(self):
        """Import presets from JSON file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入芯片预设", "", "JSON Files (*.json)")
        if not path:
            return
        
        count = self._chip_mgr.import_all_presets(Path(path))
        if count > 0:
            self._update_table()
            self.log_message.emit(f"已导入 {count} 个预设")
            InfoBar.success("成功", f"已导入 {count} 个预设",
                          parent=self.window(), position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.warning("提示", "未导入任何预设",
                          parent=self.window(), position=InfoBarPosition.TOP_RIGHT)
    
    def _export_preset(self):
        """Export selected preset to JSON"""
        key = self._get_selected_key()
        if not key:
            return
        
        config = self._chip_mgr.get_preset(key)
        if not config:
            return
        
        default_name = f"{config.name.replace(' ', '_')}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出预设", default_name, "JSON Files (*.json)")
        if not path:
            return
        
        if self._chip_mgr.export_preset(key, Path(path)):
            self.log_message.emit(f"已导出: {path}")
            InfoBar.success("成功", f"已导出预设", 
                          parent=self.window(), position=InfoBarPosition.TOP_RIGHT)
    
    def _export_all(self):
        """Export all user presets"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出所有用户预设", "user_chip_configs.json", "JSON Files (*.json)")
        if not path:
            return
        
        if self._chip_mgr.export_all_user_presets(Path(path)):
            self.log_message.emit(f"已导出所有用户预设: {path}")
            InfoBar.success("成功", "已导出所有用户预设",
                          parent=self.window(), position=InfoBarPosition.TOP_RIGHT)
