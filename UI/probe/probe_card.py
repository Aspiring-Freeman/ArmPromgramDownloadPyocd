#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probe Card - Debug probe detection and selection UI component
"""

import logging
from typing import Optional, Callable

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    CardWidget, ToolButton, PushButton, StrongBodyLabel, CaptionLabel,
    ListWidget, FluentIcon
)

from UI.probe.scanner import ProbeScanner
from UI.tooltip_helper import install_tooltip

LOG = logging.getLogger(__name__)


class ProbeCard(CardWidget):
    """Debug probe detection and selection card
    
    Provides:
    - Real-time probe detection
    - Background auto-scanning
    - Chip detection button
    """
    
    def __init__(self, wrapper, config, parent=None):
        super().__init__(parent)
        self._wrapper = wrapper
        self._config = config
        self._scanner: Optional[ProbeScanner] = None
        self._on_detect_chip_callback: Optional[Callable] = None
        self._on_log_message: Optional[Callable[[str], None]] = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize probe card UI"""
        layout = QVBoxLayout(self)
        
        # Header row
        header = QHBoxLayout()
        header.addWidget(StrongBodyLabel("检测到的探针"))
        
        self.scan_btn = ToolButton(FluentIcon.SYNC)
        self.scan_btn.setToolTip("刷新探针列表")
        self.scan_btn.clicked.connect(self.scan_probes)
        header.addWidget(self.scan_btn)
        
        self.detect_chip_btn = PushButton("检测芯片", icon=FluentIcon.SEARCH)
        self.detect_chip_btn.setToolTip("连接芯片并读取CPU信息，帮助识别芯片型号")
        self.detect_chip_btn.clicked.connect(self._on_detect_chip_clicked)
        header.addWidget(self.detect_chip_btn)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Probe list
        self.probe_list = ListWidget()
        self.probe_list.setMaximumHeight(120)
        self.probe_list.hide()
        layout.addWidget(self.probe_list)
        
        # No probe message
        self.no_probe_label = CaptionLabel("未检测到探针，点击刷新按钮扫描")
        layout.addWidget(self.no_probe_label)
        
        # Install tooltips
        install_tooltip(self.detect_chip_btn)
    
    def set_detect_chip_callback(self, callback: Callable):
        """Set callback for chip detection button"""
        self._on_detect_chip_callback = callback
    
    def set_log_callback(self, callback: Callable[[str], None]):
        """Set callback for log messages"""
        self._on_log_message = callback
    
    def _on_detect_chip_clicked(self):
        """Handle chip detection button click"""
        if self._on_detect_chip_callback:
            self._on_detect_chip_callback()
    
    def _log(self, message: str):
        """Log message via callback"""
        if self._on_log_message:
            self._on_log_message(message)
    
    def scan_probes(self):
        """Manually trigger probe scan"""
        probes = self._wrapper.list_probes()
        self.update_probe_list(probes)
        self._log(f"发现 {len(probes)} 个探针")
    
    def update_probe_list(self, probes):
        """Update the probe list UI"""
        self.probe_list.clear()
        if probes:
            self.no_probe_label.hide()
            self.probe_list.show()
            for p in probes:
                display_name = f"{p.product_name}"
                if p.vendor_name and p.vendor_name != "Unknown":
                    display_name = f"{p.vendor_name} {p.product_name}"
                self.probe_list.addItem(f"{display_name} [{p.unique_id[:12]}...]")
        else:
            self.no_probe_label.show()
            self.probe_list.hide()
    
    def start_scanning(self):
        """Start background probe scanning"""
        auto_scan = self._config.get('settings.auto_scan_probes', True)
        if not auto_scan:
            LOG.info("自动探针扫描已禁用")
            return
        
        scan_interval = self._config.get('settings.probe_scan_interval', 10)
        self._scanner = ProbeScanner(self._wrapper, scan_interval)
        self._scanner.probes_found.connect(self.update_probe_list)
        self._scanner.start()
    
    def stop_scanning(self):
        """Stop background probe scanning"""
        if self._scanner:
            self._scanner.stop()
    
    def get_selected_probe_id(self) -> Optional[str]:
        """Get the unique ID of the currently selected probe"""
        selected_items = self.probe_list.selectedItems()
        if selected_items:
            text = selected_items[0].text()
            if '[' in text and ']' in text:
                return text.split('[')[1].split(']')[0].replace('...', '')
        return None
    
    def get_current_item_text(self) -> Optional[str]:
        """Get current item text for chip detection"""
        if self.probe_list.currentItem():
            return self.probe_list.currentItem().text()
        return None
