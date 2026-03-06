#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reset Panel - Target reset control UI component
"""

import logging
from typing import Optional, Callable

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    CardWidget, PushButton, ToolButton, ComboBox, BodyLabel, CaptionLabel,
    StrongBodyLabel, FluentIcon, CheckBox, MessageBox
)

from Core.pyocd_wrapper import ResetType
from UI.tooltip_helper import install_tooltip

LOG = logging.getLogger(__name__)


class ResetPanel(CardWidget):
    """Reset control panel
    
    Provides:
    - Reset type selection
    - Halt after reset option
    - Reset execution
    - Reset type help documentation
    """
    
    def __init__(self, wrapper, parent=None):
        super().__init__(parent)
        self._wrapper = wrapper
        self._on_log_message: Optional[Callable[[str], None]] = None
        self._is_connected_checker: Optional[Callable[[], bool]] = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize reset panel UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        header.addWidget(StrongBodyLabel("复位控制"))
        
        self.reset_help_btn = ToolButton(FluentIcon.QUESTION)
        self.reset_help_btn.setToolTip("点击查看复位类型说明")
        self.reset_help_btn.clicked.connect(self._show_reset_help)
        header.addWidget(self.reset_help_btn)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Reset options row
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
        
        layout.addLayout(reset_row)
        
        # Reset type description
        reset_desc = CaptionLabel("💡 Default: 通用 | Hardware: 最彻底(需RESET线) | Software: 仅复位CPU | SYSRESETREQ: 系统级")
        layout.addWidget(reset_desc)
        
        # Install tooltips
        install_tooltip(self.reset_combo)
        install_tooltip(self.halt_check)
        install_tooltip(self.reset_help_btn)
    
    def set_log_callback(self, callback: Callable[[str], None]):
        """Set callback for log messages"""
        self._on_log_message = callback
    
    def set_connected_checker(self, checker: Callable[[], bool]):
        """Set callback to check if connected"""
        self._is_connected_checker = checker
    
    def _log(self, message: str):
        """Log message via callback"""
        if self._on_log_message:
            self._on_log_message(message)
    
    def _do_reset(self):
        """Execute reset operation"""
        if self._is_connected_checker and not self._is_connected_checker():
            return
        
        types = [ResetType.DEFAULT, ResetType.HARDWARE, ResetType.SOFTWARE, ResetType.SYSRESET]
        reset_type = types[self.reset_combo.currentIndex()]
        halt = self.halt_check.isChecked()
        
        if self._wrapper.reset(reset_type, halt):
            self._log("复位完成")
        else:
            self._log("复位失败")
    
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
    
    # === Public API ===
    
    def set_enabled(self, enabled: bool):
        """Enable/disable reset button based on connection state"""
        self.reset_btn.setEnabled(enabled)
    
    def update_connection_state(self, connected: bool):
        """Update UI based on connection state"""
        self.reset_btn.setEnabled(connected)
