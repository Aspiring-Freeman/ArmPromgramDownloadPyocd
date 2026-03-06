# Release Notes v1.8.4

**发布日期**: 2026-03-06

## 新增功能

### 架构改进
- **Worker 模块独立**: 将 `FlashWorker` 和 `EraseWorker` 提取到 `UI/workers/` 独立包
- **Flash 信息纯函数**: 新增 `Core/flash_info.py`，提供 `resolve_flash_info()` 纯函数，简化 `erase_page.py`
- **模块入口点**: 新增 `__main__.py`，支持 `python -m arm_flash_tool` 运行方式

### 代码质量
- **threading.Event**: Worker 取消机制从布尔标志升级为 `threading.Event`，语义更清晰
- **现代类型注解**: 6 个核心文件添加 `from __future__ import annotations`，使用 `X | None` 语法
- **pyproject.toml 完善**: 添加 `UI.workers` 到 packages 列表，修复 `pip install .` 问题

### 测试覆盖
- **test_flash_info.py**: 新增 24 个测试用例，覆盖 FlashInfo、resolve_flash_info 及边界情况

### 文档
- **CONTRIBUTING.md**: 新增完整开发指南，包含环境搭建、项目结构、测试指南

## 代码量化

| 文件 | 变化 |
|------|------|
| `erase_page.py` | -3.1 KB (apply_chip_config 90行→30行) |
| `Core/flash_info.py` | +5.8 KB (新增) |
| `test_flash_info.py` | +8.5 KB (新增) |
| `CONTRIBUTING.md` | +6 KB (新增) |

## 测试结果

```
233 passed in 15.93s
```

## 升级指南

无破坏性变更，直接更新即可。

## 完整变更列表

- feat: 添加 `Core/flash_info.py` 纯函数模块
- feat: 添加 `__main__.py` 模块入口点
- feat: Worker 使用 `threading.Event` 取消机制
- refactor: `erase_page.apply_chip_config()` 简化为调用 `resolve_flash_info()`
- fix: `pyproject.toml` 添加 `UI.workers` 包
- test: 新增 `test_flash_info.py` 共 24 个测试
- docs: 新增 `Doc/Development/CONTRIBUTING.md`
- chore: 6 个文件添加 `from __future__ import annotations`
