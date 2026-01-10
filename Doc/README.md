# 文档索引

本目录包含ARM Flash Programming Tool的所有文档。

## 📁 目录结构

### � 项目组织
- [PROJECT_ORGANIZATION.md](PROJECT_ORGANIZATION.md) - 项目结构整理说明

### �📖 ChipConfigs/
芯片配置预设文件
- 各种芯片的配置示例
- JSON格式的预设配置

### 🔧 Development/
开发相关文档
- [TESTING.md](Development/TESTING.md) - 测试指南
- [TEST_IMPROVEMENTS.md](Development/TEST_IMPROVEMENTS.md) - 测试改进总结

### 🛡️ Security/
安全相关文档
- [SECURITY.md](Security/SECURITY.md) - 安全改进和资源管理

### 📦 Release/
版本发布文档
- [CHANGELOG.md](Release/CHANGELOG.md) - 变更日志
- [RELEASE_NOTES.md](Release/RELEASE_NOTES.md) - 发行说明

## 🚀 快速链接

### 开发者文档
- **测试指南**: [Development/TESTING.md](Development/TESTING.md)
  - 如何运行测试
  - 测试标记和分类
  - CI/CD集成

- **测试改进**: [Development/TEST_IMPROVEMENTS.md](Development/TEST_IMPROVEMENTS.md)
  - 新增测试内容
  - 测试覆盖率
  - 改进总结

### 安全文档
- **安全指南**: [Security/SECURITY.md](Security/SECURITY.md)
  - USB扫描保护
  - 资源限制
  - 输入验证
  - 危险操作防护

### 发布文档
- **变更日志**: [Release/CHANGELOG.md](Release/CHANGELOG.md)
  - 版本历史
  - 功能更新
  - Bug修复

- **发行说明**: [Release/RELEASE_NOTES.md](Release/RELEASE_NOTES.md)
  - 版本亮点
  - 升级指南
  - 已知问题

## 📝 芯片配置

### 预设配置示例
- [FM33LG04x系列](ChipConfigs/FM33LG04X.json)
- [STM32系列](ChipConfigs/)
- 更多配置请查看 [ChipConfigs/](ChipConfigs/) 目录

### 创建自定义配置
参考 [ChipConfigs/](ChipConfigs/) 目录中的示例文件

## 🔍 文档搜索

### 按主题查找

#### 测试相关
- 测试指南: [Development/TESTING.md](Development/TESTING.md)
- 测试改进: [Development/TEST_IMPROVEMENTS.md](Development/TEST_IMPROVEMENTS.md)

#### 安全相关
- USB扫描问题: [Security/SECURITY.md](Security/SECURITY.md#usb扫描保护)
- 资源限制: [Security/SECURITY.md](Security/SECURITY.md#资源限制)
- 输入验证: [Security/SECURITY.md](Security/SECURITY.md#输入验证)

#### 版本信息
- 最新变更: [Release/CHANGELOG.md](Release/CHANGELOG.md)
- 发行说明: [Release/RELEASE_NOTES.md](Release/RELEASE_NOTES.md)

## 🛠️ 贡献指南

### 添加新文档
1. 确定文档类型（开发/安全/发布）
2. 放入对应目录
3. 更新本索引文件

### 文档规范
- 使用Markdown格式
- 中文文档为主
- 包含目录和示例
- 及时更新日期

## 📧 问题反馈

如果文档有问题或需要补充，请：
1. 检查现有文档是否已覆盖
2. 提交Issue说明需求
3. 或直接提交Pull Request

---

**最后更新**: 2026-01-10
