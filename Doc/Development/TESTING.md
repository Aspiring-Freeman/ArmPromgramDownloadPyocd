# Testing Guide

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Quick tests (cross-platform, recommended)
```bash
# Python script (works on Windows/Linux/macOS)
python tests/run_quick_tests.py

# Or bash script (Linux/macOS only)
cd tests && ./run_tests.sh
```

### Run specific test categories

#### Fast tests only (skip slow tests)
```bash
pytest tests/ -m "not slow"
```

#### Skip USB tests (recommended for systems with USB storage)
```bash
pytest tests/ -m "not usb" -v
```

#### Security and safety tests
```bash
pytest tests/test_security_safety.py -v
```

#### Probe scanner tests
```bash
pytest tests/test_probe_scanner.py -v
```

#### Skip hardware-dependent tests
```bash
pytest tests/ -m "not hardware"
```

#### Skip USB-related tests (to avoid affecting USB storage)
```bash
pytest tests/ -m "not usb"
```

### Run with coverage
```bash
pytest tests/ --cov=Core --cov=UI --cov-report=html
```

## Test Categories

### 1. Unit Tests
- `test_config.py` - Configuration management
- `test_chip_config.py` - Chip configuration
- `test_logger.py` - Logging functionality
- `test_utils.py` - Utility functions
- `test_pack_parser.py` - CMSIS-Pack parsing

### 2. Integration Tests
- `test_integration.py` - Cross-module integration
- `test_pyocd_wrapper.py` - PyOCD wrapper functionality

### 3. UI Tests
- `test_ui_theme.py` - UI theme handling
- `test_tooltip_helper.py` - Tooltip functionality

### 4. Safety Tests ⚠️
- `test_security_safety.py` - Security and resource safety
- `test_probe_scanner.py` - Probe scanning safety

## Safety and Security Tests

### Purpose
These tests ensure that:
1. **USB scanning doesn't affect storage devices**
2. **Resource limits are enforced** (memory, CPU, file sizes)
3. **Path traversal attacks are prevented**
4. **Input validation prevents injection**
5. **Scanner can be disabled** to avoid USB interference

### Critical Safety Features Tested

#### 1. Auto-scan Control
- Tests that `auto_scan_probes: false` prevents automatic USB scanning
- Verifies manual scan-only operation
- Ensures scanner respects configured intervals

#### 2. Resource Limits
- Scanner doesn't leak threads
- Memory usage stays within bounds
- File sizes are validated
- Operations have timeouts

#### 3. USB Device Filtering
- Only debug probes are listed
- Storage devices are excluded
- Scanning has timeout protection

#### 4. Input Validation
- File paths are sanitized
- Frequencies are in valid range
- Target names are validated
- Probe IDs are alphanumeric only

## Dangerous Operations Prevention

### Disabled by Default
- ❌ **Automatic USB scanning** - Can be enabled in config
- ❌ **Chip erase without confirmation** - Requires explicit connection
- ❌ **Concurrent operations** - Prevented by locking mechanism

### Always Validated
- ✅ **File existence** - Before flash operations
- ✅ **File size limits** - Reject oversized files
- ✅ **Path traversal** - Normalized and validated
- ✅ **Flash addresses** - Range checked
- ✅ **SWD frequency** - Min/max bounds enforced

## Configuration Safety

### config.json Settings

#### Safe Defaults
```json
{
  "settings": {
    "auto_scan_probes": false,
    "probe_scan_interval": 10,
    "connect_retries": 3,
    "default_verify": true,
    "default_reset": true
  }
}
```

#### Recommended for USB SSD Systems
```json
{
  "settings": {
    "auto_scan_probes": false,
    "probe_scan_interval": 30
  }
}
```

## Continuous Integration

### GitHub Actions / GitLab CI
```yaml
test:
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    # Run fast tests only in CI
    - pytest tests/ -m "not slow and not hardware and not usb"
```

## Test Coverage Goals

- **Core modules**: > 80% coverage
- **Safety-critical code**: > 95% coverage
- **UI code**: > 60% coverage

## Adding New Tests

### Template for Safety Tests
```python
import pytest

class TestNewFeatureSafety:
    """Tests for <feature> safety"""
    
    def test_resource_limits(self):
        """Test that <feature> respects resource limits"""
        # Test implementation
        pass
    
    def test_input_validation(self):
        """Test that <feature> validates input"""
        # Test implementation
        pass
    
    @pytest.mark.slow
    def test_performance(self):
        """Test that <feature> completes in reasonable time"""
        # Test implementation
        pass
```

## Troubleshooting Tests

### Test hangs
- Check for USB device access issues
- Run with timeout: `pytest tests/ --timeout=30`

### Import errors
- Ensure virtual environment is activated
- Check that pyOCD is installed: `pip install -e Driver/pyOCD`

### USB-related failures
- Run without USB tests: `pytest tests/ -m "not usb"`
- Check USB permissions on Linux

## Pre-commit Tests

Recommended pre-commit hook:
```bash
#!/bin/bash
# .git/hooks/pre-commit
cd tests && ./run_tests.sh
```
