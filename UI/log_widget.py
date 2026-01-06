#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Log display widget"""

import logging
from datetime import datetime
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QTextCursor, QColor

from qfluentwidgets import (
    CardWidget, PushButton, ToolButton, PlainTextEdit,
    TitleLabel, BodyLabel, CaptionLabel, FluentIcon,
    StrongBodyLabel, ComboBox, CheckBox, SwitchButton
)

from Core.logger import command_logger

LOG = logging.getLogger(__name__)


class LogEntry:
    """Log entry"""
    def __init__(self, level: str, message: str, timestamp: datetime = None):
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()
        
    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] [{self.level}] {self.message}"


class LogWidget(QWidget):
    """Log display widget"""
    
    log_received = pyqtSignal(str)  # Signal for thread-safe logging
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[LogEntry] = []
        self._max_entries = 2000  # Increased for detailed command logs
        self._auto_scroll = True
        self._level_filter = "ALL"
        
        self._init_ui()
        self._connect_command_logger()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("日志"))
        
        # Toolbar card
        toolbar_card = CardWidget()
        toolbar_layout = QHBoxLayout(toolbar_card)
        
        toolbar_layout.addWidget(BodyLabel("级别:"))
        self.level_combo = ComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.currentTextChanged.connect(self._on_level_changed)
        toolbar_layout.addWidget(self.level_combo)
        
        self.auto_scroll_check = CheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.stateChanged.connect(self._on_auto_scroll_changed)
        toolbar_layout.addWidget(self.auto_scroll_check)
        
        toolbar_layout.addStretch()
        
        self.clear_btn = PushButton("清除", icon=FluentIcon.DELETE)
        self.clear_btn.clicked.connect(self._clear_log)
        toolbar_layout.addWidget(self.clear_btn)
        
        self.save_btn = PushButton("保存", icon=FluentIcon.SAVE)
        self.save_btn.clicked.connect(self._save_log)
        toolbar_layout.addWidget(self.save_btn)
        
        layout.addWidget(toolbar_card)
        
        # Log display
        self.log_text = PlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(400)
        self.log_text.setStyleSheet("""
            PlainTextEdit {
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # Statistics
        self.stats_label = CaptionLabel("0 条日志")
        layout.addWidget(self.stats_label)
        
        # Connect signal for thread-safe updates
        self.log_received.connect(self._on_log_received)
    
    def _connect_command_logger(self):
        """Connect to the global CommandLogger to receive detailed logs"""
        command_logger.add_callback(self._on_command_log)
    
    def _on_command_log(self, message: str):
        """Receive log from CommandLogger (may be called from any thread)"""
        # Use signal for thread-safe GUI update
        self.log_received.emit(message)
    
    def _on_log_received(self, message: str):
        """Handle log received signal (runs in GUI thread)"""
        # Determine log level from message content
        level = "INFO"
        if "❌" in message or "Error" in message or "FAILED" in message:
            level = "ERROR"
        elif "⚠️" in message or "Warning" in message:
            level = "WARNING"
        elif "✅" in message or "SUCCESS" in message:
            level = "INFO"
        elif "🔍" in message or "🔧" in message:
            level = "DEBUG"
        
        # Add without timestamp (already in message)
        entry = LogEntry(level, message.split("] ", 1)[-1] if "] " in message else message)
        entry.timestamp = datetime.now()
        
        self._entries.append(entry)
        
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
            
        if self._should_show(entry):
            self._append_raw_entry(message, level)
            
        self._update_stats()
        
    def add_log(self, message: str, level: str = "INFO"):
        """Add log entry"""
        entry = LogEntry(level, message)
        self._entries.append(entry)
        
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
            
        if self._should_show(entry):
            self._append_entry(entry)
            
        self._update_stats()
        
    def _should_show(self, entry: LogEntry) -> bool:
        if self._level_filter == "ALL":
            return True
        level_order = ["DEBUG", "INFO", "WARNING", "ERROR"]
        try:
            filter_idx = level_order.index(self._level_filter)
            entry_idx = level_order.index(entry.level)
            return entry_idx >= filter_idx
        except ValueError:
            return True
            
    def _append_entry(self, entry: LogEntry):
        color_map = {
            "DEBUG": "#808080",
            "INFO": "#2196F3",
            "WARNING": "#FF9800",
            "ERROR": "#F44336"
        }
        color = color_map.get(entry.level, "#FFFFFF")
        
        html = f'<span style="color:{color}">{str(entry)}</span>'
        self.log_text.appendHtml(html)
        
        if self._auto_scroll:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
    
    def _append_raw_entry(self, message: str, level: str):
        """Append raw message with color based on level"""
        color_map = {
            "DEBUG": "#808080",
            "INFO": "#2196F3",
            "WARNING": "#FF9800",
            "ERROR": "#F44336"
        }
        color = color_map.get(level, "#CCCCCC")
        
        # Escape HTML entities but preserve newlines
        import html
        escaped = html.escape(message)
        
        html_text = f'<span style="color:{color}; white-space: pre;">{escaped}</span><br/>'
        self.log_text.appendHtml(html_text)
        
        if self._auto_scroll:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
            
    def _on_level_changed(self, level):
        self._level_filter = level
        self._refresh_display()
        
    def _on_auto_scroll_changed(self, state):
        self._auto_scroll = state == Qt.CheckState.Checked.value
        
    def _refresh_display(self):
        self.log_text.clear()
        for entry in self._entries:
            if self._should_show(entry):
                self._append_entry(entry)
                
    def _clear_log(self):
        self._entries.clear()
        self.log_text.clear()
        self._update_stats()
        
    def _save_log(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "arm_flash_log.txt", "Text Files (*.txt)"
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    for entry in self._entries:
                        f.write(str(entry) + '\n')
                self.add_log(f"日志已保存到: {path}", "INFO")
            except Exception as e:
                self.add_log(f"保存失败: {e}", "ERROR")
                
    def _update_stats(self):
        total = len(self._entries)
        shown = sum(1 for e in self._entries if self._should_show(e))
        self.stats_label.setText(f"{shown}/{total} 条日志")


class LogHandler(logging.Handler):
    """Custom log handler to redirect to LogWidget"""
    def __init__(self, widget: LogWidget):
        super().__init__()
        self._widget = widget
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self._widget.add_log(msg, record.levelname)
        except Exception:
            pass
