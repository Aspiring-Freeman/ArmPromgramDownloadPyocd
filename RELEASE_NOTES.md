# Release v1.0.0 - Initial Release

## 🎉 ARM Flash Programming Tool v1.0.0

基于 PyOCD 的 ARM Cortex-M 芯片烧录工具首个正式版本发布！

### ✨ 功能特性

#### 🔌 硬件支持
- **多探针支持**: CMSIS-DAP, ST-Link, J-Link 等主流调试器
- **多芯片支持**: STM32, GD32, MM32, NXP, Nordic, Artery, WCH 等
- **CMSIS-Pack 支持**: 自动加载芯片定义和 Flash 算法

#### 💾 Flash 操作
- 烧录 HEX/BIN 文件
- 烧录前自动擦除
- 烧录后验证
- 烧录后复位

#### 🗑️ 擦除功能
- 全片擦除
- 扇区擦除
- 批量擦除

#### ⚙️ 芯片预设系统
- 保存/加载芯片配置
- 导入/导出 JSON 预设文件
- 项目级预设管理 (Doc/ChipConfigs/)
- 内置常用芯片预设

#### 🎨 现代化界面
- PyQt6 + Fluent Widgets 流畅设计
- 明亮/暗黑主题切换
- 实时操作日志
- 帮助文档页面

### 📋 系统要求

- Python 3.9+
- Linux / Windows / macOS
- 调试探针 (CMSIS-DAP / ST-Link / J-Link)

### 🚀 快速开始

```bash
git clone https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd.git
cd ArmPromgramDownloadPyocd
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 📦 包含内容

- 完整源代码
- 本地 PyOCD v0.36.0
- 示例 CMSIS-Pack 文件
- udev 规则 (Linux)
- 帮助文档

---

**Full Changelog**: https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd/commits/v1.0.0
