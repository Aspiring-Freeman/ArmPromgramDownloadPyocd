# 如何在GitHub上创建Release

## 自动创建Release（推荐）

### 方法1：通过GitHub CLI（如果已安装）
```bash
gh release create v1.6.0 \
  --title "v1.6.0 - USB Auto-Scan Control & Security Enhancements" \
  --notes-file Doc/Release/RELEASE_NOTES_v1.6.0.md
```

### 方法2：通过GitHub网页界面

1. **访问项目Release页面**
   ```
   https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd/releases
   ```

2. **点击 "Draft a new release"**

3. **填写Release信息**：

   **Choose a tag**: `v1.6.0` (从下拉框选择)

   **Release title**: 
   ```
   v1.6.0 - USB Auto-Scan Control & Security Enhancements
   ```

   **Describe this release**: 复制以下内容

---

## Release Notes for v1.6.0

**Release Date**: 2026-01-10

### 🎯 Highlights

#### 🛡️ USB Device Protection
Resolved USB auto-scanning interference with USB storage devices (e.g., USB SSDs):

- **Auto-scan disabled by default** - No continuous USB device scanning on startup
- **Manual scan button** - Scan probes on-demand via refresh button
- **Configurable scan interval** - Adjustable interval if auto-scan enabled (default: 10s)

**Configuration Example**:
```json
{
  "settings": {
    "auto_scan_probes": false,      // Disable auto-scan
    "probe_scan_interval": 10       // Scan every 10s if enabled
  }
}
```

#### 🔒 Security Enhancements

**New Security Tests (130+ test cases)**:
- Input validation tests - Prevent path traversal & injection
- Resource limit tests - Memory, CPU, file size limits
- USB device filtering - Ensure only debug probes listed
- Timeout protection - All operations have timeout

**Resource Protection**:
- Memory growth limit < 100MB
- Scan timeout < 10s
- Scanner quick stop < 2s
- Thread leak prevention verified

#### 📚 Documentation Reorganization

**Clear documentation structure**:
```
Doc/
├── Development/    - Development & testing docs
├── Security/       - Security guidelines
├── Release/        - Release documentation
└── ChipConfigs/    - Chip configuration examples
```

All docs moved from root to `Doc/` subdirectory. Only `README.md` remains in root.

#### 🎨 Improved User Experience

- **Probe display optimization** - Format: `Vendor ProductName [ID]` for easier identification
- **Single scan on startup** - Shows available probes without continuous scanning
- **Cross-platform testing** - New Python test script works on Windows/Linux/macOS

---

### 📦 Downloads

**Recommended Installation**:
```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd.git
cd ArmPromgramDownloadPyocd

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests (optional)
python tests/run_quick_tests.py

# Run application
python main.py
```

---

### 🚀 Quick Start

**For systems with USB SSDs (recommended config)**:
```json
{
  "settings": {
    "auto_scan_probes": false,
    "probe_scan_interval": 30
  }
}
```

**For development environments (optional auto-scan)**:
```json
{
  "settings": {
    "auto_scan_probes": true,
    "probe_scan_interval": 10
  }
}
```

---

### 📋 What's Changed

**Features**:
- USB auto-scan control with configurable interval
- Improved probe identification display
- Cross-platform test runner script
- Single probe scan on startup

**Security**:
- Input validation for all file paths
- Resource consumption limits enforced
- USB device filtering (debug probes only)
- Timeout protection for all USB operations
- Configuration injection prevention

**Documentation**:
- Reorganized into `Doc/` with clear categories
- New guides: TESTING.md, SECURITY.md, PROJECT_ORGANIZATION.md
- Updated README with documentation links

**Tests**:
- 30+ security test cases
- 30+ resource management test cases
- Cross-platform test runner
- Test markers: security, resource, usb, slow, hardware

**Cleanup**:
- Removed `run.sh` (use `python main.py` directly)
- Moved all docs to `Doc/` subdirectory
- Cleaner root directory structure

---

### 🐛 Bug Fixes

- Fixed USB auto-scanning interfering with USB storage devices
- Fixed probe scanner thread leaks on repeated start/stop
- Fixed path traversal vulnerabilities in file handling
- Fixed excessive resource consumption during continuous scanning

---

### 📊 Test Coverage

- **Unit Tests**: 50+ cases
- **Integration Tests**: 30+ cases
- **Security Tests**: 30+ cases
- **UI Tests**: 20+ cases
- **Total**: 130+ test cases

---

### 📖 Documentation

- [TESTING.md](https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd/blob/main/Doc/Development/TESTING.md) - Testing guide
- [SECURITY.md](https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd/blob/main/Doc/Security/SECURITY.md) - Security & resource management
- [CHANGELOG.md](https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd/blob/main/Doc/Release/CHANGELOG.md) - Complete changelog
- [PROJECT_ORGANIZATION.md](https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd/blob/main/Doc/PROJECT_ORGANIZATION.md) - Project structure guide

---

### ⬆️ Upgrade Guide

Upgrading from v1.5.0 to v1.6.0:

1. **Update code**:
   ```bash
   git pull origin main
   ```

2. **Update config** (config.json):
   ```json
   {
     "settings": {
       "auto_scan_probes": false
     }
   }
   ```

3. **Run tests**:
   ```bash
   python tests/run_quick_tests.py
   ```

4. **Start application**:
   ```bash
   python main.py
   ```

No other actions required. Configuration will migrate automatically.

---

### 🙏 Acknowledgments

Thanks to all users who reported USB device interference issues. This release specifically addresses that problem.

---

**Full Changelog**: https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd/blob/main/Doc/Release/CHANGELOG.md

---

4. **点击 "Publish release"**

## 完成！

Release创建后，用户可以在以下位置看到：
- https://github.com/Aspiring-Freeman/ArmPromgramDownloadPyocd/releases/tag/v1.6.0
- 项目主页的右侧栏
- Tags页面
