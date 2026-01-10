# Release Notes - Version 1.6.0

**发布日期**: 2026-01-10

## 🎯 主要更新

### 🛡️ USB设备保护
解决了自动扫描USB设备导致干扰USB固态硬盘的问题：

- **默认禁用自动扫描** - 启动时不再持续扫描USB设备
- **手动扫描按钮** - 需要时点击刷新按钮扫描探针
- **可配置扫描间隔** - 如需启用自动扫描，间隔可调（默认10秒）

**配置示例**:
```json
{
  "settings": {
    "auto_scan_probes": false,      // 禁用自动扫描
    "probe_scan_interval": 10       // 如启用，10秒扫描一次
  }
}
```

### 🔒 安全性增强

#### 新增安全测试（130+测试用例）
- 输入验证测试 - 防止路径遍历和注入攻击
- 资源限制测试 - 内存、CPU、文件大小限制
- USB设备过滤测试 - 确保只列出调试探针
- 超时保护测试 - 所有操作有超时机制

#### 资源保护
- 内存增长限制 < 100MB
- 扫描超时 < 10秒
- 扫描器快速停止 < 2秒
- 无线程泄漏验证

### 📚 文档重组

**清晰的文档结构**:
```
Doc/
├── Development/    - 开发和测试文档
├── Security/       - 安全指南
├── Release/        - 版本发布文档
└── ChipConfigs/    - 芯片配置示例
```

所有文档都从主目录移至 `Doc/` 子目录，主目录只保留 `README.md`。

### 🎨 改进的用户体验

- **探针显示优化** - 格式改为 `厂商 产品名 [ID]`，更易识别
- **启动时单次扫描** - 显示可用探针，但不持续扫描
- **跨平台测试** - 新增Python测试脚本，Windows/Linux/macOS通用

## 🚀 快速开始

### 运行程序
```bash
# 激活虚拟环境（可选）
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 运行程序
python main.py
```

### 运行测试
```bash
# 跨平台方式（推荐）
python tests/run_quick_tests.py

# 或手动运行
pytest tests/ -m "not usb and not slow"
```

## 📋 配置建议

### 有USB固态硬盘的系统（推荐配置）
```json
{
  "settings": {
    "auto_scan_probes": false,
    "probe_scan_interval": 30
  }
}
```

### 开发环境（可选自动扫描）
```json
{
  "settings": {
    "auto_scan_probes": true,
    "probe_scan_interval": 10
  }
}
```

## 🔍 重要变更

### 破坏性变更
无破坏性变更，所有更新向后兼容。

### 弃用功能
- `run.sh` 已删除 - 请直接使用 `python main.py`

### 新增依赖
无新增依赖。

## 🐛 已知问题

暂无已知严重问题。

## 📊 测试覆盖

- **单元测试**: 50+ 用例
- **集成测试**: 30+ 用例
- **安全测试**: 30+ 用例
- **UI测试**: 20+ 用例
- **总计**: 130+ 测试用例

## 📖 文档更新

- [TESTING.md](../Development/TESTING.md) - 测试指南
- [SECURITY.md](../Security/SECURITY.md) - 安全和资源管理
- [CHANGELOG.md](CHANGELOG.md) - 完整变更日志
- [PROJECT_ORGANIZATION.md](../PROJECT_ORGANIZATION.md) - 项目结构说明

## 🙏 感谢

感谢所有提出USB设备干扰问题的用户，此版本专门解决了该问题。

## 📝 升级指南

从 v1.5.0 升级到 v1.6.0：

1. **更新代码**:
   ```bash
   git pull origin main
   ```

2. **更新配置** (config.json):
   ```json
   {
     "settings": {
       "auto_scan_probes": false
     }
   }
   ```

3. **运行测试**:
   ```bash
   python tests/run_quick_tests.py
   ```

4. **启动程序**:
   ```bash
   python main.py
   ```

无需其他操作，配置文件会自动迁移。

---

**完整变更日志**: [CHANGELOG.md](CHANGELOG.md)  
**项目主页**: https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd
