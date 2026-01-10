# ARM Flash Programming Tool

<div align="center">

![Version](https://img.shields.io/badge/version-1.6.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)

**基于 PyOCD 的 ARM Cortex-M 芯片烧录工具**

[English](#english) | [中文](#中文)

</div>

---

## 中文

### ✨ 功能特性

- 🔌 **多探针支持**: CMSIS-DAP, ST-Link, J-Link 等主流调试器
- 🎯 **多芯片支持**: STM32, GD32, MM32, NXP, Nordic, Artery 等
- 📦 **CMSIS-Pack 支持**: 自动加载芯片定义和 Flash 算法
- 💾 **Flash 操作**: 烧录、擦除、验证一键完成
- ⚙️ **芯片预设**: 保存/导入/导出芯片配置，支持项目级管理
- 🎨 **现代化界面**: 基于 PyQt6 + Fluent Widgets 的流畅设计
- 📊 **实时日志**: 详细的操作日志和错误提示

### 📸 界面预览

```
┌─────────────────────────────────────────────────────────┐
│  ARM Flash Tool                                         │
├─────────────────────────────────────────────────────────┤
│  📡 探针与连接  │  💾 烧录  │  🗑️ 擦除  │  ⚙️ 设置      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  检测到的探针:                                           │
│  ├─ Embedfire fireDAP CMSIS-DAP [64961d75d71e...]      │
│                                                         │
│  芯片预设配置:                                           │
│  ├─ 厂商: STMicroelectronics                            │
│  └─ 预设: STM32H503CBTX Custom                          │
│                                                         │
│  目标芯片: stm32h503cbtx                                │
│  SWD频率: 10 MHz    连接模式: Under Reset               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 🚀 快速开始

#### 安装依赖

```bash
# 克隆仓库 (推荐：使用 --recurse-submodules 初始化 PyOCD 子模块)
git clone --recurse-submodules https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd.git
cd ArmPromgramDownloadPyocd

# 如果已经克隆但没有初始化子模块，运行:
git submodule update --init --recursive

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

> ⚠️ **重要**: 本项目使用本地 `Driver/pyOCD` 目录下的 PyOCD 版本以确保兼容性。
> 如果子模块未正确初始化，程序会尝试回退到 pip 安装的 PyOCD，但可能存在兼容性问题。

#### 配置 udev 规则 (仅 Linux)

```bash
sudo ./udev/install_udev_rules.sh
```

#### 运行程序

```bash
python main.py
# 或
./run.sh
```

### 🧪 运行测试

```bash
# 激活虚拟环境后运行所有测试
pytest

# 运行带覆盖率的测试
pytest --cov=Core --cov-report=html

# 运行特定测试文件
pytest tests/test_utils.py -v
```

### 📁 项目结构

```
ArmPromgramDownloadPyocd/
├── main.py                 # 主程序入口
├── Core/                   # 核心模块
│   ├── pyocd_wrapper.py    # PyOCD 封装
│   ├── chip_config.py      # 芯片配置管理
│   └── config.py           # 应用配置
├── UI/                     # 用户界面
│   ├── main_window.py      # 主窗口
│   ├── probe_page.py       # 探针连接页
│   ├── flash_page.py       # 烧录页面
│   ├── erase_page.py       # 擦除页面
│   └── settings_page.py    # 设置页面
├── tests/                  # 单元测试
│   ├── conftest.py         # pytest 配置和 fixtures
│   ├── test_utils.py       # utils 模块测试
│   ├── test_chip_config.py # 芯片配置测试
│   └── test_config.py      # 应用配置测试
├── Driver/pyOCD/           # 本地 PyOCD (Git 子模块)
├── Package/                # CMSIS-Pack 文件
│   └── Vendor/             # 按厂商分类
├── Doc/ChipConfigs/        # 芯片预设配置
└── Mcu_Hex_Directories/    # HEX/BIN 文件目录
```

### ⚙️ 配置说明

#### 连接模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **Under Reset** | 复位状态下连接 | 🔒 最可靠，推荐首选 |
| **Halt** | 连接后暂停 CPU | 正常运行的芯片 |
| **Pre-Reset** | 先复位再连接 | 需要干净状态 |
| **Attach** | 附加到运行中的芯片 | 不中断程序运行 |

#### SWD 频率

| 频率 | 建议 |
|------|------|
| 100 kHz | 长线缆、干扰环境 |
| 1 MHz | 默认推荐 |
| 4-10 MHz | 短线缆、稳定环境 |

### 🔧 故障排除

**连接失败?**
1. 检查探针与目标板连接
2. 降低 SWD 频率到 100kHz
3. 使用 "Under Reset" 模式
4. 确认 CMSIS-Pack 已加载

**擦除/烧录失败?**
1. 检查芯片是否被保护
2. 确认电源稳定
3. 尝试全片擦除

### � 文档

- **[文档索引](Doc/README.md)** - 所有文档的入口
- **[测试指南](Doc/Development/TESTING.md)** - 如何运行和编写测试
- **[安全指南](Doc/Security/SECURITY.md)** - USB扫描保护和资源管理
- **[变更日志](Doc/Release/CHANGELOG.md)** - 版本历史和更新
- **[发行说明](Doc/Release/RELEASE_NOTES.md)** - 版本亮点

### �📝 许可证

本项目基于 MIT 许可证开源。

PyOCD 使用 Apache 2.0 许可证。

---

## English

### ✨ Features

- 🔌 **Multi-probe Support**: CMSIS-DAP, ST-Link, J-Link
- 🎯 **Multi-chip Support**: STM32, GD32, MM32, NXP, Nordic, etc.
- 📦 **CMSIS-Pack Support**: Auto-load chip definitions and flash algorithms
- 💾 **Flash Operations**: Program, erase, verify in one click
- ⚙️ **Chip Presets**: Save/import/export chip configurations
- 🎨 **Modern UI**: PyQt6 + Fluent Widgets design
- 📊 **Real-time Logging**: Detailed operation logs

### 🚀 Quick Start

```bash
# Clone repository with submodules (recommended)
git clone --recurse-submodules https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd.git
cd ArmPromgramDownloadPyocd

# If already cloned without submodules:
git submodule update --init --recursive

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests (optional, cross-platform)
python tests/run_quick_tests.py  # Quick tests (skips USB tests)
# or
pytest tests/  # Full test suite

# Run application
python main.py
```

> ⚠️ **Note**: This project uses a local PyOCD version from `Driver/pyOCD` for compatibility.
> If the submodule is not initialized, it will fall back to pip-installed PyOCD.

### 📚 Documentation

- **[Documentation Index](Doc/README.md)** - Entry point for all docs
- **[Testing Guide](Doc/Development/TESTING.md)** - How to run and write tests
- **[Security Guide](Doc/Security/SECURITY.md)** - USB protection & resource management
- **[Changelog](Doc/Release/CHANGELOG.md)** - Version history
- **[Release Notes](Doc/Release/RELEASE_NOTES.md)** - Release highlights

### 📝 License

MIT License. PyOCD uses Apache 2.0 License.

---

<div align="center">

**Made with ❤️ for Embedded Developers**

</div>
