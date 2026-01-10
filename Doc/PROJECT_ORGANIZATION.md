# 项目结构整理说明

## 整理日期
2026-01-10

## 整理内容

### 📂 文档整理

#### 移动的文件
主目录 → Doc子目录，按类别组织：

**开发文档** → `Doc/Development/`
- `TESTING.md` - 测试指南
- `TEST_IMPROVEMENTS.md` - 测试改进总结

**安全文档** → `Doc/Security/`
- `SECURITY.md` - 安全和资源管理指南

**发布文档** → `Doc/Release/`
- `CHANGELOG.md` - 变更日志
- `RELEASE_NOTES.md` - 发行说明

#### 新增的文档
- `Doc/README.md` - 文档索引入口
- `Doc/STRUCTURE.md` - 目录结构说明

### 🔧 脚本整理

#### 删除的脚本
- ❌ `run.sh` - 已删除
  - 原因：不跨平台，用户习惯手动激活虚拟环境
  - 替代：直接运行 `python main.py`

#### 移动的脚本
- `run_tests.sh` → `tests/run_tests.sh`
  - 仅Linux/macOS可用
  - 保留以便熟悉bash的用户使用

#### 新增的脚本
- ✅ `tests/run_quick_tests.py` - 跨平台测试脚本
  - 使用Python编写，Windows/Linux/macOS都能用
  - 自动运行快速、安全的测试（跳过USB和慢速测试）

### 📁 最终目录结构

```
项目根目录/
├── README.md                    # 主文档（唯一保留在根目录）
├── main.py                      # 程序入口
├── requirements.txt
├── pytest.ini
├── config.json
├── version.py
├── LICENSE
│
├── Core/                        # 核心模块
├── UI/                          # 界面模块
├── Driver/                      # pyOCD驱动
├── Package/                     # 芯片包
├── Mcu_Hex_Directories/         # 固件文件
├── udev/                        # Linux udev规则
│
├── tests/                       # 测试目录
│   ├── run_tests.sh            # bash测试脚本（Linux/macOS）
│   ├── run_quick_tests.py      # Python测试脚本（跨平台）✨
│   ├── conftest.py
│   ├── test_*.py               # 各种测试文件
│   └── ...
│
└── Doc/                         # 文档目录（整理后）✨
    ├── README.md               # 文档索引
    ├── STRUCTURE.md            # 目录结构
    ├── ChipConfigs/            # 芯片配置
    ├── Development/            # 开发文档
    │   ├── TESTING.md
    │   └── TEST_IMPROVEMENTS.md
    ├── Security/               # 安全文档
    │   └── SECURITY.md
    └── Release/                # 发布文档
        ├── CHANGELOG.md
        └── RELEASE_NOTES.md
```

## 使用方式

### 启动程序
```bash
# 激活虚拟环境（根据需要）
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 运行程序
python main.py
```

### 运行测试

#### 跨平台方式（推荐）
```bash
python tests/run_quick_tests.py
```

#### Linux/macOS
```bash
cd tests && ./run_tests.sh
```

#### 手动方式
```bash
pytest tests/                              # 全部测试
pytest tests/ -m "not usb and not slow"    # 快速测试
```

### 查看文档
- 主文档：`README.md`
- 文档索引：`Doc/README.md`
- 测试指南：`Doc/Development/TESTING.md`
- 安全指南：`Doc/Security/SECURITY.md`

## 改进效果

### ✅ 主目录清爽
- 只保留 `README.md` 和核心配置文件
- 无多余的 `.sh` 和 `.md` 文件

### ✅ 文档分类清晰
- Development - 开发相关
- Security - 安全相关
- Release - 发布相关
- 易于查找和维护

### ✅ 跨平台兼容
- Python测试脚本在所有平台工作
- 不依赖bash脚本
- 用户可自主选择激活虚拟环境

### ✅ 保持灵活性
- bash脚本仍保留在tests/目录
- 熟悉Linux的用户仍可使用
- 新用户使用Python脚本更简单

## 注意事项

1. **激活虚拟环境**
   - 由用户自行决定何时激活
   - 更灵活，符合个人习惯

2. **运行测试**
   - 优先使用 `python tests/run_quick_tests.py`
   - 避免触发USB设备扫描

3. **查阅文档**
   - 从 `Doc/README.md` 开始
   - 按类别查找相关文档

---

**整理人员**: GitHub Copilot  
**审核日期**: 2026-01-10
