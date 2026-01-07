#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Core.pyocd module

Tests cover:
- Base classes (enums, dataclasses)
- PyOCDWrapper class structure
- Connection/disconnection logic (mocked)
- Flash/erase operation interfaces (mocked)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass


class TestBaseClasses:
    """Tests for Core.pyocd.base module"""
    
    def test_reset_type_enum(self):
        """Test ResetType enum values"""
        from Core.pyocd.base import ResetType
        
        assert ResetType.DEFAULT.value == "default"
        assert ResetType.HARDWARE.value == "hw"
        assert ResetType.SOFTWARE.value == "sw"
        assert ResetType.SYSRESET.value == "sysresetreq"
        assert ResetType.VECTRESET.value == "vectreset"
    
    def test_erase_mode_enum(self):
        """Test EraseMode enum values"""
        from Core.pyocd.base import EraseMode
        
        assert EraseMode.CHIP.value == "chip"
        assert EraseMode.SECTOR.value == "sector"
        assert EraseMode.MASS.value == "mass"
    
    def test_connect_mode_enum(self):
        """Test ConnectMode enum values"""
        from Core.pyocd.base import ConnectMode
        
        assert ConnectMode.HALT.value == "halt"
        assert ConnectMode.PRE_RESET.value == "pre-reset"
        assert ConnectMode.UNDER_RESET.value == "under-reset"
        assert ConnectMode.ATTACH.value == "attach"
    
    def test_probe_info_dataclass(self):
        """Test ProbeInfo dataclass"""
        from Core.pyocd.base import ProbeInfo
        
        probe = ProbeInfo(
            unique_id="12345678901234567890",
            description="STLink V2",
            vendor_name="STMicroelectronics",
            product_name="STLink"
        )
        
        assert probe.unique_id == "12345678901234567890"
        assert probe.description == "STLink V2"
        assert probe.vendor_name == "STMicroelectronics"
        assert probe.product_name == "STLink"
        
        # Test __str__
        assert "STLink V2" in str(probe)
        assert "12345678" in str(probe)  # First 8 chars
    
    def test_flash_region_dataclass(self):
        """Test FlashRegion dataclass"""
        from Core.pyocd.base import FlashRegion
        
        region = FlashRegion(
            start=0x08000000,
            size=128 * 1024,  # 128KB
            sector_size=1024,
            name="Main Flash"
        )
        
        assert region.start == 0x08000000
        assert region.size == 128 * 1024
        assert region.sector_size == 1024
        assert region.name == "Main Flash"
        
        # Test end property
        assert region.end == 0x08000000 + 128 * 1024
        
        # Test __str__
        region_str = str(region)
        assert "Main Flash" in region_str
        assert "0x08000000" in region_str.lower() or "0X08000000" in region_str.upper()
        assert "128KB" in region_str


class TestPyOCDWrapperImports:
    """Tests for Core.pyocd_wrapper backward compatibility imports"""
    
    def test_backward_compat_imports(self):
        """Test that backward compatibility imports work"""
        from Core.pyocd_wrapper import (
            ResetType,
            EraseMode,
            ConnectMode,
            ProbeInfo,
            FlashRegion,
            PyOCDWrapper,
        )
        
        # All should be importable
        assert ResetType is not None
        assert EraseMode is not None
        assert ConnectMode is not None
        assert ProbeInfo is not None
        assert FlashRegion is not None
        assert PyOCDWrapper is not None
    
    def test_new_import_path(self):
        """Test that new import path works"""
        from Core.pyocd import (
            ResetType,
            EraseMode,
            ConnectMode,
            ProbeInfo,
            FlashRegion,
            PyOCDWrapper,
        )
        
        assert ResetType is not None
        assert PyOCDWrapper is not None


class TestPyOCDWrapperStructure:
    """Tests for PyOCDWrapper class structure"""
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_wrapper_init(self, mock_pack_target):
        """Test PyOCDWrapper initialization"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        
        assert wrapper._session is None
        assert wrapper._current_target is None
        assert wrapper._pack_paths == []
        assert wrapper._lock is not None
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_wrapper_init_with_packs(self, mock_pack_target):
        """Test PyOCDWrapper initialization with pack paths"""
        from Core.pyocd import PyOCDWrapper
        
        pack_paths = ["/path/to/pack1.pack", "/path/to/pack2.pack"]
        wrapper = PyOCDWrapper(pack_paths=pack_paths)
        
        assert wrapper._pack_paths == pack_paths
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_is_connected_false_by_default(self, mock_pack_target):
        """Test is_connected property returns False when no session"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        assert wrapper.is_connected is False
    
    @patch('Core.pyocd.wrapper.pack_target')
    @patch('Core.pyocd.wrapper.TARGET', {'stm32f103c8': {}, 'stm32f407vg': {}})
    def test_list_targets(self, mock_pack_target):
        """Test list_targets method"""
        from Core.pyocd import PyOCDWrapper
        
        mock_pack_target.PackTargets.get_targets.return_value = {}
        
        wrapper = PyOCDWrapper()
        targets = wrapper.list_targets()
        
        assert isinstance(targets, list)
        assert 'stm32f103c8' in targets
        assert 'stm32f407vg' in targets
    
    @patch('Core.pyocd.wrapper.pack_target')
    @patch('Core.pyocd.wrapper.TARGET', {'stm32f103c8': {}, 'stm32f407vg': {}, 'gd32f303cg': {}})
    def test_list_targets_with_filter(self, mock_pack_target):
        """Test list_targets method with name filter"""
        from Core.pyocd import PyOCDWrapper
        
        mock_pack_target.PackTargets.get_targets.return_value = {}
        
        wrapper = PyOCDWrapper()
        
        # Filter for stm32
        targets = wrapper.list_targets(name_filter='stm32')
        assert 'stm32f103c8' in targets
        assert 'stm32f407vg' in targets
        assert 'gd32f303cg' not in targets
        
        # Filter for gd32
        targets = wrapper.list_targets(name_filter='gd32')
        assert 'gd32f303cg' in targets
        assert 'stm32f103c8' not in targets
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_context_manager(self, mock_pack_target):
        """Test context manager protocol"""
        from Core.pyocd import PyOCDWrapper
        
        with PyOCDWrapper() as wrapper:
            assert wrapper is not None
            assert wrapper._session is None


class TestConnectionMixin:
    """Tests for connection-related methods"""
    
    @patch('Core.pyocd.wrapper.pack_target')
    @patch('Core.pyocd.connection.ConnectHelper')
    def test_list_probes_empty(self, mock_helper, mock_pack_target):
        """Test list_probes returns empty list when no probes"""
        from Core.pyocd import PyOCDWrapper
        
        mock_helper.get_all_connected_probes.return_value = []
        
        wrapper = PyOCDWrapper()
        probes = wrapper.list_probes()
        
        assert probes == []
    
    @patch('Core.pyocd.wrapper.pack_target')
    @patch('Core.pyocd.connection.ConnectHelper')
    def test_list_probes_found(self, mock_helper, mock_pack_target):
        """Test list_probes returns probe info"""
        from Core.pyocd import PyOCDWrapper, ProbeInfo
        
        mock_probe = Mock()
        mock_probe.unique_id = "123456789012"
        mock_probe.description = "ST-Link V2"
        mock_probe.vendor_name = "STMicroelectronics"
        mock_probe.product_name = "ST-Link"
        
        mock_helper.get_all_connected_probes.return_value = [mock_probe]
        
        wrapper = PyOCDWrapper()
        probes = wrapper.list_probes()
        
        assert len(probes) == 1
        assert isinstance(probes[0], ProbeInfo)
        assert probes[0].unique_id == "123456789012"
        assert probes[0].description == "ST-Link V2"
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_disconnect_without_session(self, mock_pack_target):
        """Test disconnect when no session exists"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        # Should not raise
        wrapper.disconnect()
        assert wrapper._session is None
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_disconnect_force(self, mock_pack_target):
        """Test force disconnect"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        mock_session = Mock()
        wrapper._session = mock_session
        
        wrapper.disconnect(force=True)
        
        mock_session.close.assert_called_once()
        assert wrapper._session is None
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_get_flash_regions_not_connected(self, mock_pack_target):
        """Test get_flash_regions returns empty when not connected"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        regions = wrapper.get_flash_regions()
        
        assert regions == []


class TestFlashMixin:
    """Tests for flash-related methods"""
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_flash_not_connected(self, mock_pack_target):
        """Test flash returns False when not connected"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        result = wrapper.flash("/path/to/file.hex")
        
        assert result is False
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_flash_file_not_connected(self, mock_pack_target):
        """Test flash_file returns False when not connected"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        result = wrapper.flash_file("/path/to/file.hex")
        
        assert result is False


class TestEraseMixin:
    """Tests for erase-related methods"""
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_erase_not_connected(self, mock_pack_target):
        """Test erase returns False when not connected"""
        from Core.pyocd import PyOCDWrapper
        from Core.pyocd.base import EraseMode
        
        wrapper = PyOCDWrapper()
        result = wrapper.erase(mode=EraseMode.CHIP)
        
        assert result is False
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_mass_erase_not_connected(self, mock_pack_target):
        """Test mass_erase returns False when not connected"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        result = wrapper.mass_erase()
        
        assert result is False
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_erase_sector_not_connected(self, mock_pack_target):
        """Test erase_sector returns False when not connected"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        result = wrapper.erase_sector(0)
        
        assert result is False
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_erase_range_not_connected(self, mock_pack_target):
        """Test erase_range returns False when not connected"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        result = wrapper.erase_range(0x08000000, 0x08010000)
        
        assert result is False


class TestResetMixin:
    """Tests for reset-related methods"""
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_reset_not_connected(self, mock_pack_target):
        """Test reset returns False when not connected"""
        from Core.pyocd import PyOCDWrapper
        from Core.pyocd.base import ResetType
        
        wrapper = PyOCDWrapper()
        result = wrapper.reset(reset_type=ResetType.DEFAULT)
        
        assert result is False
    
    @patch('Core.pyocd.wrapper.pack_target')
    def test_reset_with_halt_not_connected(self, mock_pack_target):
        """Test reset with halt returns False when not connected"""
        from Core.pyocd import PyOCDWrapper
        
        wrapper = PyOCDWrapper()
        result = wrapper.reset(halt=True)
        
        assert result is False


class TestProbeUIImports:
    """Tests for UI.probe module backward compatibility"""
    
    def test_probe_page_backward_compat(self):
        """Test backward compatibility imports for probe page"""
        # This should not raise ImportError
        try:
            from UI.probe_page import ProbePage, ProbeScanner, ConnectWorker
            assert ProbePage is not None
            assert ProbeScanner is not None
            assert ConnectWorker is not None
        except ImportError as e:
            pytest.skip(f"PyQt6 not available: {e}")
    
    def test_probe_new_import_path(self):
        """Test new import path for probe module"""
        try:
            from UI.probe import ProbePage, ProbeScanner, ConnectWorker
            assert ProbePage is not None
            assert ProbeScanner is not None
            assert ConnectWorker is not None
        except ImportError as e:
            pytest.skip(f"PyQt6 not available: {e}")
