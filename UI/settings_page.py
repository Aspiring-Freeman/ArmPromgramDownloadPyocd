#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings page"""

import os
import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog

from qfluentwidgets import (
    CardWidget, PushButton, ToolButton,
    LineEdit, ComboBox, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, StrongBodyLabel, SwitchButton, Slider,
    SettingCardGroup, OptionsSettingCard, RangeSettingCard,
    PushSettingCard, SwitchSettingCard, ConfigItem, qconfig,
    PrimaryPushSettingCard
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("设置"))
        
        # Appearance card
        appear_card = CardWidget()
        appear_layout = QVBoxLayout(appear_card)
        appear_layout.addWidget(StrongBodyLabel("外观"))
        
        theme_row = QHBoxLayout()
        theme_row.addWidget(BodyLabel("主题:"))
        self.theme_combo = ComboBox()
        self.theme_combo.addItems(["浅色", "深色", "跟随系统"])
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        appear_layout.addLayout(theme_row)
        
        layout.addWidget(appear_card)
        
        # Debug card
        debug_card = CardWidget()
        debug_layout = QVBoxLayout(debug_card)
        debug_layout.addWidget(StrongBodyLabel("调试设置"))
        
        freq_row = QHBoxLayout()
        freq_row.addWidget(BodyLabel("默认SWD频率:"))
        self.freq_combo = ComboBox()
        self.freq_combo.addItems(["100 kHz", "500 kHz", "1 MHz", "2 MHz", "4 MHz"])
        self.freq_combo.setToolTip(
            "100 kHz: 最稳定，适合连接问题排查\n"
            "500 kHz: 平衡速度和稳定性\n"
            "1 MHz: 标准速度\n"
            "2 MHz: 较快，需要良好连接\n"
            "4 MHz: 高速，可能不稳定"
        )
        freq_row.addWidget(self.freq_combo)
        freq_row.addStretch()
        debug_layout.addLayout(freq_row)
        
        retry_row = QHBoxLayout()
        retry_row.addWidget(BodyLabel("连接重试次数:"))
        self.retry_slider = Slider(Qt.Orientation.Horizontal)
        self.retry_slider.setRange(1, 10)
        self.retry_slider.setValue(3)
        self.retry_slider.setFixedWidth(200)
        retry_row.addWidget(self.retry_slider)
        self.retry_label = BodyLabel("3")
        self.retry_slider.valueChanged.connect(lambda v: self.retry_label.setText(str(v)))
        retry_row.addWidget(self.retry_label)
        retry_row.addStretch()
        debug_layout.addLayout(retry_row)
        
        layout.addWidget(debug_card)
        
        # Pack card
        pack_card = CardWidget()
        pack_layout = QVBoxLayout(pack_card)
        pack_layout.addWidget(StrongBodyLabel("CMSIS-Pack 设置"))
        
        pack_dir_row = QHBoxLayout()
        pack_dir_row.addWidget(BodyLabel("Pack 目录:"))
        self.pack_dir_edit = LineEdit()
        self.pack_dir_edit.setPlaceholderText("选择 CMSIS-Pack 目录")
        pack_dir_row.addWidget(self.pack_dir_edit)
        self.pack_dir_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.pack_dir_btn.clicked.connect(self._browse_pack_dir)
        pack_dir_row.addWidget(self.pack_dir_btn)
        pack_layout.addLayout(pack_dir_row)
        
        self.pack_info_label = CaptionLabel("未设置 Pack 目录")
        pack_layout.addWidget(self.pack_info_label)
        
        layout.addWidget(pack_card)
        
        # Flash card
        flash_card = CardWidget()
        flash_layout = QVBoxLayout(flash_card)
        flash_layout.addWidget(StrongBodyLabel("烧录设置"))
        
        verify_row = QHBoxLayout()
        verify_row.addWidget(BodyLabel("默认校验烧录:"))
        self.verify_switch = SwitchButton()
        self.verify_switch.setChecked(True)
        verify_row.addWidget(self.verify_switch)
        verify_row.addStretch()
        flash_layout.addLayout(verify_row)
        
        reset_row = QHBoxLayout()
        reset_row.addWidget(BodyLabel("烧录后自动复位:"))
        self.reset_switch = SwitchButton()
        self.reset_switch.setChecked(True)
        reset_row.addWidget(self.reset_switch)
        reset_row.addStretch()
        flash_layout.addLayout(reset_row)
        
        layout.addWidget(flash_card)
        
        # About card
        about_card = CardWidget()
        about_layout = QVBoxLayout(about_card)
        about_layout.addWidget(StrongBodyLabel("关于"))
        about_layout.addWidget(BodyLabel("ARM Flash Tool v1.0.0"))
        about_layout.addWidget(CaptionLabel("基于 PyOCD 的 ARM 芯片烧录工具"))
        about_layout.addWidget(CaptionLabel("支持 CMSIS-DAP / ST-Link 调试器"))
        
        link_row = QHBoxLayout()
        self.github_btn = PushButton("GitHub", icon=FluentIcon.GITHUB)
        link_row.addWidget(self.github_btn)
        self.docs_btn = PushButton("文档", icon=FluentIcon.DOCUMENT)
        link_row.addWidget(self.docs_btn)
        link_row.addStretch()
        about_layout.addLayout(link_row)
        
        layout.addWidget(about_card)
        
        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.reset_btn = PushButton("恢复默认", icon=FluentIcon.SYNC)
        self.reset_btn.clicked.connect(self._reset_settings)
        btn_row.addWidget(self.reset_btn)
        
        self.save_btn = PushButton("保存设置", icon=FluentIcon.SAVE)
        self.save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(self.save_btn)
        
        layout.addLayout(btn_row)
        layout.addStretch()
        
    def _browse_pack_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择 CMSIS-Pack 目录")
        if path:
            self.pack_dir_edit.setText(path)
            self._update_pack_info(path)
            
    def _update_pack_info(self, path):
        if path and os.path.isdir(path):
            pack_count = len([f for f in os.listdir(path) if f.endswith('.pack')])
            self.pack_info_label.setText(f"找到 {pack_count} 个 Pack 文件")
        else:
            self.pack_info_label.setText("未设置 Pack 目录")
            
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
        freq_map = {100000: 0, 500000: 1, 1000000: 2, 2000000: 3, 4000000: 4}
        self.freq_combo.setCurrentIndex(freq_map.get(freq, 2))
        
        self.retry_slider.setValue(settings.get("connect_retries", 3))
        
        pack_dir = settings.get("pack_directory", "")
        self.pack_dir_edit.setText(pack_dir)
        self._update_pack_info(pack_dir)
        
        self.verify_switch.setChecked(settings.get("default_verify", True))
        self.reset_switch.setChecked(settings.get("default_reset", True))
        
    def _save_settings(self):
        settings = self._config.data.setdefault("settings", {})
        
        # Save theme
        theme_map = {0: "light", 1: "dark", 2: "auto"}
        settings["theme"] = theme_map.get(self.theme_combo.currentIndex(), "light")
        
        freq_map = {0: 100000, 1: 500000, 2: 1000000, 3: 2000000, 4: 4000000}
        settings["default_frequency"] = freq_map.get(self.freq_combo.currentIndex(), 1000000)
        
        settings["connect_retries"] = self.retry_slider.value()
        settings["pack_directory"] = self.pack_dir_edit.text()
        settings["default_verify"] = self.verify_switch.isChecked()
        settings["default_reset"] = self.reset_switch.isChecked()
        
        self._config.save()
        self.log_message.emit("设置已保存")
        
    def _reset_settings(self):
        self.theme_combo.setCurrentIndex(0)  # Light theme
        self.freq_combo.setCurrentIndex(2)  # 1 MHz
        self.retry_slider.setValue(3)
        self.pack_dir_edit.clear()
        self.verify_switch.setChecked(True)
        self.reset_switch.setChecked(True)
        self._update_pack_info("")
        self.log_message.emit("设置已重置")
