#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Window - Qt Fluent Design
"""

import os
import logging
from typing import Optional
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt6.QtGui import QColor

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    InfoBar, InfoBarPosition, StateToolTip, MessageBox,
    setTheme, Theme, setThemeColor, isDarkTheme
)

from .flash_page import FlashPage
from .erase_page import ErasePage
from .probe_page import ProbePage
from .log_widget import LogWidget
from .settings_page import SettingsPage
from .chip_config_page import ChipConfigPage
from .help_page import HelpPage

LOG = logging.getLogger(__name__)


class MainWindow(FluentWindow):
    """Main application window with Fluent Design"""
    
    def __init__(self, pyocd_wrapper, config_manager, parent=None):
        super().__init__(parent)
        
        self._wrapper = pyocd_wrapper
        self._config = config_manager
        self._state_tooltip: Optional[StateToolTip] = None
        
        self._init_window()
        self._apply_theme()  # Apply theme BEFORE creating pages
        self._init_pages()
        self._connect_signals()
        self._restore_geometry()
        
    def _init_window(self):
        self.setWindowTitle("ARM Flash Programming Tool")
        self.setMinimumSize(1000, 700)
        
    def _init_pages(self):
        # Create pages
        self.probe_page = ProbePage(self._wrapper, self._config, self)
        self.probe_page.setObjectName("probe_page")
        
        self.flash_page = FlashPage(self._wrapper, self._config, self)
        self.flash_page.setObjectName("flash_page")
        
        self.erase_page = ErasePage(self._wrapper, self._config, self)
        self.erase_page.setObjectName("erase_page")
        
        self.chip_config_page = ChipConfigPage(self._config, self)
        self.chip_config_page.setObjectName("chip_config_page")
        
        self.help_page = HelpPage(self._config, self)
        self.help_page.setObjectName("help_page")
        
        self.log_widget = LogWidget(self)
        self.log_widget.setObjectName("log_widget")
        
        self.settings_page = SettingsPage(self._config, self)
        self.settings_page.setObjectName("settings_page")
        
        # Add to navigation
        self.addSubInterface(self.probe_page, FluentIcon.CONNECT, "探针连接")
        self.addSubInterface(self.flash_page, FluentIcon.DOWNLOAD, "烧录")
        self.addSubInterface(self.erase_page, FluentIcon.DELETE, "擦除")
        self.addSubInterface(self.chip_config_page, FluentIcon.LIBRARY, "芯片配置")
        self.addSubInterface(self.log_widget, FluentIcon.DOCUMENT, "日志")
        self.addSubInterface(self.help_page, FluentIcon.HELP, "帮助", NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, "设置", NavigationItemPosition.BOTTOM)
        
        self.switchTo(self.probe_page)
        
    def _connect_signals(self):
        self.probe_page.connection_changed.connect(self._on_connection_changed)
        self.probe_page.log_message.connect(self._log)
        self.probe_page.config_applied.connect(self._on_chip_config_applied)
        
        self.flash_page.operation_started.connect(lambda: self._on_op_started("烧录"))
        self.flash_page.operation_finished.connect(self._on_op_finished)
        self.flash_page.log_message.connect(self._log)
        
        self.erase_page.operation_started.connect(lambda: self._on_op_started("擦除"))
        self.erase_page.operation_finished.connect(self._on_op_finished)
        self.erase_page.log_message.connect(self._log)
        
        self.chip_config_page.log_message.connect(self._log)
        self.chip_config_page.preset_selected.connect(self._on_chip_config_applied)
        
        self.help_page.log_message.connect(self._log)
        
        self.settings_page.theme_changed.connect(self._apply_theme)
        self.settings_page.log_message.connect(self._log)
    
    def _on_chip_config_applied(self, chip_config):
        """Handle chip config applied from probe page or chip config page"""
        # Only apply to flash page (sets address)
        # Probe page settings (target, frequency, mode) are managed by user's "应用预设" button
        self.flash_page.apply_chip_config(chip_config)
        # Apply to erase page if needed
        if hasattr(self.erase_page, 'apply_chip_config'):
            self.erase_page.apply_chip_config(chip_config)
        
    def _apply_theme(self):
        theme = self._config.get_theme()
        if theme == "auto":
            import darkdetect
            setTheme(Theme.DARK if darkdetect.isDark() else Theme.LIGHT)
        elif theme == "dark":
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.LIGHT)
        setThemeColor(QColor("#0078D4"))
        
    def _restore_geometry(self):
        x, y, w, h = self._config.get_window_geometry()
        self.resize(w, h)
        if x is not None and y is not None:
            self.move(x, y)
            
    def _save_geometry(self):
        g = self.geometry()
        self._config.set_window_geometry(g.x(), g.y(), g.width(), g.height())
        
    def _log(self, msg: str, level: str = "INFO"):
        self.log_widget.add_log(msg, level)
        
    @pyqtSlot(bool)
    def _on_connection_changed(self, connected: bool):
        if connected:
            self._log("已连接到目标设备", "info")
            InfoBar.success("连接成功", "已连接到目标", parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            self._log("已断开连接", "info")
        self.flash_page.set_connected(connected)
        self.erase_page.set_connected(connected)
        
    def _on_op_started(self, op: str):
        self._state_tooltip = StateToolTip(f"正在{op}...", "请稍候", self)
        self._state_tooltip.move(self._state_tooltip.getSuitablePos())
        self._state_tooltip.show()
        
    @pyqtSlot(bool, str)
    def _on_op_finished(self, success: bool, msg: str):
        if self._state_tooltip:
            self._state_tooltip.setContent(msg)
            self._state_tooltip.setState(success)
            self._state_tooltip = None
        
        # Note: InfoBar notifications are handled by individual pages (flash_page, erase_page)
        # to avoid duplicate notifications
        
        if not success:
            if not self._wrapper.is_connected:
                self._log("检测到连接已断开", "warning")
                self._on_connection_changed(False)
                # Update probe page UI
                if hasattr(self.probe_page, '_update_ui_connected'):
                    self.probe_page._update_ui_connected(False)
                if hasattr(self.probe_page, 'connect_status'):
                    self.probe_page.connect_status.setText("连接已断开")
            
    def closeEvent(self, event):
        """Handle application close with proper resource cleanup
        
        Order of cleanup:
        1. Stop UI workers (flash/erase workers)
        2. Cancel connection attempts
        3. Stop background scanning
        4. Disconnect from hardware
        5. Save window state
        """
        LOG.info("Application closing, cleaning up resources...")
        
        # 1. Stop any ongoing flash/erase workers first
        if hasattr(self.flash_page, '_worker') and self.flash_page._worker:
            if self.flash_page._worker.isRunning():
                LOG.info("Stopping flash worker...")
                self.flash_page._worker.cancel()
                self.flash_page._worker.wait(2000)
                if self.flash_page._worker.isRunning():
                    self.flash_page._worker.terminate()
                    self.flash_page._worker.wait()
        
        if hasattr(self.erase_page, '_worker') and self.erase_page._worker:
            if self.erase_page._worker.isRunning():
                LOG.info("Stopping erase worker...")
                self.erase_page._worker.cancel()
                self.erase_page._worker.wait(2000)
                if self.erase_page._worker.isRunning():
                    self.erase_page._worker.terminate()
                    self.erase_page._worker.wait()
        
        # 2. Cancel any ongoing connection attempts
        if hasattr(self.probe_page, '_connect_worker') and self.probe_page._connect_worker:
            if self.probe_page._connect_worker.isRunning():
                LOG.info("Stopping connection worker...")
                self.probe_page._connect_worker.wait(1000)
                if self.probe_page._connect_worker.isRunning():
                    self.probe_page._connect_worker.terminate()
                    self.probe_page._connect_worker.wait()
        
        # 3. Stop background scanning
        try:
            LOG.info("Stopping probe scanner...")
            self.probe_page.stop_scanning()
        except Exception as e:
            LOG.warning(f"Error stopping scanner: {e}")
        
        # 4. Force disconnect (skip lock acquisition during shutdown)
        try:
            LOG.info("Disconnecting from hardware...")
            self._wrapper.disconnect(force=True)
        except Exception as e:
            LOG.warning(f"Error during disconnect: {e}")
        
        # 5. Save page settings
        try:
            if hasattr(self.flash_page, '_save_config'):
                self.flash_page._save_config()
        except Exception as e:
            LOG.warning(f"Error saving flash page config: {e}")
        
        # 6. Save geometry
        self._save_geometry()
        
        LOG.info("Cleanup complete, exiting")
        event.accept()
