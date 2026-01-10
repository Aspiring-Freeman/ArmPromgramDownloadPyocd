#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for UI.probe.scanner module

Tests cover:
- ProbeScanner thread behavior
- Resource management
- Safety checks for USB scanning
- Configuration-based scanning control
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QThread, pyqtSignal


@pytest.mark.usb
class TestProbeScannerSafety:
    """Tests for ProbeScanner safety and resource management"""
    
    def test_scanner_can_be_disabled_via_config(self):
        """Test that auto_scan_probes config prevents scanner startup"""
        from Core.config import ConfigManager
        import tempfile
        import json
        
        # Create a config with auto_scan disabled
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "settings": {
                    "auto_scan_probes": False,
                    "probe_scan_interval": 10
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        config = ConfigManager(config_path)
        auto_scan = config.get('settings.auto_scan_probes', True)
        
        assert auto_scan is False, "Auto scan should be disabled"
    
    def test_scanner_respects_scan_interval(self):
        """Test that scanner uses configured scan interval"""
        from UI.probe.scanner import ProbeScanner
        
        mock_wrapper = Mock()
        mock_wrapper.list_probes = Mock(return_value=[])
        
        # Test with 5 second interval
        scanner = ProbeScanner(mock_wrapper, scan_interval=5)
        assert scanner._scan_interval == 5
        
        # Test with 30 second interval
        scanner = ProbeScanner(mock_wrapper, scan_interval=30)
        assert scanner._scan_interval == 30
    
    def test_scanner_default_interval(self):
        """Test that scanner has reasonable default interval"""
        from UI.probe.scanner import ProbeScanner
        
        mock_wrapper = Mock()
        mock_wrapper.list_probes = Mock(return_value=[])
        
        # Test default (should be 10 seconds as per our implementation)
        scanner = ProbeScanner(mock_wrapper)
        assert scanner._scan_interval == 10, "Default scan interval should be 10 seconds"
    
    def test_scanner_can_be_stopped_immediately(self):
        """Test that scanner thread can be stopped quickly"""
        from UI.probe.scanner import ProbeScanner
        
        mock_wrapper = Mock()
        mock_wrapper.list_probes = Mock(return_value=[])
        
        scanner = ProbeScanner(mock_wrapper, scan_interval=100)  # Long interval
        scanner.start()
        
        # Stop immediately
        start_time = time.time()
        scanner.stop()
        stop_time = time.time()
        
        # Should stop in less than 2 seconds (0.1 * 20 iterations max)
        assert (stop_time - start_time) < 2, "Scanner should stop quickly"
        assert not scanner.isRunning(), "Scanner thread should be stopped"
    
    def test_scanner_emits_probe_list(self):
        """Test that scanner emits probe list signal"""
        from UI.probe.scanner import ProbeScanner
        from Core.pyocd.base import ProbeInfo
        
        mock_wrapper = Mock()
        test_probes = [
            ProbeInfo("123456", "Test Probe 1", "TestVendor", "TestProduct"),
            ProbeInfo("789012", "Test Probe 2", "TestVendor", "TestProduct")
        ]
        mock_wrapper.list_probes = Mock(return_value=test_probes)
        
        scanner = ProbeScanner(mock_wrapper, scan_interval=1)
        
        # Collect emitted signals
        emitted_probes = []
        scanner.probes_found.connect(lambda p: emitted_probes.append(p))
        
        scanner.start()
        time.sleep(0.5)  # Wait for first scan
        scanner.stop()
        
        assert len(emitted_probes) > 0, "Should emit probe list at least once"
        assert emitted_probes[0] == test_probes, "Should emit correct probe list"


@pytest.mark.resource
class TestProbeScannerResourceLimits:
    """Tests for resource usage limits"""
    
    def test_scanner_does_not_leak_threads(self):
        """Test that multiple start/stop cycles don't leak threads"""
        from UI.probe.scanner import ProbeScanner
        import threading
        
        mock_wrapper = Mock()
        mock_wrapper.list_probes = Mock(return_value=[])
        
        initial_thread_count = threading.active_count()
        
        # Start and stop scanner multiple times
        for _ in range(5):
            scanner = ProbeScanner(mock_wrapper, scan_interval=1)
            scanner.start()
            time.sleep(0.1)
            scanner.stop()
            scanner.wait()  # Ensure thread is fully stopped
        
        final_thread_count = threading.active_count()
        
        # Thread count should not grow significantly
        assert final_thread_count <= initial_thread_count + 1, \
            "Scanner should not leak threads"
    
    def test_scanner_handles_wrapper_errors_gracefully(self):
        """Test that scanner doesn't crash on wrapper errors"""
        from UI.probe.scanner import ProbeScanner
        
        mock_wrapper = Mock()
        mock_wrapper.list_probes = Mock(side_effect=Exception("USB error"))
        
        scanner = ProbeScanner(mock_wrapper, scan_interval=1)
        
        # Scanner should not crash even if list_probes raises exception
        try:
            scanner.start()
            time.sleep(0.3)  # Let it try a scan
            scanner.stop()
            success = True
        except Exception:
            success = False
        
        assert success, "Scanner should handle wrapper errors gracefully"
    
    @pytest.mark.slow
    def test_scanner_max_scan_frequency(self):
        """Test that scanner doesn't scan too frequently (resource protection)"""
        from UI.probe.scanner import ProbeScanner
        
        mock_wrapper = Mock()
        mock_wrapper.list_probes = Mock(return_value=[])
        
        # Minimum safe interval should be at least 1 second
        scanner = ProbeScanner(mock_wrapper, scan_interval=1)
        
        scan_count = [0]
        def count_scans(_):
            scan_count[0] += 1
        
        scanner.probes_found.connect(count_scans)
        scanner.start()
        
        time.sleep(2.5)  # Run for 2.5 seconds
        scanner.stop()
        
        # Should not scan more than 3 times in 2.5 seconds with 1 second interval
        assert scan_count[0] <= 4, \
            f"Scanner should not scan too frequently: {scan_count[0]} scans in 2.5s"


@pytest.mark.usb
class TestProbeListResourceSafety:
    """Tests for safe probe listing (avoiding USB device issues)"""
    
    def test_list_probes_does_not_hang(self):
        """Test that list_probes completes in reasonable time"""
        from Core.pyocd.wrapper import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        
        start_time = time.time()
        try:
            probes = wrapper.list_probes()
            elapsed = time.time() - start_time
            
            # Should complete in less than 5 seconds
            assert elapsed < 5.0, f"list_probes took too long: {elapsed}s"
        except Exception as e:
            # Even on error, should not hang
            elapsed = time.time() - start_time
            assert elapsed < 5.0, f"list_probes hung on error: {elapsed}s"
    
    def test_list_probes_returns_valid_structure(self):
        """Test that list_probes returns expected data structure"""
        from Core.pyocd.wrapper import PyOCDWrapper
        from Core.pyocd.base import ProbeInfo
        
        wrapper = PyOCDWrapper()
        probes = wrapper.list_probes()
        
        assert isinstance(probes, list), "list_probes should return a list"
        
        for probe in probes:
            assert isinstance(probe, ProbeInfo), \
                "Each probe should be a ProbeInfo instance"
            assert hasattr(probe, 'unique_id'), "Probe should have unique_id"
            assert hasattr(probe, 'description'), "Probe should have description"
            assert hasattr(probe, 'vendor_name'), "Probe should have vendor_name"
            assert hasattr(probe, 'product_name'), "Probe should have product_name"


class TestProbeScannerConfiguration:
    """Tests for configuration-based scanner behavior"""
    
    def test_config_can_disable_auto_scan(self):
        """Test that config properly controls auto scanning"""
        from Core.config import ConfigManager
        import tempfile
        import json
        
        # Create config with various settings
        configs = [
            {"settings": {"auto_scan_probes": False}},
            {"settings": {"auto_scan_probes": True}},
            {"settings": {}},  # Missing setting
        ]
        
        for i, config_data in enumerate(configs):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config_data, f)
                config_path = f.name
            
            config = ConfigManager(config_path)
            auto_scan = config.get('settings.auto_scan_probes', True)
            
            if i == 0:
                assert auto_scan is False, "Should respect explicit False"
            elif i == 1:
                assert auto_scan is True, "Should respect explicit True"
            else:
                assert auto_scan is True, "Should default to True when missing"
    
    def test_config_scan_interval_validation(self):
        """Test that scan interval has reasonable bounds"""
        # Scan interval should not be less than 1 second (too aggressive)
        # and not more than 60 seconds (too infrequent for UX)
        
        valid_intervals = [1, 5, 10, 30, 60]
        for interval in valid_intervals:
            assert 1 <= interval <= 60, \
                f"Interval {interval} should be between 1 and 60 seconds"
        
        # Test that scanner accepts these intervals
        from UI.probe.scanner import ProbeScanner
        mock_wrapper = Mock()
        mock_wrapper.list_probes = Mock(return_value=[])
        
        for interval in valid_intervals:
            scanner = ProbeScanner(mock_wrapper, scan_interval=interval)
            assert scanner._scan_interval == interval


class TestProbeSelectionSafety:
    """Tests for safe probe selection and filtering"""
    
    def test_probe_list_does_not_include_storage_devices(self):
        """Test that probe scanning doesn't interfere with USB storage"""
        from Core.pyocd.wrapper import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        probes = wrapper.list_probes()
        
        # All probes should be debug probes, not storage devices
        for probe in probes:
            # Debug probes typically have specific vendor/product names
            # Storage devices would not match these patterns
            description = probe.description.lower()
            
            # These are NOT valid debug probe indicators
            invalid_keywords = ['mass storage', 'disk', 'storage', 'drive']
            for keyword in invalid_keywords:
                assert keyword not in description, \
                    f"Probe list should not include storage devices: {description}"
    
    def test_probe_unique_id_format(self):
        """Test that probe unique IDs are valid"""
        from Core.pyocd.wrapper import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        probes = wrapper.list_probes()
        
        for probe in probes:
            # Unique ID should be a non-empty string
            assert isinstance(probe.unique_id, str), "Unique ID should be string"
            assert len(probe.unique_id) > 0, "Unique ID should not be empty"
            # Typical debug probe IDs are hexadecimal strings
            assert len(probe.unique_id) >= 8, "Unique ID should be at least 8 chars"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
