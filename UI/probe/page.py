#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probe Page - Main UI Component
Probe management and connection page
Refactored to use modular panels for better maintainability
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea

from qfluentwidgets import TitleLabel, InfoBar, InfoBarPosition

from Core.chip_config import ChipConfig, normalize_pack_path

from UI.probe.probe_card import ProbeCard
from UI.probe.chip_config_panel import ChipConfigPanel
from UI.probe.connection_panel import ConnectionPanel
from UI.probe.reset_panel import ResetPanel
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
    
    Architecture:
    - ProbeCard: Probe detection and chip detection
    - ChipConfigPanel: Preset/file/pack configuration
    - ConnectionPanel: Target selection, frequency, mode, connect/disconnect
    - ResetPanel: Reset controls
    """
    
    connection_changed = pyqtSignal(bool)
    log_message = pyqtSignal(str)
    config_applied = pyqtSignal(object)  # Emits ChipConfig when preset is applied
    
    def __init__(self, wrapper, config, parent=None):
        super().__init__(parent)
        self._wrapper = wrapper
        self._config = config
        
        self._init_ui()
        self._connect_signals()
        
        # Initial probe scan
        self.probe_card.scan_probes()
        
        # Start auto-scanning
        self.probe_card.start_scanning()
    
    def _init_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        # Scroll content container
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background: transparent; }")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(20)
        
        # Title
        layout.addWidget(TitleLabel("探针与连接"))
        
        # Probe card
        self.probe_card = ProbeCard(self._wrapper, self._config, self)
        layout.addWidget(self.probe_card)
        
        # Chip configuration panel
        self.chip_config_panel = ChipConfigPanel(self)
        layout.addWidget(self.chip_config_panel)
        
        # Connection panel
        self.connection_panel = ConnectionPanel(self._wrapper, self._config, self)
        layout.addWidget(self.connection_panel)
        
        # Reset panel
        self.reset_panel = ResetPanel(self._wrapper, self)
        layout.addWidget(self.reset_panel)
        
        layout.addStretch()
        
        # Set up scroll area
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
    
    def _connect_signals(self):
        """Connect signals between panels"""
        # Probe card callbacks
        self.probe_card.set_log_callback(self._emit_log)
        self.probe_card.set_detect_chip_callback(self._detect_chip)
        
        # Chip config panel signals
        self.chip_config_panel.set_log_callback(self._emit_log)
        self.chip_config_panel.config_applied.connect(self._on_config_applied)
        self.chip_config_panel.config_changed.connect(self._on_config_changed)
        
        # Connection panel callbacks and signals
        self.connection_panel.set_log_callback(self._emit_log)
        self.connection_panel.set_config_applied_checker(
            lambda: self.chip_config_panel.is_config_applied
        )
        self.connection_panel.set_probe_id_getter(
            self.probe_card.get_selected_probe_id
        )
        self.connection_panel.set_pack_path_getter(
            self.chip_config_panel.get_pack_path
        )
        self.connection_panel.connection_changed.connect(self._on_connection_changed)
        
        # Reset panel callbacks
        self.reset_panel.set_log_callback(self._emit_log)
        self.reset_panel.set_connected_checker(
            lambda: self.connection_panel.is_connected
        )
    
    def _emit_log(self, message: str):
        """Emit log message signal"""
        self.log_message.emit(message)
    
    def _on_config_applied(self, config: ChipConfig):
        """Handle configuration applied"""
        LOG.debug(f"Config applied: {config.name}")
        
        # Update connection panel with config settings
        self._apply_config_to_connection_panel(config)
        
        # Emit signal
        self.config_applied.emit(config)
    
    def _apply_config_to_connection_panel(self, config: ChipConfig):
        """Apply config settings to connection panel"""
        self._emit_log(f"[DEBUG] 应用配置: target={config.target}, pack={config.pack_file}")
        
        # Handle pack file if present
        if config.pack_file:
            from pathlib import Path
            pack_path = Path(config.pack_file)
            if pack_path.exists():
                # Set pack path in chip config panel
                if self.chip_config_panel.loaded_pack_path != config.pack_file:
                    self.chip_config_panel.set_pack_path(config.pack_file)
                
                # Add pack targets to connection panel
                pack_info = self.chip_config_panel.pack_info
                if pack_info and pack_info.devices:
                    self.connection_panel.add_pack_targets(pack_info, pack_info.name)
        
        # Set target
        self.connection_panel.set_target(config.target)
        
        # Set frequency
        self.connection_panel.set_frequency(config.default_frequency)
        
        # Set connection mode
        self.connection_panel.set_connect_mode(config.connect_mode)
    
    def _on_config_changed(self):
        """Handle configuration selection changed (not applied)"""
        # Disconnect if connected
        if self.connection_panel.is_connected:
            self.connection_panel.disconnect_if_connected()
            self._emit_log("⚠️ 配置已更改，已自动断开连接")
    
    def _on_connection_changed(self, connected: bool):
        """Handle connection state change"""
        self.reset_panel.update_connection_state(connected)
        self.connection_changed.emit(connected)
    
    def _detect_chip(self):
        """Open chip detection dialog"""
        from UI.chip_detect_dialog import ChipDetectDialog
        
        # Get current settings
        probe_item_text = self.probe_card.get_current_item_text()
        probe_id = None
        if probe_item_text and "[" in probe_item_text and "]" in probe_item_text:
            probe_id = probe_item_text.split("[")[1].split("]")[0].replace("...", "")
        
        # Get pack path
        pack_path = self.chip_config_panel.get_pack_path()
        current_config = self.chip_config_panel.current_config
        if not pack_path and current_config and current_config.pack_file:
            pack_path = normalize_pack_path(current_config.pack_file)
        
        # Get target hint and frequency from connection panel
        target_hint = self.connection_panel.get_target() or ""
        frequency = self.connection_panel.get_frequency()
        
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
            self._emit_log(f"芯片检测完成: {result.core_type}")
            if result.matched_targets:
                for t in result.matched_targets:
                    self._emit_log(f"  {t}")
    
    # === Public API (backward compatibility) ===
    
    def stop_scanning(self):
        """Stop background probe scanning"""
        self.probe_card.stop_scanning()
    
    @property
    def is_connected(self) -> bool:
        """Check if connected (backward compatibility)"""
        return self.connection_panel.is_connected
    
    # === PresetManagerMixin integration ===
    # The PresetManagerMixin methods are available for external use
    # Internal preset management is now handled by ChipConfigPanel
