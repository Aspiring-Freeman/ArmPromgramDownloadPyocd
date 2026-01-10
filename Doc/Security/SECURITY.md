# 安全性和资源管理改进总结

## 🎯 主要问题解决

### 问题：USB自动扫描影响固态硬盘
**原因**: 程序每2秒自动扫描所有USB设备，可能干扰USB固态硬盘

**解决方案**:
1. ✅ 默认禁用自动扫描 (`auto_scan_probes: false`)
2. ✅ 支持手动扫描按钮
3. ✅ 启动时执行一次初始扫描显示探针
4. ✅ 可配置扫描间隔（默认10秒）

## 🛡️ 安全改进清单

### 1. USB设备扫描保护

#### 配置选项
```json
{
  "settings": {
    "auto_scan_probes": false,        // 禁用自动扫描
    "probe_scan_interval": 10         // 扫描间隔10秒
  }
}
```

#### 实现功能
- ✅ 扫描器可以完全禁用
- ✅ 扫描间隔可配置（1-60秒）
- ✅ 快速停止机制（<2秒）
- ✅ 只扫描调试探针，过滤存储设备
- ✅ 扫描超时保护（<10秒）

### 2. 资源限制

#### 内存管理
- ✅ 扫描器不泄漏线程
- ✅ 内存增长限制（<100MB）
- ✅ 配置文件大小合理限制

#### CPU使用
- ✅ 扫描频率限制（最快1秒/次）
- ✅ 后台线程使用sleep避免CPU占用
- ✅ 操作超时机制

#### 文件大小限制
- ✅ 固件文件：最大16MB
- ✅ Pack文件：最大500MB
- ✅ 配置文件：JSON结构验证

### 3. 输入验证

#### 路径安全
```python
# 防止路径遍历
"../../../etc/passwd"  ❌ 被拦截
"../../sensitive"      ❌ 被拦截
"Package/valid.pack"   ✅ 允许
```

#### 参数验证
- ✅ SWD频率：100kHz - 50MHz
- ✅ Flash地址：非负，范围检查
- ✅ 探针ID：仅字母数字
- ✅ 目标名称：非空，无特殊字符

### 4. 危险操作防护

#### 需要确认的操作
- ⚠️ 芯片擦除：需要连接
- ⚠️ Flash编程：需要有效文件
- ⚠️ 复位操作：需要连接

#### 自动保护
- ✅ 并发操作防护（线程锁）
- ✅ 文件存在性检查
- ✅ 无效地址拦截
- ✅ 错误处理和恢复

### 5. 配置安全

#### 防注入
```json
// 这些值被安全存储为字符串，不会执行
{
  "dangerous": "eval('code')",      // ✅ 存为字符串
  "command": "rm -rf /",            // ✅ 存为字符串
  "injection": "__import__('os')"   // ✅ 存为字符串
}
```

#### 验证机制
- ✅ JSON格式验证
- ✅ 深度嵌套限制
- ✅ 字符串长度检查
- ✅ 类型验证

## 📋 测试覆盖

### 新增测试文件

#### 1. test_probe_scanner.py (350行)
- 扫描器安全性测试
- 资源限制测试
- 配置控制测试
- 探针过滤测试

#### 2. test_security_safety.py (550行)
- 文件路径安全
- 配置安全
- 资源限制
- 危险操作防护
- USB设备过滤
- 输入验证
- 日志安全

### 测试标记
```bash
# 快速测试（不涉及USB）
pytest tests/ -m "not slow and not usb"

# 安全测试
pytest tests/ -m "security"

# 资源测试
pytest tests/ -m "resource"

# USB测试（小心运行）
pytest tests/ -m "usb"
```

## 🚀 使用指南

### 安全配置（推荐用于有USB SSD的系统）

```json
{
  "settings": {
    "auto_scan_probes": false,      // 禁用自动扫描
    "probe_scan_interval": 30,      // 如果启用，30秒扫描一次
    "connect_retries": 3,           // 连接重试次数
    "default_verify": true,         // 默认验证
    "default_reset": true           // 默认复位
  }
}
```

### 工作流程

1. **启动程序**
   - 不会自动扫描USB（保护固态硬盘）
   - 执行一次初始扫描显示探针

2. **选择探针**
   - 点击🔄刷新按钮手动扫描
   - 从列表选择探针
   - 格式：`厂商 产品名 [ID]`

3. **连接和操作**
   - 选择芯片型号
   - 连接到目标
   - 执行Flash/Erase操作

### 命令行工具

```bash
# 快速测试（安全，不访问USB）- 跨平台
python tests/run_quick_tests.py

# Linux/macOS专用
cd tests && ./run_tests.sh

# 完整测试
pytest tests/ -v

# 只测试安全性
pytest tests/test_security_safety.py -v

# 测试探针扫描器
pytest tests/test_probe_scanner.py -v
```

## 📊 性能指标

### 资源使用限制
- 内存增长：< 100 MB
- 扫描时间：< 10 秒
- 停止时间：< 2 秒
- 线程数量：固定，不泄漏

### 扫描频率
- 最小间隔：1 秒
- 推荐间隔：10-30 秒
- 默认间隔：10 秒
- 禁用：0（不扫描）

## ⚠️ 禁止的危险行为

### 代码级别禁止
1. ❌ **无限循环扫描** - 必须可停止
2. ❌ **无超时操作** - 所有操作有超时
3. ❌ **未验证的路径** - 必须规范化
4. ❌ **直接系统调用** - 使用pyOCD API
5. ❌ **并发Flash操作** - 使用锁机制

### 配置级别禁止
1. ❌ **频繁扫描**（<1秒） - 配置验证
2. ❌ **无限大文件** - 大小限制
3. ❌ **代码注入** - 字符串存储
4. ❌ **路径遍历** - 路径规范化

## 🔍 故障排除

### USB固态硬盘仍受影响？
```bash
# 1. 确认配置
cat config.json | grep auto_scan_probes
# 应显示: "auto_scan_probes": false

# 2. 检查是否有其他程序扫描USB
lsusb  # 查看USB设备
ps aux | grep usb  # 查看USB相关进程

# 3. 测试不触发USB
pytest tests/test_probe_scanner.py -m "not usb" -v
```

### 测试失败？
```bash
# 运行快速安全测试
./run_tests.sh

# 详细错误信息
pytest tests/test_security_safety.py -v --tb=long

# 跳过慢速测试
pytest tests/ -m "not slow" -v
```

## 📝 开发建议

### 添加新功能时
1. ✅ 添加对应的安全测试
2. ✅ 验证所有输入
3. ✅ 设置资源限制
4. ✅ 实现超时机制
5. ✅ 添加错误处理

### 测试模板
```python
@pytest.mark.security
class TestNewFeatureSafety:
    def test_input_validation(self):
        # 验证输入
        pass
    
    def test_resource_limits(self):
        # 检查资源限制
        pass
    
    def test_timeout(self):
        # 验证超时机制
        pass
```

## 📚 相关文档

- [TESTING.md](TESTING.md) - 完整测试指南
- [pytest.ini](pytest.ini) - 测试配置
- [config.json](config.json) - 应用配置
- [tests/test_security_safety.py](tests/test_security_safety.py) - 安全测试
- [tests/test_probe_scanner.py](tests/test_probe_scanner.py) - 扫描器测试

## ✅ 验证清单

安装后验证：
- [ ] `auto_scan_probes: false` 在config.json中
- [ ] 程序启动不自动扫描
- [ ] 点击刷新按钮可以扫描
- [ ] 扫描显示探针名称和ID
- [ ] 可以选择探针
- [ ] USB固态硬盘不受影响
- [ ] 测试通过：`python tests/run_quick_tests.py`

---
**最后更新**: 2026-01-10
**版本**: 1.0.0
