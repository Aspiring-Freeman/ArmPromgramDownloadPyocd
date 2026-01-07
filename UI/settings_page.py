#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings page"""

import os
import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QScrollArea

from qfluentwidgets import (
    CardWidget, PushButton, ToolButton,
    LineEdit, ComboBox, EditableComboBox, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, StrongBodyLabel, SwitchButton, Slider,
    SettingCardGroup, OptionsSettingCard, RangeSettingCard,
    PushSettingCard, SwitchSettingCard, ConfigItem, qconfig,
    PrimaryPushSettingCard, SmoothScrollArea
)

from Core.chip_config import (
    get_project_root, to_relative_path, to_absolute_path,
    DEFAULT_PYOCD_PATH, DEFAULT_PACK_DIRECTORY
)

try:
    from qfluentwidgets import setTheme, Theme, setThemeColor
    HAS_THEME = True
except ImportError:
    HAS_THEME = False

LOG = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """Application settings page"""
    
    theme_changed = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        
        self._init_ui()
        self._load_settings()
        
    def _init_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scroll area
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # Content widget - use transparent background for theme compatibility
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("设置"))
        
        ROW_HEIGHT = 36
        
        # Appearance card
        appear_card = CardWidget()
        appear_layout = QVBoxLayout(appear_card)
        appear_layout.setSpacing(10)
        appear_layout.addWidget(StrongBodyLabel("外观"))
        
        theme_row = QHBoxLayout()
        theme_row.setSpacing(10)
        lbl_theme = BodyLabel("主题:")
        lbl_theme.setFixedHeight(ROW_HEIGHT)
        theme_row.addWidget(lbl_theme)
        self.theme_combo = ComboBox()
        self.theme_combo.addItems(["浅色", "深色", "跟随系统"])
        self.theme_combo.setFixedHeight(ROW_HEIGHT)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        appear_layout.addLayout(theme_row)
        
        layout.addWidget(appear_card)
        
        # Debug card
        debug_card = CardWidget()
        debug_layout = QVBoxLayout(debug_card)
        debug_layout.setSpacing(10)
        debug_layout.addWidget(StrongBodyLabel("调试设置"))
        
        freq_row = QHBoxLayout()
        freq_row.setSpacing(10)
        lbl_freq = BodyLabel("默认SWD频率:")
        lbl_freq.setFixedHeight(ROW_HEIGHT)
        freq_row.addWidget(lbl_freq)
        self.freq_combo = EditableComboBox()
        self.freq_combo.addItems(["100 kHz", "500 kHz", "1 MHz", "2 MHz", "4 MHz", "8 MHz", "10 MHz"])
        self.freq_combo.setPlaceholderText("输入或选择频率")
        self.freq_combo.setFixedHeight(ROW_HEIGHT)
        self.freq_combo.setToolTip(
            "100 kHz: 最稳定，适合连接问题排查\n"
            "500 kHz: 平衡速度和稳定性\n"
            "1 MHz: 标准速度\n"
            "2 MHz: 较快，需要良好连接\n"
            "4 MHz+: 高速，可能不稳定\n"
            "支持自定义频率输入"
        )
        freq_row.addWidget(self.freq_combo)
        freq_row.addStretch()
        debug_layout.addLayout(freq_row)
        
        retry_row = QHBoxLayout()
        retry_row.setSpacing(10)
        lbl_retry = BodyLabel("连接重试次数:")
        lbl_retry.setFixedHeight(ROW_HEIGHT)
        retry_row.addWidget(lbl_retry)
        self.retry_slider = Slider(Qt.Orientation.Horizontal)
        self.retry_slider.setRange(1, 10)
        self.retry_slider.setValue(3)
        self.retry_slider.setFixedWidth(200)
        self.retry_slider.setFixedHeight(ROW_HEIGHT)
        retry_row.addWidget(self.retry_slider)
        self.retry_label = BodyLabel("3")
        self.retry_label.setFixedHeight(ROW_HEIGHT)
        self.retry_slider.valueChanged.connect(lambda v: self.retry_label.setText(str(v)))
        retry_row.addWidget(self.retry_label)
        retry_row.addStretch()
        debug_layout.addLayout(retry_row)
        
        layout.addWidget(debug_card)
        
        # PyOCD card
        pyocd_card = CardWidget()
        pyocd_layout = QVBoxLayout(pyocd_card)
        pyocd_layout.setSpacing(10)
        pyocd_layout.addWidget(StrongBodyLabel("PyOCD 设置"))
        
        pyocd_path_row = QHBoxLayout()
        pyocd_path_row.setSpacing(10)
        lbl_pyocd = BodyLabel("PyOCD 路径:")
        lbl_pyocd.setFixedHeight(ROW_HEIGHT)
        pyocd_path_row.addWidget(lbl_pyocd)
        self.pyocd_path_edit = LineEdit()
        self.pyocd_path_edit.setPlaceholderText(f"默认: {DEFAULT_PYOCD_PATH}")
        self.pyocd_path_edit.setFixedHeight(ROW_HEIGHT)
        self.pyocd_path_edit.setToolTip(
            f"PyOCD 路径 (相对于工程根目录)\n"
            f"默认值: {DEFAULT_PYOCD_PATH}\n\n"
            f"使用相对路径可跨平台使用，无需修改配置"
        )
        pyocd_path_row.addWidget(self.pyocd_path_edit, 1)
        self.pyocd_path_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.pyocd_path_btn.setFixedHeight(ROW_HEIGHT)
        self.pyocd_path_btn.clicked.connect(self._browse_pyocd_path)
        pyocd_path_row.addWidget(self.pyocd_path_btn)
        pyocd_layout.addLayout(pyocd_path_row)
        
        self.pyocd_info_label = CaptionLabel(f"使用默认: {DEFAULT_PYOCD_PATH}")
        pyocd_layout.addWidget(self.pyocd_info_label)
        
        layout.addWidget(pyocd_card)
        
        # Pack card
        pack_card = CardWidget()
        pack_layout = QVBoxLayout(pack_card)
        pack_layout.setSpacing(10)
        pack_layout.addWidget(StrongBodyLabel("CMSIS-Pack 设置"))
        
        pack_dir_row = QHBoxLayout()
        pack_dir_row.setSpacing(10)
        lbl_pack = BodyLabel("Pack 目录:")
        lbl_pack.setFixedHeight(ROW_HEIGHT)
        pack_dir_row.addWidget(lbl_pack)
        self.pack_dir_edit = LineEdit()
        self.pack_dir_edit.setPlaceholderText(f"默认: {DEFAULT_PACK_DIRECTORY}")
        self.pack_dir_edit.setFixedHeight(ROW_HEIGHT)
        self.pack_dir_edit.setToolTip(
            f"CMSIS-Pack 搜索目录 (相对于工程根目录)\n"
            f"默认值: {DEFAULT_PACK_DIRECTORY}\n\n"
            f"会递归搜索该目录下的所有 .pack 文件"
        )
        pack_dir_row.addWidget(self.pack_dir_edit, 1)
        self.pack_dir_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.pack_dir_btn.setFixedHeight(ROW_HEIGHT)
        self.pack_dir_btn.clicked.connect(self._browse_pack_dir)
        pack_dir_row.addWidget(self.pack_dir_btn)
        pack_layout.addLayout(pack_dir_row)
        
        self.pack_info_label = CaptionLabel(f"使用默认: {DEFAULT_PACK_DIRECTORY}")
        pack_layout.addWidget(self.pack_info_label)
        
        layout.addWidget(pack_card)
        
        # Flash card
        flash_card = CardWidget()
        flash_layout = QVBoxLayout(flash_card)
        flash_layout.setSpacing(10)
        flash_layout.addWidget(StrongBodyLabel("烧录设置"))
        
        verify_row = QHBoxLayout()
        verify_row.setSpacing(10)
        lbl_verify = BodyLabel("默认校验烧录:")
        lbl_verify.setFixedHeight(ROW_HEIGHT)
        verify_row.addWidget(lbl_verify)
        self.verify_switch = SwitchButton()
        self.verify_switch.setChecked(True)
        verify_row.addWidget(self.verify_switch)
        verify_row.addStretch()
        flash_layout.addLayout(verify_row)
        
        reset_row = QHBoxLayout()
        reset_row.setSpacing(10)
        lbl_reset = BodyLabel("烧录后自动复位:")
        lbl_reset.setFixedHeight(ROW_HEIGHT)
        reset_row.addWidget(lbl_reset)
        self.reset_switch = SwitchButton()
        self.reset_switch.setChecked(True)
        reset_row.addWidget(self.reset_switch)
        reset_row.addStretch()
        flash_layout.addLayout(reset_row)
        
        layout.addWidget(flash_card)
        
        # About card
        about_card = CardWidget()
        about_layout = QVBoxLayout(about_card)
        about_layout.setSpacing(8)
        about_layout.addWidget(StrongBodyLabel("关于"))
        about_layout.addWidget(BodyLabel("ARM Flash Tool v1.3.0"))
        about_layout.addWidget(CaptionLabel("基于 PyOCD 的 ARM 芯片烧录工具"))
        about_layout.addWidget(CaptionLabel("支持 CMSIS-DAP / ST-Link 调试器"))
        
        link_row = QHBoxLayout()
        link_row.setSpacing(10)
        self.github_btn = PushButton("GitHub", icon=FluentIcon.GITHUB)
        self.github_btn.setFixedHeight(ROW_HEIGHT)
        link_row.addWidget(self.github_btn)
        self.docs_btn = PushButton("文档", icon=FluentIcon.DOCUMENT)
        self.docs_btn.setFixedHeight(ROW_HEIGHT)
        link_row.addWidget(self.docs_btn)
        link_row.addStretch()
        about_layout.addLayout(link_row)
        
        layout.addWidget(about_card)
        
        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.reset_btn = PushButton("恢复默认", icon=FluentIcon.SYNC)
        self.reset_btn.setFixedHeight(ROW_HEIGHT)
        self.reset_btn.clicked.connect(self._reset_settings)
        btn_row.addWidget(self.reset_btn)
        
        self.save_btn = PushButton("保存设置", icon=FluentIcon.SAVE)
        self.save_btn.setFixedHeight(ROW_HEIGHT)
        self.save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(self.save_btn)
        
        layout.addLayout(btn_row)
        layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
    def _browse_pack_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择 CMSIS-Pack 目录")
        if path:
            # Convert to relative path for display and storage
            rel_path = to_relative_path(path)
            self.pack_dir_edit.setText(rel_path)
            self._update_pack_info(rel_path)
    
    def _browse_pyocd_path(self):
        """Browse for custom PyOCD path"""
        path = QFileDialog.getExistingDirectory(self, "选择 PyOCD 目录")
        if path:
            # Convert to relative path for display and storage
            rel_path = to_relative_path(path)
            self.pyocd_path_edit.setText(rel_path)
            self._update_pyocd_info(rel_path)
    
    def _update_pyocd_info(self, path):
        """Update PyOCD info label based on path"""
        if not path:
            self.pyocd_info_label.setText(f"使用默认: {DEFAULT_PYOCD_PATH}")
            return
        
        # Convert to absolute path for checking
        abs_path = to_absolute_path(path)
        
        # Check if it's a valid pyocd path
        if os.path.isdir(abs_path):
            # Check for pyocd module
            pyocd_init = os.path.join(abs_path, "pyocd", "__init__.py")
            pyocd_direct = os.path.join(abs_path, "__init__.py")
            
            if os.path.exists(pyocd_init):
                self.pyocd_info_label.setText(f"✓ 找到 PyOCD 模块")
            elif os.path.exists(pyocd_direct) and "pyocd" in abs_path.lower():
                self.pyocd_info_label.setText(f"✓ 找到 PyOCD 模块")
            else:
                self.pyocd_info_label.setText(f"⚠ 未找到 pyocd 模块，请检查路径")
        else:
            self.pyocd_info_label.setText(f"⚠ 路径不存在")
            
    def _update_pack_info(self, path):
        if not path:
            self.pack_info_label.setText(f"使用默认: {DEFAULT_PACK_DIRECTORY}")
            return
            
        # Convert to absolute path for checking
        abs_path = to_absolute_path(path)
        
        if os.path.isdir(abs_path):
            # Count pack files recursively
            pack_count = sum(1 for _ in self._find_pack_files(abs_path))
            self.pack_info_label.setText(f"✓ 找到 {pack_count} 个 Pack 文件")
        else:
            self.pack_info_label.setText("⚠ 目录不存在")
    
    def _find_pack_files(self, directory):
        """Recursively find all .pack files in directory"""
        for root, dirs, files in os.walk(directory):
            for f in files:
                if f.endswith('.pack'):
                    yield os.path.join(root, f)
            
    def _on_theme_changed(self, index):
        """Apply theme change immediately"""
        if HAS_THEME:
            themes = [Theme.LIGHT, Theme.DARK, Theme.AUTO]
            if index < len(themes):
                setTheme(themes[index])
        theme_names = ["light", "dark", "auto"]
        if index < len(theme_names):
            # Use ui.theme for consistency with main_window
            self._config.set_theme(theme_names[index])
            self.theme_changed.emit(theme_names[index])
            
    def _load_settings(self):
        settings = self._config.data.get("settings", {})
        
        # Load theme from ui.theme (consistent with main_window)
        self.theme_combo.blockSignals(True)
        theme = self._config.get_theme()  # Uses ui.theme
        theme_idx = {"light": 0, "dark": 1, "auto": 2}.get(theme, 0)
        self.theme_combo.setCurrentIndex(theme_idx)
        self.theme_combo.blockSignals(False)
        
        # Apply theme on startup
        if HAS_THEME:
            themes = [Theme.LIGHT, Theme.DARK, Theme.AUTO]
            setTheme(themes[theme_idx])
        
        freq = settings.get("default_frequency", 1000000)
        freq_text_map = {100000: "100 kHz", 500000: "500 kHz", 1000000: "1 MHz", 
                        2000000: "2 MHz", 4000000: "4 MHz", 8000000: "8 MHz", 10000000: "10 MHz"}
        if freq in freq_text_map:
            self.freq_combo.setText(freq_text_map[freq])
        else:
            # Custom frequency - format nicely
            if freq >= 1000000:
                self.freq_combo.setText(f"{freq / 1000000:.1f} MHz")
            else:
                self.freq_combo.setText(f"{freq / 1000} kHz")
        
        self.retry_slider.setValue(settings.get("connect_retries", 3))
        
        # PyOCD path - use default if empty
        pyocd_path = settings.get("pyocd_path", DEFAULT_PYOCD_PATH)
        self.pyocd_path_edit.setText(pyocd_path)
        self._update_pyocd_info(pyocd_path)
        
        # Pack directory - use default if empty
        pack_dir = settings.get("pack_directory", DEFAULT_PACK_DIRECTORY)
        self.pack_dir_edit.setText(pack_dir)
        self._update_pack_info(pack_dir)
        
        self.verify_switch.setChecked(settings.get("default_verify", True))
        self.reset_switch.setChecked(settings.get("default_reset", True))
        
    def _save_settings(self):
        settings = self._config.data.setdefault("settings", {})
        
        # Save theme
        theme_map = {0: "light", 1: "dark", 2: "auto"}
        settings["theme"] = theme_map.get(self.theme_combo.currentIndex(), "light")
        
        # Parse frequency from text (EditableComboBox)
        freq_text = self.freq_combo.text().strip().lower()
        frequency = 1000000  # default 1 MHz
        try:
            if 'mhz' in freq_text:
                freq_val = float(freq_text.replace('mhz', '').strip())
                frequency = int(freq_val * 1000000)
            elif 'khz' in freq_text:
                freq_val = float(freq_text.replace('khz', '').strip())
                frequency = int(freq_val * 1000)
            elif freq_text.isdigit():
                frequency = int(freq_text)
        except (ValueError, AttributeError):
            frequency = 1000000
        settings["default_frequency"] = frequency
        
        settings["connect_retries"] = self.retry_slider.value()
        
        # Save paths as relative paths for portability
        pyocd_path = self.pyocd_path_edit.text().strip()
        settings["pyocd_path"] = to_relative_path(pyocd_path) if pyocd_path else DEFAULT_PYOCD_PATH
        
        pack_dir = self.pack_dir_edit.text().strip()
        settings["pack_directory"] = to_relative_path(pack_dir) if pack_dir else DEFAULT_PACK_DIRECTORY
        
        settings["default_verify"] = self.verify_switch.isChecked()
        settings["default_reset"] = self.reset_switch.isChecked()
        
        self._config.save()
        self.log_message.emit("设置已保存")
        
    def _reset_settings(self):
        """Reset all settings to default values"""
        self.theme_combo.setCurrentIndex(0)  # Light theme
        self.freq_combo.setText("1 MHz")  # 1 MHz default
        self.retry_slider.setValue(3)
        
        # Use default paths
        self.pyocd_path_edit.setText(DEFAULT_PYOCD_PATH)
        self._update_pyocd_info(DEFAULT_PYOCD_PATH)
        
        self.pack_dir_edit.setText(DEFAULT_PACK_DIRECTORY)
        self._update_pack_info(DEFAULT_PACK_DIRECTORY)
        
        self.verify_switch.setChecked(True)
        self.reset_switch.setChecked(True)
        self.log_message.emit("设置已重置为默认值")
