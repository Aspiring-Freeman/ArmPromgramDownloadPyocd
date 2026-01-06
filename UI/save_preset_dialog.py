#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Save Preset Dialog
Enhanced dialog for saving chip configuration presets
"""

import os
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFileDialog, QDialogButtonBox
)

from qfluentwidgets import (
    LineEdit, ComboBox, BodyLabel, StrongBodyLabel,
    PushButton, FluentIcon, CheckBox, TextEdit,
    InfoBar, InfoBarPosition, CardWidget
)

from Core.config import config

LOG = logging.getLogger(__name__)


class SavePresetDialog(QDialog):
    """Enhanced dialog for saving chip presets"""
    
    def __init__(self, parent=None, initial_data: dict = None, export_only: bool = False):
        """
        Args:
            parent: Parent widget
            initial_data: Initial data to populate form fields
            export_only: If True, only show export options (no save to app)
        """
        super().__init__(parent)
        self._initial_data = initial_data or {}
        self._export_only = export_only
        self._project_root = self._get_project_root()
        
        self.setWindowTitle("保存芯片预设")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500 if not export_only else 400)
        
        self._init_ui()
        self._load_defaults()
    
    def _get_project_root(self) -> Path:
        """Get project root directory"""
        # Try to find project root
        current = Path(__file__).parent.parent
        if (current / "main.py").exists():
            return current
        return Path.cwd()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Title
        layout.addWidget(StrongBodyLabel("保存芯片配置预设"))
        
        # Basic info card
        basic_card = CardWidget()
        basic_layout = QGridLayout(basic_card)
        basic_layout.setSpacing(10)
        
        # Preset name
        basic_layout.addWidget(BodyLabel("预设名称:"), 0, 0)
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("例如: STM32H503 开发板")
        basic_layout.addWidget(self.name_edit, 0, 1)
        
        # Vendor
        basic_layout.addWidget(BodyLabel("厂商:"), 1, 0)
        self.vendor_combo = ComboBox()
        self.vendor_combo.addItems([
            "STMicroelectronics", "GigaDevice", "MindMotion", "NXP", "Nordic",
            "Artery", "APM/Geehy", "WCH", "Microchip", "Infineon", "Nuvoton", "其他"
        ])
        basic_layout.addWidget(self.vendor_combo, 1, 1)
        
        # Chip family
        basic_layout.addWidget(BodyLabel("芯片系列:"), 2, 0)
        self.family_edit = LineEdit()
        self.family_edit.setPlaceholderText("例如: STM32H5")
        basic_layout.addWidget(self.family_edit, 2, 1)
        
        # Target
        basic_layout.addWidget(BodyLabel("目标芯片:"), 3, 0)
        self.target_edit = LineEdit()
        self.target_edit.setPlaceholderText("PyOCD 目标名称")
        self.target_edit.setReadOnly(True)  # From current settings
        basic_layout.addWidget(self.target_edit, 3, 1)
        
        layout.addWidget(basic_card)
        
        # Memory config card
        mem_card = CardWidget()
        mem_layout = QGridLayout(mem_card)
        mem_layout.setSpacing(10)
        
        mem_layout.addWidget(StrongBodyLabel("内存配置"), 0, 0, 1, 4)
        
        mem_layout.addWidget(BodyLabel("Flash起始:"), 1, 0)
        self.flash_edit = LineEdit()
        self.flash_edit.setPlaceholderText("0x08000000")
        mem_layout.addWidget(self.flash_edit, 1, 1)
        
        mem_layout.addWidget(BodyLabel("RAM起始:"), 1, 2)
        self.ram_edit = LineEdit()
        self.ram_edit.setPlaceholderText("0x20000000")
        mem_layout.addWidget(self.ram_edit, 1, 3)
        
        layout.addWidget(mem_card)
        
        # Connection config card
        conn_card = CardWidget()
        conn_layout = QGridLayout(conn_card)
        conn_layout.setSpacing(10)
        
        conn_layout.addWidget(StrongBodyLabel("连接配置"), 0, 0, 1, 4)
        
        conn_layout.addWidget(BodyLabel("SWD频率:"), 1, 0)
        self.freq_combo = ComboBox()
        self.freq_combo.addItems(["100 kHz", "500 kHz", "1 MHz", "2 MHz", "4 MHz", "8 MHz", "10 MHz"])
        conn_layout.addWidget(self.freq_combo, 1, 1)
        
        conn_layout.addWidget(BodyLabel("连接模式:"), 1, 2)
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["under-reset", "halt", "pre-reset", "attach"])
        conn_layout.addWidget(self.mode_combo, 1, 3)
        
        conn_layout.addWidget(BodyLabel("Pack文件:"), 2, 0)
        self.pack_edit = LineEdit()
        self.pack_edit.setPlaceholderText("可选 CMSIS-Pack 文件")
        conn_layout.addWidget(self.pack_edit, 2, 1, 1, 2)
        self.pack_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.pack_btn.clicked.connect(self._browse_pack)
        conn_layout.addWidget(self.pack_btn, 2, 3)
        
        layout.addWidget(conn_card)
        
        # Description card
        desc_card = CardWidget()
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.addWidget(StrongBodyLabel("描述与备注"))
        
        desc_row = QHBoxLayout()
        desc_row.addWidget(BodyLabel("描述:"))
        self.desc_edit = LineEdit()
        self.desc_edit.setPlaceholderText("简短描述")
        desc_row.addWidget(self.desc_edit)
        desc_layout.addLayout(desc_row)
        
        notes_row = QHBoxLayout()
        notes_row.addWidget(BodyLabel("备注:"))
        self.notes_edit = LineEdit()
        self.notes_edit.setPlaceholderText("使用注意事项")
        notes_row.addWidget(self.notes_edit)
        desc_layout.addLayout(notes_row)
        
        layout.addWidget(desc_card)
        
        # Save location card
        save_card = CardWidget()
        save_layout = QVBoxLayout(save_card)
        save_layout.addWidget(StrongBodyLabel("保存位置"))
        
        # Save to app config
        self.save_to_app = CheckBox("保存到应用配置 (下次启动自动加载)")
        self.save_to_app.setChecked(True)
        save_layout.addWidget(self.save_to_app)
        
        # Export to file
        export_row = QHBoxLayout()
        self.export_to_file = CheckBox("同时导出到文件:")
        self.export_to_file.setChecked(False)
        self.export_to_file.stateChanged.connect(self._on_export_changed)
        export_row.addWidget(self.export_to_file)
        
        self.export_path_edit = LineEdit()
        self.export_path_edit.setEnabled(False)
        self.export_path_edit.setPlaceholderText("选择保存路径...")
        export_row.addWidget(self.export_path_edit)
        
        self.export_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._browse_export_path)
        export_row.addWidget(self.export_btn)
        save_layout.addLayout(export_row)
        
        # Quick path buttons
        path_row = QHBoxLayout()
        path_row.addWidget(BodyLabel("快速选择:"))
        
        self.doc_btn = PushButton("Doc/ChipConfigs")
        self.doc_btn.clicked.connect(lambda: self._set_export_path("Doc/ChipConfigs"))
        self.doc_btn.setEnabled(False)
        path_row.addWidget(self.doc_btn)
        
        self.package_btn = PushButton("Package")
        self.package_btn.clicked.connect(lambda: self._set_export_path("Package"))
        self.package_btn.setEnabled(False)
        path_row.addWidget(self.package_btn)
        
        path_row.addStretch()
        save_layout.addLayout(path_row)
        
        layout.addWidget(save_card)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        save_text = "导出" if self._export_only else "保存"
        self.save_btn = PushButton(save_text, icon=FluentIcon.SAVE)
        self.save_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_accept(self):
        """Validate and accept dialog"""
        # Validate required fields
        if not self.name_edit.text().strip():
            InfoBar.warning("提示", "请输入预设名称", parent=self,
                          position=InfoBarPosition.TOP)
            return
        
        if not self.target_edit.text().strip():
            InfoBar.warning("提示", "目标芯片不能为空", parent=self,
                          position=InfoBarPosition.TOP)
            return
        
        if self._export_only or self.export_to_file.isChecked():
            export_path = self.export_path_edit.text().strip()
            if not export_path:
                InfoBar.warning("提示", "请选择导出路径", parent=self,
                              position=InfoBarPosition.TOP)
                return
            # Remember the path
            config.set('last_preset_export_path', export_path)
        
        self.accept()
    
    def _load_defaults(self):
        """Load current settings into form"""
        settings = self._initial_data
        
        # Name
        name = settings.get('name', '')
        if name:
            self.name_edit.setText(name)
        
        # Target
        target = settings.get('target', '')
        self.target_edit.setText(target)
        
        # Vendor
        vendor = settings.get('vendor', '')
        if vendor:
            idx = self.vendor_combo.findText(vendor)
            if idx >= 0:
                self.vendor_combo.setCurrentIndex(idx)
        else:
            # Auto-detect vendor from target name
            target_lower = target.lower()
            if target_lower.startswith('stm32'):
                self.vendor_combo.setCurrentText("STMicroelectronics")
            elif target_lower.startswith('gd32'):
                self.vendor_combo.setCurrentText("GigaDevice")
            elif target_lower.startswith('mm32'):
                self.vendor_combo.setCurrentText("MindMotion")
            elif target_lower.startswith('nrf'):
                self.vendor_combo.setCurrentText("Nordic")
            elif target_lower.startswith('lpc') or target_lower.startswith('mimx'):
                self.vendor_combo.setCurrentText("NXP")
            elif target_lower.startswith('at32'):
                self.vendor_combo.setCurrentText("Artery")
        
        # Chip family
        family = settings.get('chip_family', '')
        if family:
            self.family_edit.setText(family)
        elif target and len(target) >= 5:
            self.family_edit.setText(target[:5].upper())
        
        # Frequency
        freq = settings.get('frequency', 1000000)
        freq_map = {100000: 0, 500000: 1, 1000000: 2, 2000000: 3, 4000000: 4, 8000000: 5, 10000000: 6}
        self.freq_combo.setCurrentIndex(freq_map.get(freq, 2))
        
        # Connect mode
        mode = settings.get('connect_mode', 'under-reset')
        idx = self.mode_combo.findText(mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        
        # Pack file
        pack = settings.get('pack_file', settings.get('pack', ''))
        self.pack_edit.setText(pack)
        
        # Flash address - ensure proper formatting
        flash_start = settings.get('flash_start', '0x08000000')
        if isinstance(flash_start, int):
            self.flash_edit.setText(f"0x{flash_start:08X}")
        elif isinstance(flash_start, str):
            # Normalize hex string format
            try:
                if flash_start.lower().startswith('0x'):
                    val = int(flash_start, 16)
                else:
                    val = int(flash_start)
                self.flash_edit.setText(f"0x{val:08X}")
            except ValueError:
                self.flash_edit.setText("0x08000000")
        else:
            self.flash_edit.setText("0x08000000")
        self.ram_edit.setText("0x20000000")
        
        # Description
        desc = settings.get('description', '')
        if desc:
            self.desc_edit.setText(desc)
        
        # Load last export path
        last_path = config.get('last_preset_export_path', '')
        if last_path:
            self.export_path_edit.setText(last_path)
        
        # If export_only, auto-enable export and set default path
        if self._export_only:
            self.export_to_file.setChecked(True)
            self.save_to_app.setVisible(False)
            if not last_path:
                default_dir = self._project_root / "Doc" / "ChipConfigs"
                os.makedirs(default_dir, exist_ok=True)
                name_text = self.name_edit.text() or "preset"
                default_path = default_dir / f"{name_text.replace(' ', '_')}.json"
                self.export_path_edit.setText(str(default_path))
    
    def _on_export_changed(self, state):
        """Enable/disable export path controls"""
        enabled = state == Qt.CheckState.Checked.value
        self.export_path_edit.setEnabled(enabled)
        self.export_btn.setEnabled(enabled)
        self.doc_btn.setEnabled(enabled)
        self.package_btn.setEnabled(enabled)
    
    def _browse_pack(self):
        """Browse for pack file"""
        start_dir = str(self._project_root / "Package")
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 CMSIS-Pack", start_dir, "CMSIS-Pack (*.pack)")
        if path:
            self.pack_edit.setText(path)
    
    def _browse_export_path(self):
        """Browse for export path"""
        # Start from last used or Doc/ChipConfigs
        last_path = self.export_path_edit.text()
        if last_path and os.path.isdir(os.path.dirname(last_path)):
            start_dir = os.path.dirname(last_path)
        else:
            start_dir = str(self._project_root / "Doc" / "ChipConfigs")
        
        # Create directory if not exists
        os.makedirs(start_dir, exist_ok=True)
        
        # Generate default filename
        name = self.name_edit.text() or "preset"
        default_name = f"{name.replace(' ', '_')}.json"
        
        path, _ = QFileDialog.getSaveFileName(
            self, "保存预设文件", os.path.join(start_dir, default_name),
            "JSON Files (*.json)")
        if path:
            self.export_path_edit.setText(path)
            # Remember the directory
            config.set('last_preset_export_path', path)
    
    def _set_export_path(self, relative_path: str):
        """Set export path to a project subdirectory"""
        dir_path = self._project_root / relative_path
        os.makedirs(dir_path, exist_ok=True)
        
        name = self.name_edit.text() or "preset"
        filename = f"{name.replace(' ', '_')}.json"
        full_path = dir_path / filename
        
        self.export_path_edit.setText(str(full_path))
        self.export_to_file.setChecked(True)
    
    def get_preset_data(self) -> dict:
        """Get preset data from form"""
        # Parse addresses
        try:
            flash_text = self.flash_edit.text().strip()
            if flash_text.lower().startswith('0x'):
                flash_start = flash_text  # Keep as hex string for caller to parse
            else:
                flash_start = hex(int(flash_text))
        except ValueError:
            flash_start = '0x08000000'
        
        try:
            ram_text = self.ram_edit.text().strip()
            if ram_text.lower().startswith('0x'):
                ram_start = ram_text
            else:
                ram_start = hex(int(ram_text))
        except ValueError:
            ram_start = '0x20000000'
        
        # Parse frequency
        freq_map = {0: 100000, 1: 500000, 2: 1000000, 3: 2000000, 4: 4000000, 5: 8000000, 6: 10000000}
        
        return {
            'name': self.name_edit.text().strip() or "Unnamed Preset",
            'vendor': self.vendor_combo.currentText(),
            'chip_family': self.family_edit.text().strip(),
            'target': self.target_edit.text().strip(),
            'flash_start': flash_start,
            'ram_start': ram_start,
            'frequency': freq_map.get(self.freq_combo.currentIndex(), 1000000),
            'connect_mode': self.mode_combo.currentText(),
            'pack_file': self.pack_edit.text().strip(),
            'description': self.desc_edit.text().strip(),
            'notes': self.notes_edit.text().strip(),
        }
    
    def should_save_to_app(self) -> bool:
        return self.save_to_app.isChecked()
    
    def should_export_to_file(self) -> bool:
        return self.export_to_file.isChecked()
    
    def get_export_path(self) -> str:
        return self.export_path_edit.text().strip()
