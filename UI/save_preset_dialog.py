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
    QFileDialog, QDialogButtonBox, QFormLayout, QLabel, QWidget
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
        self.setMinimumWidth(750)
        self.setMinimumHeight(650 if not export_only else 550)
        
        self._init_ui()
        self._load_defaults()
        
        # Force layout recalculation for high DPI
        self.adjustSize()
    
    def _get_project_root(self) -> Path:
        """Get project root directory"""
        # Try to find project root
        current = Path(__file__).parent.parent
        if (current / "main.py").exists():
            return current
        return Path.cwd()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        layout.addWidget(StrongBodyLabel("保存芯片配置预设"))
        layout.addSpacing(10)
        
        # Helper function to create a labeled row
        def add_row(label_text, widget):
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = QLabel(label_text)
            lbl.setMinimumWidth(75)
            lbl.setFixedHeight(36)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(lbl)
            widget.setFixedHeight(36)
            row.addWidget(widget, 1)
            layout.addLayout(row)
        
        # Preset name
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("例如: STM32H503 开发板")
        add_row("预设名称:", self.name_edit)
        
        # Vendor
        self.vendor_combo = ComboBox()
        self.vendor_combo.addItems([
            "STMicroelectronics", "GigaDevice", "MindMotion", "NXP", "Nordic",
            "Artery", "APM/Geehy", "WCH", "Microchip", "Infineon", "Nuvoton", "其他"
        ])
        add_row("厂商:", self.vendor_combo)
        
        # Family
        self.family_edit = LineEdit()
        self.family_edit.setPlaceholderText("例如: STM32H5")
        add_row("芯片系列:", self.family_edit)
        
        # Target
        self.target_edit = LineEdit()
        self.target_edit.setPlaceholderText("PyOCD 目标名称")
        self.target_edit.setReadOnly(True)
        add_row("目标芯片:", self.target_edit)
        
        # Memory section
        layout.addSpacing(10)
        layout.addWidget(StrongBodyLabel("内存配置"))
        
        mem_row = QHBoxLayout()
        mem_row.setSpacing(10)
        lbl_flash = QLabel("Flash起始:")
        lbl_flash.setMinimumWidth(75)
        lbl_flash.setFixedHeight(36)
        lbl_flash.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        mem_row.addWidget(lbl_flash)
        self.flash_edit = LineEdit()
        self.flash_edit.setPlaceholderText("0x08000000")
        self.flash_edit.setMaximumWidth(130)
        self.flash_edit.setFixedHeight(36)
        mem_row.addWidget(self.flash_edit)
        lbl_ram = QLabel("RAM起始:")
        lbl_ram.setFixedHeight(36)
        lbl_ram.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        mem_row.addWidget(lbl_ram)
        self.ram_edit = LineEdit()
        self.ram_edit.setPlaceholderText("0x20000000")
        self.ram_edit.setMaximumWidth(130)
        self.ram_edit.setFixedHeight(36)
        mem_row.addWidget(self.ram_edit)
        mem_row.addStretch()
        layout.addLayout(mem_row)
        
        # Connection section
        layout.addSpacing(10)
        layout.addWidget(StrongBodyLabel("连接配置"))
        
        conn_row1 = QHBoxLayout()
        conn_row1.setSpacing(10)
        lbl_freq = QLabel("SWD频率:")
        lbl_freq.setMinimumWidth(75)
        lbl_freq.setFixedHeight(36)
        lbl_freq.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        conn_row1.addWidget(lbl_freq)
        self.freq_combo = ComboBox()
        self.freq_combo.addItems(["100 kHz", "500 kHz", "1 MHz", "2 MHz", "4 MHz", "8 MHz", "10 MHz"])
        self.freq_combo.setMaximumWidth(100)
        self.freq_combo.setFixedHeight(36)
        conn_row1.addWidget(self.freq_combo)
        lbl_mode = QLabel("连接模式:")
        lbl_mode.setFixedHeight(36)
        lbl_mode.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        conn_row1.addWidget(lbl_mode)
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["under-reset", "halt", "pre-reset", "attach"])
        self.mode_combo.setMaximumWidth(120)
        self.mode_combo.setFixedHeight(36)
        conn_row1.addWidget(self.mode_combo)
        conn_row1.addStretch()
        layout.addLayout(conn_row1)
        
        conn_row2 = QHBoxLayout()
        conn_row2.setSpacing(10)
        lbl_pack = QLabel("Pack文件:")
        lbl_pack.setMinimumWidth(75)
        lbl_pack.setFixedHeight(36)
        lbl_pack.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        conn_row2.addWidget(lbl_pack)
        self.pack_edit = LineEdit()
        self.pack_edit.setPlaceholderText("可选 CMSIS-Pack 文件")
        self.pack_edit.setFixedHeight(36)
        conn_row2.addWidget(self.pack_edit, 1)
        self.pack_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.pack_btn.setFixedHeight(36)
        self.pack_btn.clicked.connect(self._browse_pack)
        conn_row2.addWidget(self.pack_btn)
        layout.addLayout(conn_row2)
        
        # Description section
        layout.addSpacing(10)
        layout.addWidget(StrongBodyLabel("描述与备注"))
        
        self.desc_edit = LineEdit()
        self.desc_edit.setPlaceholderText("简短描述")
        add_row("描述:", self.desc_edit)
        
        self.notes_edit = LineEdit()
        self.notes_edit.setPlaceholderText("使用注意事项")
        add_row("备注:", self.notes_edit)
        
        # Save location section
        layout.addSpacing(10)
        layout.addWidget(StrongBodyLabel("保存位置"))
        
        # Save to app config
        self.save_to_app = CheckBox("保存到应用配置 (下次启动自动加载)")
        self.save_to_app.setChecked(True)
        self.save_to_app.setFixedHeight(36)
        layout.addWidget(self.save_to_app)
        
        # Export to file
        export_row = QHBoxLayout()
        export_row.setSpacing(10)
        self.export_to_file = CheckBox("同时导出到文件:")
        self.export_to_file.setChecked(False)
        self.export_to_file.setFixedHeight(36)
        self.export_to_file.stateChanged.connect(self._on_export_changed)
        export_row.addWidget(self.export_to_file)
        
        self.export_path_edit = LineEdit()
        self.export_path_edit.setEnabled(False)
        self.export_path_edit.setPlaceholderText("选择保存路径...")
        self.export_path_edit.setFixedHeight(36)
        export_row.addWidget(self.export_path_edit, 1)
        
        self.export_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.export_btn.setEnabled(False)
        self.export_btn.setFixedHeight(36)
        self.export_btn.clicked.connect(self._browse_export_path)
        export_row.addWidget(self.export_btn)
        layout.addLayout(export_row)
        
        # Quick path buttons
        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        lbl_quick = QLabel("快速选择:")
        lbl_quick.setMinimumWidth(75)
        lbl_quick.setFixedHeight(36)
        lbl_quick.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        path_row.addWidget(lbl_quick)
        
        self.doc_btn = PushButton("Doc/ChipConfigs")
        self.doc_btn.clicked.connect(lambda: self._set_export_path("Doc/ChipConfigs"))
        self.doc_btn.setEnabled(False)
        self.doc_btn.setFixedHeight(36)
        path_row.addWidget(self.doc_btn)
        
        self.package_btn = PushButton("Package")
        self.package_btn.clicked.connect(lambda: self._set_export_path("Package"))
        self.package_btn.setEnabled(False)
        self.package_btn.setFixedHeight(36)
        path_row.addWidget(self.package_btn)
        
        path_row.addStretch()
        layout.addLayout(path_row)
        
        layout.addSpacing(10)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        save_text = "导出" if self._export_only else "保存"
        self.save_btn = PushButton(save_text, icon=FluentIcon.SAVE)
        self.save_btn.setFixedHeight(36)
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
