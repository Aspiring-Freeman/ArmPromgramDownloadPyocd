#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chip Detection Dialog
Dialog for detecting connected chip with configurable options
"""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFileDialog,
    QGroupBox, QFormLayout, QFrame
)

from qfluentwidgets import (
    LineEdit, ComboBox, PushButton, PrimaryPushButton,
    BodyLabel, StrongBodyLabel, CaptionLabel,
    FluentIcon, TextEdit, ProgressRing, isDarkTheme,
    setTheme, Theme
)

LOG = logging.getLogger(__name__)


class DetectWorker(QThread):
    """Worker thread for chip detection"""
    finished = pyqtSignal(object)
    
    def __init__(self, wrapper, probe_id, frequency, pack_path, target_hint):
        super().__init__()
        self._wrapper = wrapper
        self._probe_id = probe_id
        self._frequency = frequency
        self._pack_path = pack_path
        self._target_hint = target_hint
    
    def run(self):
        result = self._wrapper.detect_chip(
            self._probe_id, self._frequency, 
            self._pack_path, self._target_hint
        )
        self.finished.emit(result)


class ChipDetectDialog(QDialog):
    """Dialog for chip detection with options"""
    
    def __init__(self, wrapper, parent=None, 
                 initial_pack: str = "", 
                 initial_target: str = "",
                 initial_frequency: int = 1000000,
                 probe_id: str = None):
        super().__init__(parent)
        self._wrapper = wrapper
        self._probe_id = probe_id
        self._worker = None
        self._result = None
        
        self.setWindowTitle("芯片检测")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Apply theme-aware styling
        self._apply_theme_style()
        
        self._init_ui(initial_pack, initial_target, initial_frequency)
    
    def _apply_theme_style(self):
        """Apply theme-aware styling to the dialog"""
        if isDarkTheme():
            self.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #555;
                    border-radius: 6px;
                    margin-top: 12px;
                    padding-top: 10px;
                    background-color: #333;
                    color: #e0e0e0;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    color: #e0e0e0;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #f5f5f5;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    margin-top: 12px;
                    padding-top: 10px;
                    background-color: #fff;
                    color: #1a1a1a;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    color: #1a1a1a;
                }
            """)
    
    def _init_ui(self, initial_pack: str, initial_target: str, initial_frequency: int):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = StrongBodyLabel("芯片检测配置")
        layout.addWidget(title)
        
        desc = CaptionLabel("连接到目标芯片并读取芯片信息。对于非内置芯片（如FM33系列），需要指定Pack文件。")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Options group
        options_group = QGroupBox("检测选项")
        options_layout = QFormLayout(options_group)
        options_layout.setSpacing(10)
        
        # Pack file
        pack_row = QHBoxLayout()
        self.pack_edit = LineEdit()
        self.pack_edit.setPlaceholderText("可选：选择 CMSIS-Pack 文件以支持非内置芯片")
        self.pack_edit.setText(initial_pack)
        pack_row.addWidget(self.pack_edit)
        self.pack_btn = PushButton("浏览", icon=FluentIcon.FOLDER)
        self.pack_btn.clicked.connect(self._browse_pack)
        pack_row.addWidget(self.pack_btn)
        options_layout.addRow("Pack文件:", pack_row)
        
        # Target hint
        self.target_edit = LineEdit()
        self.target_edit.setPlaceholderText("可选：目标芯片名称提示 (如 fm33lg04x)")
        self.target_edit.setText(initial_target)
        options_layout.addRow("目标提示:", self.target_edit)
        
        # Frequency
        freq_row = QHBoxLayout()
        self.freq_combo = ComboBox()
        self.freq_combo.addItems(["100 kHz", "500 kHz", "1 MHz", "2 MHz", "4 MHz", "10 MHz"])
        # Set initial frequency
        freq_map = {100000: 0, 500000: 1, 1000000: 2, 2000000: 3, 4000000: 4, 10000000: 5}
        self.freq_combo.setCurrentIndex(freq_map.get(initial_frequency, 2))
        freq_row.addWidget(self.freq_combo)
        freq_row.addStretch()
        options_layout.addRow("SWD频率:", freq_row)
        
        layout.addWidget(options_group)
        
        # Detection button
        detect_row = QHBoxLayout()
        self.detect_btn = PrimaryPushButton("开始检测", icon=FluentIcon.SEARCH)
        self.detect_btn.clicked.connect(self._start_detection)
        detect_row.addWidget(self.detect_btn)
        
        self.progress = ProgressRing()
        self.progress.setFixedSize(24, 24)
        self.progress.hide()
        detect_row.addWidget(self.progress)
        
        detect_row.addStretch()
        layout.addLayout(detect_row)
        
        # Result group
        result_group = QGroupBox("检测结果")
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = TextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("点击「开始检测」查看结果...")
        self.result_text.setMinimumHeight(150)
        result_layout.addWidget(self.result_text)
        
        layout.addWidget(result_group)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.close_btn = PushButton("关闭")
        self.close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.close_btn)
        
        layout.addLayout(btn_row)
    
    def _browse_pack(self):
        """Browse for pack file"""
        # Default to Package directory
        default_dir = str(Path(__file__).parent.parent / "Package")
        
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 CMSIS-Pack 文件", default_dir,
            "Pack Files (*.pack);;All Files (*)"
        )
        if path:
            self.pack_edit.setText(path)
    
    def _get_frequency(self) -> int:
        """Get frequency from combo"""
        freq_map = {0: 100000, 1: 500000, 2: 1000000, 3: 2000000, 4: 4000000, 5: 10000000}
        return freq_map.get(self.freq_combo.currentIndex(), 1000000)
    
    def _start_detection(self):
        """Start chip detection"""
        self.detect_btn.setEnabled(False)
        self.progress.show()
        self.result_text.setPlainText("正在检测芯片，请稍候...")
        
        pack_path = self.pack_edit.text().strip() or None
        target_hint = self.target_edit.text().strip() or None
        frequency = self._get_frequency()
        
        # Show detection mode
        if pack_path:
            mode_text = f"使用Pack: {Path(pack_path).name}"
        elif target_hint:
            mode_text = f"使用目标提示: {target_hint}"
        else:
            mode_text = "通用模式 (cortex_m)"
        
        self.result_text.setPlainText(f"检测模式: {mode_text}\n正在连接...")
        
        self._worker = DetectWorker(
            self._wrapper, 
            self._probe_id, 
            frequency, 
            pack_path, 
            target_hint
        )
        self._worker.finished.connect(self._on_detection_finished)
        self._worker.start()
    
    def _on_detection_finished(self, result):
        """Handle detection result"""
        self.detect_btn.setEnabled(True)
        self.progress.hide()
        self._result = result
        
        if not result.success:
            self.result_text.setPlainText(f"❌ 检测失败\n\n错误: {result.error}")
            return
        
        # Build result text
        lines = [
            "✅ 连接成功",
            "",
            "═══ 从芯片读取的信息（实际硬件）═══",
            f"CPU ID:     0x{result.cpuid:08X}",
            f"内核类型:   {result.core_type}",
            f"架构:       {result.architecture}",
            f"实现者:     {result.implementer}",
        ]
        
        if result.vendor_id:
            lines.extend([
                "",
                f"芯片UID:    0x{result.vendor_id:08X}",
            ])
        
        # Parse matched_targets to separate actual vs pack info
        actual_target = ""
        actual_target_name = ""  # Just the target name without extra info
        pack_targets = []
        flash_info = ""
        ram_info = ""
        warning_msg = ""
        
        if result.matched_targets:
            for t in result.matched_targets:
                if t.startswith("✓ 使用目标:"):
                    actual_target = t.replace("✓ 使用目标:", "").strip()
                    # Extract just the target name (before any parentheses)
                    actual_target_name = actual_target.split()[0].lower() if actual_target else ""
                elif t.startswith("⚠"):
                    warning_msg = t
                elif t.startswith("Pack可用目标:"):
                    continue  # Skip header
                elif t.strip().startswith("• "):
                    pack_targets.append(t.strip()[2:])  # Remove "• "
                elif t.strip().startswith("Flash:"):
                    flash_info = t.strip()
                elif t.strip().startswith("RAM:"):
                    ram_info = t.strip()
        
        # Show pack available targets prominently
        if pack_targets:
            lines.extend([
                "",
                "═══ Pack 中可用的芯片型号 ═══",
            ])
            for t in pack_targets:
                # Mark the currently used target
                is_current = (t.lower() == actual_target_name)
                marker = "→" if is_current else " "
                lines.append(f"  {marker} {t}")
            
            lines.extend([
                "",
                "提示: 请根据你的实际芯片选择正确的型号。",
            ])
        
        # Show what target was actually used
        if actual_target:
            lines.extend([
                "",
                "═══ 当前使用的目标配置 ═══",
                f"目标:  {actual_target}",
            ])
            if flash_info:
                lines.append(f"{flash_info}")
            if ram_info:
                lines.append(f"{ram_info}")
            
            lines.extend([
                "",
                "⚠ 注意: Flash/RAM 大小来自 Pack 定义，",
                "        如果型号选错，这些值可能不正确！",
            ])
        
        if warning_msg:
            lines.extend([
                "",
                warning_msg,
            ])
        
        # Show hint about target hint field
        target_hint = self.target_edit.text().strip()
        if target_hint and pack_targets:
            # Check if hint matches any pack target
            hint_lower = target_hint.lower()
            matched = any(hint_lower in t.lower() or t.lower() in hint_lower for t in pack_targets)
            if not matched:
                lines.extend([
                    "",
                    f"💡 您输入的目标提示「{target_hint}」不在 Pack 中，",
                    "   系统自动使用了 Pack 的第一个目标。",
                    "   建议清空目标提示或输入正确的型号名称。",
                ])
        
        lines.extend([
            "",
            "════════════════════",
        ])
        
        self.result_text.setPlainText("\n".join(lines))
    
    def get_result(self):
        """Get detection result"""
        return self._result
