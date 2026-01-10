# Release v1.4.0 - Chip Detection & Pack Parser

## 🎉 ARM Flash Programming Tool v1.4.0

新增芯片检测功能和 CMSIS-Pack 解析器！

### ✨ 新功能

#### 🔍 芯片检测
- **自动检测芯片型号**: 通过读取 CPUID 寄存器识别连接的芯片
- **检测配置对话框**: 可配置 Pack 文件、频率、目标提示
- **结果分类显示**: 清晰区分"芯片信息"、"Pack目标"、"当前配置"

#### 📦 CMSIS-Pack 解析
- **Pack 解析器**: 新增 `Core/pack_parser.py` 模块
- **设备信息提取**: 自动读取 Flash 起始地址、大小、RAM 信息
- **厂商版本支持**: 显示 Pack 厂商和版本信息

#### 🎛️ UI 重新设计
- **探测页三选一配置**: RadioButton 选择配置来源
  - 文件导入: 从 JSON 文件加载配置
  - 预设选择: 从已保存的预设选择
  - Pack 导入: 从 CMSIS-Pack 设备定义导入
- **擦除页增强**:
  - 芯片配置信息卡片
  - 扇区信息显示和地址范围
  - 地址范围验证和警告提示

#### 🗃️ 预设管理增强
- **删除预设按钮**: 带确认对话框
- **导出名称同步**: 复选框控制是否使用默认文件名
- **Pack 地址保存**: 正确保存 Pack 来源的 Flash 地址

### 🐛 Bug 修复
- 修复 main_window.py 中重复的信号连接
- 修复 qfluentwidgets ComboBox itemData() 返回 None 的问题
- 修复 ChipDetectDialog 的主题样式问题
- 修复最近文件选择的路径映射问题
- 清理未使用的导入

---

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
