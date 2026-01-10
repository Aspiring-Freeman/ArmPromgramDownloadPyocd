#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Help and Documentation Page
Provides documentation for all features and configurations
"""

import logging
import sys
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame

from qfluentwidgets import (
    CardWidget, PushButton, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, StrongBodyLabel, SubtitleLabel, ExpandSettingCard,
    SettingCard, ScrollArea, SimpleCardWidget
)

from version import __version__, get_pyocd_version

LOG = logging.getLogger(__name__)


# Documentation content
DOCS = {
    "reset_types": {
        "title": "复位类型说明",
        "content": """
**Default (默认复位)**
- 使用目标芯片的默认复位方式
- 通常是最安全的选择
- 推荐大多数情况使用

**Hardware (硬件复位)**  
- 通过 nRST 引脚触发硬件复位
- 需要调试器连接到目标板的 RESET 引脚
- 最彻底的复位方式，会复位所有外设
- 适用于：芯片死锁、硬件初始化异常

**Software (软件复位)**
- 通过 AIRCR 寄存器触发软件复位
- 不需要 RESET 引脚连接
- 只复位 CPU 核心，部分外设状态可能保留
- 适用于：调试器无 RESET 连接时

**SYSRESETREQ (系统复位请求)**
- 通过 AIRCR.SYSRESETREQ 位触发
- 请求系统级复位
- 复位范围取决于芯片实现
- 适用于：需要复位整个系统但无硬件复位线时
"""
    },
    "connect_modes": {
        "title": "连接模式说明",
        "content": """
**Under Reset (复位下连接)** ⭐推荐
- 在保持复位状态下建立调试连接
- 最可靠的连接方式
- 适用于：芯片进入低功耗模式、调试口被禁用、Flash被锁定

**Halt (暂停)**
- 连接后立即暂停 CPU
- 适用于：需要在代码执行前停止芯片

**Pre-Reset (预复位)**
- 连接前先执行复位
- 适用于：需要从干净状态开始调试

**Attach (附加)**
- 连接到正在运行的目标，不干扰其执行
- 适用于：观察运行中程序的状态
- 注意：某些芯片状态可能无法正确读取
"""
    },
    "swd_frequency": {
        "title": "SWD 频率说明",
        "content": """
**100 kHz** - 最稳定
- 兼容性最好，适合调试连接不稳定的情况
- 速度较慢，适合长线缆或干扰环境

**500 kHz** - 较稳定
- 平衡速度和稳定性
- 推荐用于大多数开发板

**1 MHz** - 标准速度
- PyOCD 默认频率
- 适合大多数正常连接情况

**2 MHz** - 较快
- 适合高性能芯片
- 需要良好的硬件连接

**4 MHz+** - 高速
- 需要短线缆、良好接地
- 某些芯片可能不支持
- 如果出现 "No ACK" 错误，请降低频率
"""
    },
    "flash_addresses": {
        "title": "Flash 起始地址说明",
        "content": """
**不同厂商的默认 Flash 起始地址:**

| 厂商/系列 | Flash 地址 |
|----------|-----------|
| STM32 全系列 | 0x08000000 |
| GD32 (兆易) | 0x08000000 |
| MM32 (灵动) | 0x08000000 |
| AT32 (雅特力) | 0x08000000 |
| APM32 (极海) | 0x08000000 |
| CH32 (沁恒) | 0x08000000 |
| Nordic nRF | 0x00000000 |
| NXP LPC | 0x00000000 |
| NXP i.MX RT | 0x60000000 |
| Microchip SAM | 0x00000000 |

**HEX/ELF 文件:** 
- 地址信息已嵌入文件中，通常自动识别

**BIN 文件:**
- 必须手动指定起始地址
- 错误的地址会导致芯片无法启动！
"""
    },
    "erase_modes": {
        "title": "擦除模式说明",
        "content": """
**全片擦除 (Chip Erase)**
- 擦除芯片的整个 Flash 区域
- 包括所有扇区和用户数据
- 最彻底但耗时最长
- 某些芯片可能需要 10+ 秒

**扇区擦除 (Sector Erase)**
- 只擦除指定的扇区
- 速度快，适合部分更新
- 需要知道扇区编号

**地址范围擦除 (Range Erase)**
- 擦除指定地址范围内的扇区
- 自动计算涉及的扇区
- 实际擦除范围会对齐到扇区边界

**注意事项:**
- 擦除过程中不要断电！
- 擦除失败可能导致芯片变砖
- 某些芯片有写保护，需要先解锁
"""
    },
    "pack_files": {
        "title": "CMSIS-Pack 说明",
        "content": """
**什么是 CMSIS-Pack?**
- ARM 定义的软件包格式
- 包含芯片的调试支持信息
- Flash 算法、内存布局、SVD 文件等

**何时需要 Pack 文件?**
- PyOCD 内置支持大多数常见芯片
- 新芯片或小众芯片可能需要 Pack
- 某些特殊功能需要 Pack 支持

**获取 Pack 文件:**
1. Keil MDK Pack Installer
2. 芯片厂商官网
3. https://www.keil.com/dd2/pack/

**Pack 文件格式:**
- 文件扩展名: .pack
- 实际是 ZIP 格式
- 可以解压查看内容

**本工具支持的 Pack:**
- 自动加载 Package/Vendor/ 目录下的 Pack
- 可在设置中配置额外的 Pack 目录
"""
    },
    "troubleshooting": {
        "title": "常见问题排查",
        "content": """
**"No ACK received" 错误**
1. 检查 SWD 连线 (SWDIO, SWCLK, GND)
2. 确认目标板已供电
3. 降低 SWD 频率到 100kHz
4. 使用 "Under Reset" 连接模式
5. 检查目标是否在低功耗模式

**"Target not found" 错误**
1. 确认目标芯片型号正确
2. 检查是否需要加载 CMSIS-Pack
3. 使用 "pyocd list --targets" 查看支持列表

**"Probe not found" 错误**
1. 检查 USB 连接
2. 尝试不同 USB 端口
3. Linux: 检查 udev 规则
4. 确认调试器驱动已安装

**擦除/烧录失败**
1. Flash 可能被写保护
2. 尝试降低 SWD 频率
3. 检查电源稳定性
4. 某些芯片需要特殊解锁流程

**USB 设备断开**
1. USB 线缆质量问题
2. 目标板电源不稳定
3. 尝试使用带供电的 USB Hub
"""
    },
    "pyocd_commands": {
        "title": "PyOCD 命令行参考",
        "content": """
**列出探针:**
```
pyocd list
```

**列出支持的目标:**
```
pyocd list --targets
```

**连接目标:**
```
pyocd commander --target <target>
```

**烧录固件:**
```
pyocd flash --target <target> firmware.hex
pyocd flash --target <target> --base-address 0x08000000 firmware.bin
```

**擦除 Flash:**
```
pyocd erase --target <target> --chip
pyocd erase --target <target> --sector 0
```

**启动 GDB Server:**
```
pyocd gdbserver --target <target> --port 3333
```

**使用 Pack 文件:**
```
pyocd flash --target <target> --pack <file.pack> firmware.hex
```

**指定 SWD 频率:**
```
pyocd flash --target <target> --frequency 1000000 firmware.hex
```
"""
    },
}


class HelpPage(QWidget):
    """Help and documentation page"""
    
    log_message = pyqtSignal(str)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("帮助文档"))
        layout.addWidget(CaptionLabel("点击卡片查看详细说明"))
        
        # Version info card - NEW
        version_card = self._create_version_card()
        layout.addWidget(version_card)
        
        # Create scroll area for documentation
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)
        
        # Add documentation sections
        for key, doc in DOCS.items():
            card = self._create_doc_card(doc["title"], doc["content"])
            scroll_layout.addWidget(card)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        
        layout.addWidget(scroll)
        
        # Quick links
        links_card = CardWidget()
        links_layout = QHBoxLayout(links_card)
        links_layout.addWidget(StrongBodyLabel("快速链接:"))
        
        self.pyocd_docs_btn = PushButton("PyOCD 官方文档", icon=FluentIcon.LINK)
        self.pyocd_docs_btn.clicked.connect(lambda: self._open_url("https://pyocd.io/docs/"))
        links_layout.addWidget(self.pyocd_docs_btn)
        
        self.arm_docs_btn = PushButton("ARM 调试指南", icon=FluentIcon.LINK)
        self.arm_docs_btn.clicked.connect(lambda: self._open_url("https://developer.arm.com/"))
        links_layout.addWidget(self.arm_docs_btn)
        
        links_layout.addStretch()
        layout.addWidget(links_card)
    
    def _create_version_card(self) -> CardWidget:
        """创建版本信息卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        
        card_layout.addWidget(StrongBodyLabel("💻 版本信息"))
        
        # Tool version
        tool_version_label = BodyLabel(f"ARM Flash Tool: v{__version__}")
        card_layout.addWidget(tool_version_label)
        
        # PyOCD version
        pyocd_version = get_pyocd_version()
        pyocd_label = BodyLabel(f"Vendored PyOCD: {pyocd_version}")
        card_layout.addWidget(pyocd_label)
        
        # Python version
        python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        python_label = CaptionLabel(f"Python: {python_ver} | Platform: {sys.platform}")
        card_layout.addWidget(python_label)
        
        # Virtual environment check
        in_venv = hasattr(sys, 'real_prefix') or \
                  (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        venv_status = "✅ 虚拟环境" if in_venv else "⚠️  系统全局环境"
        venv_label = CaptionLabel(f"Environment: {venv_status}")
        card_layout.addWidget(venv_label)
        
        return card
    
    def _create_doc_card(self, title: str, content: str) -> CardWidget:
        """Create a documentation card"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        
        # Title
        title_label = SubtitleLabel(title)
        card_layout.addWidget(title_label)
        
        # Content - using TextEdit for better display
        from PyQt6.QtWidgets import QTextEdit
        content_edit = QTextEdit()
        content_edit.setReadOnly(True)
        content_edit.setPlainText(self._format_content(content))
        content_edit.setMinimumHeight(150)
        content_edit.setMaximumHeight(300)
        content_edit.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                font-size: 14px;
            }
        """)
        card_layout.addWidget(content_edit)
        
        return card
    
    def _format_content(self, content: str) -> str:
        """Format markdown-like content for display"""
        # Simple formatting - remove markdown syntax for now
        lines = content.strip().split('\n')
        formatted_lines = []
        
        for line in lines:
            # Convert markdown headers
            if line.startswith('**') and line.endswith('**'):
                line = '【' + line[2:-2] + '】'
            elif line.startswith('**'):
                line = line.replace('**', '').replace('**', '')
            # Convert bullet points
            if line.startswith('- '):
                line = '• ' + line[2:]
            if line.startswith('```'):
                continue  # Skip code block markers
            formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _open_url(self, url: str):
        """Open URL in browser"""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            self.log_message.emit(f"无法打开链接: {e}")
