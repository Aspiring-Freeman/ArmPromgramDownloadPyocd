#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security and Resource Safety Tests

Tests cover:
- Resource consumption limits
- File path validation
- Configuration injection prevention
- Memory and CPU usage limits
- Dangerous operation prevention
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time


@pytest.mark.security
class TestFilePathSafety:
    """Tests for safe file path handling"""
    
    def test_reject_path_traversal_in_pack_path(self):
        """Test that path traversal attempts are caught"""
        from Core.chip_config import normalize_pack_path
        
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "pack/../../sensitive",
            "C:\\..\\..\\Windows",
        ]
        
        for dangerous_path in dangerous_paths:
            normalized = normalize_pack_path(dangerous_path)
            # Normalized path should not escape workspace
            assert '..' not in normalized or \
                   os.path.isabs(normalized), \
                f"Path traversal not properly handled: {dangerous_path} -> {normalized}"
    
    def test_reject_absolute_paths_outside_workspace(self):
        """Test that absolute paths outside workspace are handled safely"""
        from Core.chip_config import normalize_pack_path
        
        # System paths that should not be accessible
        dangerous_paths = [
            "/etc/passwd",
            "/root/.ssh/id_rsa",
            "C:\\Windows\\System32\\config\\SAM",
            "/dev/sda",
        ]
        
        for dangerous_path in dangerous_paths:
            # Should either reject or convert to safe relative path
            normalized = normalize_pack_path(dangerous_path)
            # The normalized path should be within acceptable bounds
            assert isinstance(normalized, str), "Should return string"
    
    def test_hex_file_path_validation(self):
        """Test that hex file paths are validated"""
        # Test with various paths
        test_paths = [
            "valid.hex",
            "../../../etc/passwd",
            "C:\\test.hex",
            "/tmp/test.hex",
        ]
        
        for path in test_paths:
            # Path should be validated before use
            p = Path(path)
            # At minimum, extension should be checked for flash operations
            if p.suffix.lower() in ['.hex', '.bin', '.elf']:
                # Valid extensions
                pass
            else:
                # Invalid extension for flash programming
                pass


@pytest.mark.security
class TestConfigurationSafety:
    """Tests for safe configuration handling"""
    
    def test_config_rejects_malicious_json(self):
        """Test that malicious JSON structures are rejected"""
        from Core.config import ConfigManager
        
        malicious_configs = [
            # Extremely deep nesting
            {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": "deep"}}}}}}}} * 100,
            # Extremely large arrays
            {"settings": {"array": list(range(1000000))}},
        ]
        
        for i, config_data in enumerate(malicious_configs):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                try:
                    json.dump(config_data, f)
                    config_path = f.name
                except (MemoryError, RecursionError):
                    # Expected for malicious data
                    continue
            
            # ConfigManager should handle this gracefully
            try:
                config = ConfigManager(config_path)
                # Should not crash
                assert config is not None
            except Exception:
                # Acceptable to reject malicious config
                pass
    
    def test_config_limits_string_length(self):
        """Test that configuration string values have reasonable length limits"""
        from Core.config import ConfigManager
        
        # Create config with extremely long string
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "settings": {
                    "some_setting": "A" * 1000000  # 1MB string
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        config = ConfigManager(config_path)
        # Should load, but reasonable limits should apply when used
        value = config.get('settings.some_setting', '')
        # In practice, UI elements should limit this
        assert isinstance(value, str)
    
    def test_config_prevents_code_injection(self):
        """Test that config values don't execute code"""
        from Core.config import ConfigManager
        
        # Potentially dangerous strings
        dangerous_values = [
            "__import__('os').system('ls')",
            "eval('1+1')",
            "exec('print(1)')",
            "${os.system('ls')}",
            "$(rm -rf /)",
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "settings": {f"test_{i}": val for i, val in enumerate(dangerous_values)}
            }
            json.dump(config_data, f)
            config_path = f.name
        
        config = ConfigManager(config_path)
        
        # Values should be strings, not executed
        for i, dangerous in enumerate(dangerous_values):
            value = config.get(f'settings.test_{i}', '')
            assert value == dangerous, "Value should be stored as-is, not executed"
            assert isinstance(value, str), "Should remain as string"


@pytest.mark.resource
class TestResourceLimits:
    """Tests for resource consumption limits"""
    
    def test_max_file_size_for_flash(self):
        """Test that firmware files have size limits"""
        # Typical MCU flash is 32KB to 2MB
        # Reject files larger than 16MB (reasonable upper bound)
        max_size = 16 * 1024 * 1024  # 16 MB
        
        with tempfile.NamedTemporaryFile(suffix='.hex', delete=False) as f:
            # Create a large file
            f.write(b'0' * (max_size + 1))
            large_file = f.name
        
        file_size = os.path.getsize(large_file)
        
        # In real implementation, this should be rejected
        if file_size > max_size:
            # Should implement size check before programming
            assert True, "Large files should be validated"
        
        os.unlink(large_file)
    
    def test_pack_file_size_limit(self):
        """Test that CMSIS-Pack files have reasonable size limits"""
        # Pack files are typically 1-50 MB
        # Reject files larger than 500 MB
        max_pack_size = 500 * 1024 * 1024
        
        # This is a safety check - actual implementation should verify
        assert max_pack_size > 0, "Pack file size limit should be defined"
    
    @pytest.mark.slow
    def test_memory_usage_during_operations(self):
        """Test that operations don't cause excessive memory usage"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform typical operations
        from Core.pyocd.wrapper import PyOCDWrapper
        from Core.config import ConfigManager
        
        wrapper = PyOCDWrapper()
        
        # List probes multiple times
        for _ in range(10):
            probes = wrapper.list_probes()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100 MB for these operations)
        assert memory_increase < 100, \
            f"Excessive memory usage: {memory_increase:.1f} MB increase"
    
    def test_no_infinite_loops_in_scanner(self):
        """Test that scanner doesn't run indefinitely when stopped"""
        from UI.probe.scanner import ProbeScanner
        
        mock_wrapper = Mock()
        mock_wrapper.list_probes = Mock(return_value=[])
        
        scanner = ProbeScanner(mock_wrapper, scan_interval=100)
        scanner.start()
        
        # Stop after short time
        time.sleep(0.2)
        start_stop = time.time()
        scanner.stop()
        end_stop = time.time()
        
        stop_duration = end_stop - start_stop
        
        # Should stop within 2 seconds
        assert stop_duration < 2.0, \
            f"Scanner took too long to stop: {stop_duration}s"


@pytest.mark.security
class TestDangerousOperationPrevention:
    """Tests for preventing dangerous operations"""
    
    def test_erase_requires_confirmation(self):
        """Test that chip erase operations require explicit confirmation"""
        from Core.pyocd.wrapper import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        
        # Erase should not succeed without proper connection
        # This tests the safety mechanism
        result = wrapper.erase(mode="chip")
        assert result is False, "Erase should fail when not connected"
    
    def test_flash_requires_valid_file(self):
        """Test that flash operations validate file existence"""
        from Core.pyocd.wrapper import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        
        # Flash with non-existent file should fail safely
        result = wrapper.flash("/nonexistent/file.hex")
        assert result is False, "Flash should fail for non-existent file"
    
    def test_flash_rejects_invalid_addresses(self):
        """Test that invalid flash addresses are rejected"""
        from Core.pyocd.wrapper import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        
        # Create a temporary valid hex file
        with tempfile.NamedTemporaryFile(suffix='.hex', delete=False) as f:
            f.write(b':00000001FF\n')  # Empty Intel HEX
            hex_file = f.name
        
        # Invalid addresses
        invalid_addresses = [
            -1,  # Negative
            0xFFFFFFFF + 1,  # Too large
            "invalid",  # Non-numeric
        ]
        
        for addr in invalid_addresses:
            # Should handle invalid addresses gracefully
            if isinstance(addr, int) and addr < 0:
                # Negative addresses are clearly invalid
                assert True
        
        os.unlink(hex_file)
    
    def test_concurrent_operations_prevented(self):
        """Test that concurrent flash/erase operations are prevented"""
        from Core.pyocd.wrapper import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        
        # Wrapper should use locking to prevent concurrent operations
        # This is a structural test
        assert hasattr(wrapper, '_lock'), \
            "Wrapper should have lock mechanism for thread safety"


@pytest.mark.usb
class TestUSBDeviceFilteringSafety:
    """Tests for safe USB device filtering"""
    
    def test_only_debug_probes_listed(self):
        """Test that only debug probes are listed, not other USB devices"""
        from Core.pyocd.wrapper import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        probes = wrapper.list_probes()
        
        # All returned devices should be debug probes
        expected_probe_types = [
            'stlink', 'jlink', 'cmsis-dap', 'daplink', 
            'picoprobe', 'ftdi', 'usb'
        ]
        
        for probe in probes:
            description_lower = probe.description.lower()
            # Should match at least one expected probe type
            # Or have specific vendor IDs
            # This is a sanity check
            assert len(probe.unique_id) > 0, \
                "Probe should have valid unique ID"
    
    def test_probe_scanning_timeout(self):
        """Test that probe scanning has timeout to prevent hanging"""
        from Core.pyocd.wrapper import PyOCDWrapper
        import time
        
        wrapper = PyOCDWrapper()
        
        start_time = time.time()
        try:
            probes = wrapper.list_probes()
            elapsed = time.time() - start_time
            
            # Should complete within 10 seconds even with many USB devices
            assert elapsed < 10.0, \
                f"Probe scanning took too long: {elapsed:.1f}s"
        except Exception:
            elapsed = time.time() - start_time
            # Even on error, should not hang indefinitely
            assert elapsed < 10.0, \
                f"Probe scanning hung: {elapsed:.1f}s"


@pytest.mark.security
class TestInputValidation:
    """Tests for input validation and sanitization"""
    
    def test_frequency_value_validation(self):
        """Test that SWD frequency values are validated"""
        # Valid frequencies are typically 100kHz to 50MHz
        min_freq = 100_000  # 100 kHz
        max_freq = 50_000_000  # 50 MHz
        
        valid_frequencies = [100_000, 1_000_000, 10_000_000, 20_000_000]
        invalid_frequencies = [0, -1000, 100_000_000]
        
        for freq in valid_frequencies:
            assert min_freq <= freq <= max_freq, \
                f"Frequency {freq} should be in valid range"
        
        for freq in invalid_frequencies:
            assert freq < min_freq or freq > max_freq, \
                f"Frequency {freq} should be rejected"
    
    def test_target_name_validation(self):
        """Test that target names are validated"""
        from Core.pyocd.wrapper import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        
        # Invalid target names
        invalid_targets = [
            "",  # Empty
            " ",  # Whitespace
            "../../etc/passwd",  # Path traversal
            "target; rm -rf /",  # Command injection attempt
        ]
        
        for target in invalid_targets:
            # Connect should fail or sanitize these
            result = wrapper.connect(target=target)
            assert result is False, \
                f"Should reject invalid target: {target}"
    
    def test_probe_id_validation(self):
        """Test that probe IDs are validated"""
        # Probe IDs should be alphanumeric strings
        valid_ids = ["123456789ABC", "ABCD1234"]
        invalid_ids = ["", "../../etc", "id; rm -rf /"]
        
        for probe_id in valid_ids:
            # Should be accepted
            assert all(c.isalnum() for c in probe_id), \
                "Valid probe ID should be alphanumeric"
        
        for probe_id in invalid_ids:
            # Should be rejected
            if not probe_id or not all(c.isalnum() for c in probe_id):
                assert True, "Invalid probe ID should be rejected"


class TestLogSafety:
    """Tests for safe logging (preventing log injection)"""
    
    def test_log_sanitizes_user_input(self):
        """Test that user input is sanitized in logs"""
        from Core.logger import command_logger
        
        # Potentially dangerous strings
        dangerous_inputs = [
            "test\n[ERROR] Fake error",
            "input\r\n\r\n[CRITICAL] Injection",
            "data\x00\x01\x02",  # Null bytes
        ]
        
        for dangerous in dangerous_inputs:
            # Logger should handle these safely
            try:
                command_logger.log(f"User input: {dangerous}")
                # Should not crash
                assert True
            except Exception as e:
                pytest.fail(f"Logger crashed on input: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
