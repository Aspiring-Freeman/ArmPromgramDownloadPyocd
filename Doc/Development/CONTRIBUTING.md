# 开发指南

本文档提供 ARM 烧录工具开发环境搭建和贡献指南。

## 开发环境搭建

### 1. 克隆并初始化子模块

```bash
git clone --recurse-submodules <repo-url>
cd ArmProgramDownloadPyocd

# 如果已克隆但缺少子模块
git submodule update --init --recursive
```

### 2. 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 安装开发依赖
pip install -e ".[dev]"

# 或使用 requirements.txt
pip install -r requirements.txt
pip install pytest pytest-mock ruff mypy
```

### 3. 运行测试

```bash
# 全部测试
pytest

# 跳过需要硬件的测试
pytest -m "not usb and not hardware"

# 快速测试（跳过慢速测试）
pytest -m "not slow"

# 运行特定测试文件
pytest tests/test_chip_config.py -v

# 覆盖率报告
pytest --cov=Core --cov=UI --cov-report=html
```

### 4. 代码检查

```bash
# Ruff 代码检查
ruff check .

# Ruff 自动修复
ruff check --fix .

# 类型检查
mypy Core/ UI/

# 格式化（可选）
ruff format .
```

## 项目结构

```
Core/               业务逻辑（不依赖 Qt）
├── pyocd/          PyOCD 操作封装 (Mixin 架构)
│   ├── base.py         数据定义
│   ├── connection.py   连接管理
│   ├── flash.py        烧录操作
│   ├── erase.py        擦除操作
│   ├── reset.py        复位操作
│   └── wrapper.py      Mixin 组装
├── chip_config.py  芯片预设管理
├── config.py       应用配置 (JSON)
├── flash_info.py   Flash 信息解析（纯函数）
├── pack_parser.py  CMSIS-Pack 解析
└── logger.py       命令日志（等效命令行输出）

UI/                 Qt GUI 界面
├── probe/          探针连接页（模块化）
│   ├── page.py         主页面
│   ├── scanner.py      探针扫描
│   ├── worker.py       连接工作线程
│   └── preset_manager.py 预设管理
├── workers/        后台工作线程
│   ├── flash_worker.py
│   └── erase_worker.py
├── flash_page.py   烧录页面
├── erase_page.py   擦除页面
├── chip_config_page.py 芯片配置页面
└── main_window.py  主窗口

tests/              测试套件
├── conftest.py         共享 fixtures
├── test_chip_config.py 芯片配置测试
├── test_pyocd_wrapper.py PyOCD 封装测试（Mock）
├── test_security_safety.py 安全测试（路径穿越等）
└── test_ui_theme.py    主题兼容性测试

Doc/                文档
├── ChipConfigs/    芯片配置示例
├── Development/    开发文档
└── Release/        版本发布说明
```

## 架构设计原则

### 1. Core/UI 分离

- `Core/` 目录不可导入任何 Qt 模块
- UI 组件通过构造函数注入 wrapper 和 config
- 业务逻辑可独立于 Qt 测试

### 2. Mixin 架构 (PyOCD Wrapper)

```python
class PyOCDWrapper(ConnectionMixin, FlashMixin, EraseMixin, ResetMixin, BaseWrapper):
    """通过 Mixin 组合功能，保持单一职责"""
    pass
```

### 3. 信号槽线程安全

- 硬件操作（connect/flash/erase）在 QThread 中执行
- 使用 pyqtSignal 跨线程传递结果
- 共享资源使用 `threading.Lock` 保护

### 4. 协作式取消

```python
class FlashWorker(QThread):
    def __init__(self):
        self._cancel_event = threading.Event()
    
    def cancel(self):
        self._cancel_event.set()
    
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()
```

## 测试指南

### 单元测试

```python
# tests/test_flash_info.py
def test_resolve_flash_info_from_config():
    from Core.flash_info import resolve_flash_info
    from Core.chip_config import ChipConfig
    
    config = ChipConfig(target="STM32F103C8", flash_start=0x08000000)
    info = resolve_flash_info(config)
    
    assert info.flash_start == 0x08000000
    assert info.flash_size > 0
```

### Mock 硬件测试

```python
# tests/test_pyocd_wrapper.py
@pytest.fixture
def mock_probe():
    with patch('pyocd.probe.debug_probe.DebugProbeAggregator') as mock:
        yield mock

def test_connect_success(mock_probe, wrapper):
    mock_probe.return_value.open.return_value = True
    assert wrapper.connect() == True
```

### 安全测试

```python
# tests/test_security_safety.py
@pytest.mark.security
def test_path_traversal_blocked():
    """确保路径穿越攻击被阻止"""
    malicious_path = "../../../etc/passwd"
    with pytest.raises(ValueError):
        normalize_pack_path(malicious_path)
```

## 提交规范

提交信息格式:

```
<type>(<scope>): <subject>

<body>
```

类型:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具变更

示例:
```
feat(erase): 添加扇区擦除进度回调

- 扇区擦除现在显示实时进度
- 添加取消支持
```

## 发布流程

1. 更新 `version.py` 中的版本号
2. 更新 `Doc/Release/CHANGELOG.md`
3. 创建发布说明 `RELEASE_NOTES_vX.Y.Z.md`
4. 打 tag 并推送

```bash
git tag -a v1.8.4 -m "Release v1.8.4"
git push origin v1.8.4
```

## 常见问题

### Q: 如何添加新芯片支持?

1. 在 `Doc/ChipConfigs/` 创建 JSON 配置
2. 或在代码中添加到 `BUILTIN_PRESETS`
3. 如果需要特殊处理，修改 `Core/flash_info.py`

### Q: 如何调试 PyOCD 问题?

启用 DEBUG 日志:
```python
import logging
logging.getLogger('pyocd').setLevel(logging.DEBUG)
```

查看 `CommandLogger` 输出的等效命令行:
```
📋 pyocd flash -t stm32f103c8 firmware.hex --frequency 1000000
```

### Q: USB 权限问题 (Linux)?

安装 udev 规则:
```bash
sudo cp udev/99-arm-debug-probes.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```
