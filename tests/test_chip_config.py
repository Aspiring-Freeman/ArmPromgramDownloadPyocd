#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Core/chip_config.py
Tests ChipConfig dataclass, ChipConfigManager, and preset handling
"""

import pytest
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from Core.chip_config import (
    ChipConfig,
    ChipConfigManager,
    ChipVendor,
    BUILTIN_PRESETS,
    get_default_flash_start,
)


class TestChipConfig:
    """Tests for ChipConfig dataclass"""
    
    def test_create_chip_config_with_defaults(self):
        """Test creating ChipConfig with minimal required fields"""
        config = ChipConfig(
            name="Test Config",
            vendor="TestVendor",
            chip_family="TestFamily",
            target="test_target"
        )
        
        # Check defaults
        assert config.flash_start == 0x08000000
        assert config.ram_start == 0x20000000
        assert config.default_frequency == 1000000
        assert config.connect_mode == "under-reset"
        assert config.reset_type == "default"
        assert config.options == {}
    
    def test_create_chip_config_with_all_fields(self, sample_chip_config_dict):
        """Test creating ChipConfig with all fields specified"""
        config = ChipConfig.from_dict(sample_chip_config_dict)
        
        assert config.name == "Test STM32F4"
        assert config.vendor == "STMicroelectronics"
        assert config.target == "stm32f407vg"
        assert config.flash_start == 0x08000000
        assert config.flash_size == 1024 * 1024
        assert config.default_frequency == 2000000
    
    def test_chip_config_to_dict(self, sample_chip_config_dict):
        """Test converting ChipConfig to dictionary"""
        config = ChipConfig.from_dict(sample_chip_config_dict)
        result = config.to_dict()
        
        assert result['name'] == sample_chip_config_dict['name']
        assert result['target'] == sample_chip_config_dict['target']
        assert result['flash_start'] == sample_chip_config_dict['flash_start']
    
    def test_chip_config_from_dict_with_string_addresses(self):
        """Test ChipConfig handles string addresses correctly"""
        data = {
            "name": "Test",
            "vendor": "Test",
            "chip_family": "Test",
            "target": "test_target",
            "flash_start": "0x08000000",  # String hex
            "ram_start": "536870912"  # String decimal (0x20000000)
        }
        config = ChipConfig.from_dict(data)
        
        assert config.flash_start == 0x08000000
        assert config.ram_start == 0x20000000
    
    def test_chip_config_from_dict_validates_target(self):
        """Test that missing or empty target raises ValueError"""
        with pytest.raises(ValueError, match="'target' field is required"):
            ChipConfig.from_dict({
                "name": "Test",
                "vendor": "Test",
                "chip_family": "Test",
                "target": ""  # Empty target
            })
    
    def test_chip_config_from_dict_validates_flash_start_range(self):
        """Test flash_start validation for out of range values"""
        with pytest.raises(ValueError, match="flash_start out of range"):
            ChipConfig.from_dict({
                "name": "Test",
                "vendor": "Test", 
                "chip_family": "Test",
                "target": "test",
                "flash_start": 0x1FFFFFFFF  # Out of 32-bit range
            })
    
    def test_chip_config_from_dict_validates_connect_mode(self):
        """Test invalid connect_mode defaults to 'under-reset'"""
        config = ChipConfig.from_dict({
            "name": "Test",
            "vendor": "Test",
            "chip_family": "Test",
            "target": "test",
            "connect_mode": "invalid_mode"
        })
        assert config.connect_mode == "under-reset"
    
    def test_chip_config_from_dict_validates_frequency(self):
        """Test out-of-range frequency defaults to 1MHz"""
        config = ChipConfig.from_dict({
            "name": "Test",
            "vendor": "Test",
            "chip_family": "Test",
            "target": "test",
            "default_frequency": 100000000  # 100 MHz - too high
        })
        assert config.default_frequency == 1000000
    
    def test_chip_config_from_dict_handles_legacy_configs(self):
        """Test handling of older config formats with missing fields"""
        # Minimal legacy config
        legacy_config = {
            "target": "legacy_target"
        }
        config = ChipConfig.from_dict(legacy_config)
        
        assert config.target == "legacy_target"
        assert config.name == "Unknown"  # Default
        assert config.flash_start == 0x08000000  # Default


class TestChipVendor:
    """Tests for ChipVendor enum"""
    
    def test_vendor_enum_values(self):
        """Test that all expected vendors are defined"""
        assert ChipVendor.ST.value == "STMicroelectronics"
        assert ChipVendor.GD.value == "GigaDevice"
        assert ChipVendor.NORDIC.value == "Nordic"
        assert ChipVendor.NXP.value == "NXP"
        assert ChipVendor.UNKNOWN.value == "Unknown"


class TestBuiltinPresets:
    """Tests for built-in chip presets"""
    
    def test_builtin_presets_not_empty(self):
        """Test that builtin presets exist"""
        assert len(BUILTIN_PRESETS) > 0
    
    def test_builtin_presets_have_valid_structure(self):
        """Test all builtin presets have required fields"""
        for key, preset in BUILTIN_PRESETS.items():
            assert isinstance(preset, ChipConfig)
            assert preset.name, f"Preset {key} missing name"
            assert preset.target, f"Preset {key} missing target"
            assert preset.vendor, f"Preset {key} missing vendor"
    
    def test_stm32_presets_have_correct_flash_start(self):
        """Test STM32 presets use 0x08000000 flash start"""
        stm32_presets = [k for k in BUILTIN_PRESETS if k.startswith('stm32')]
        for key in stm32_presets:
            assert BUILTIN_PRESETS[key].flash_start == 0x08000000, \
                f"Preset {key} has wrong flash_start"
    
    def test_nxp_lpc_presets_have_correct_flash_start(self):
        """Test NXP LPC presets use 0x00000000 flash start"""
        if 'lpc1768' in BUILTIN_PRESETS:
            assert BUILTIN_PRESETS['lpc1768'].flash_start == 0x00000000
    
    def test_nxp_imxrt_presets_have_correct_flash_start(self):
        """Test NXP i.MX RT presets use 0x60000000 (FlexSPI) flash start"""
        if 'mimxrt1060' in BUILTIN_PRESETS:
            assert BUILTIN_PRESETS['mimxrt1060'].flash_start == 0x60000000


class TestChipConfigManager:
    """Tests for ChipConfigManager"""
    
    def test_manager_creation(self, temp_dir):
        """Test creating a ChipConfigManager"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        assert manager is not None
    
    def test_get_all_presets_includes_builtin(self, temp_dir):
        """Test get_all_presets includes builtin presets"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        all_presets = manager.get_all_presets()
        
        # Should include all builtin presets
        for key in BUILTIN_PRESETS:
            assert key in all_presets
    
    def test_get_builtin_presets(self, temp_dir):
        """Test get_builtin_presets returns only builtin"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        builtin = manager.get_builtin_presets()
        
        assert len(builtin) == len(BUILTIN_PRESETS)
    
    def test_get_user_presets_initially_empty(self, temp_dir):
        """Test user presets are empty by default"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        user_presets = manager.get_user_presets()
        
        assert len(user_presets) == 0
    
    def test_add_user_preset(self, temp_dir):
        """Test adding a user preset"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        
        new_preset = ChipConfig(
            name="My Custom Board",
            vendor="Custom",
            chip_family="CUSTOM",
            target="custom_target"
        )
        manager.add_user_preset("my_custom", new_preset)
        
        # Verify it was added
        retrieved = manager.get_preset("my_custom")
        assert retrieved is not None
        assert retrieved.name == "My Custom Board"
    
    def test_user_preset_persists(self, temp_dir):
        """Test that user presets are saved to disk"""
        config_dir = temp_dir / "chip_configs"
        
        # Add a preset
        manager1 = ChipConfigManager(config_dir=config_dir)
        manager1.add_user_preset("persist_test", ChipConfig(
            name="Persist Test",
            vendor="Test",
            chip_family="TEST",
            target="persist_target"
        ))
        
        # Create new manager instance (should load from disk)
        manager2 = ChipConfigManager(config_dir=config_dir)
        retrieved = manager2.get_preset("persist_test")
        
        assert retrieved is not None
        assert retrieved.name == "Persist Test"
    
    def test_delete_user_preset(self, temp_dir):
        """Test deleting a user preset"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        
        # Add then delete
        manager.add_user_preset("to_delete", ChipConfig(
            name="Delete Me",
            vendor="Test",
            chip_family="TEST",
            target="delete_target"
        ))
        
        result = manager.delete_user_preset("to_delete")
        assert result is True
        assert manager.get_preset("to_delete") is None
    
    def test_delete_nonexistent_preset_returns_false(self, temp_dir):
        """Test deleting nonexistent preset returns False"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        result = manager.delete_user_preset("nonexistent")
        assert result is False
    
    def test_get_presets_by_vendor(self, temp_dir):
        """Test filtering presets by vendor"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        st_presets = manager.get_presets_by_vendor("STMicroelectronics")
        
        assert len(st_presets) > 0
        for preset in st_presets.values():
            assert preset.vendor == "STMicroelectronics"
    
    def test_get_vendors(self, temp_dir):
        """Test getting list of all vendors"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        vendors = manager.get_vendors()
        
        assert len(vendors) > 0
        assert "STMicroelectronics" in vendors
    
    def test_export_preset(self, temp_dir, sample_chip_config_dict):
        """Test exporting a preset to JSON file"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        
        # Add a preset first
        manager.add_user_preset("export_test", ChipConfig.from_dict(sample_chip_config_dict))
        
        # Export it
        export_path = temp_dir / "exported.json"
        result = manager.export_preset("export_test", export_path)
        
        assert result is True
        assert export_path.exists()
        
        # Verify content
        with open(export_path, 'r') as f:
            exported = json.load(f)
        assert exported['name'] == sample_chip_config_dict['name']
    
    def test_import_single_preset(self, temp_dir, sample_chip_config_json):
        """Test importing a single preset from JSON file"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        
        key = manager.import_preset(sample_chip_config_json)
        
        assert key is not None
        imported = manager.get_preset(key)
        assert imported is not None
        assert imported.target == "stm32f407vg"
    
    def test_import_multiple_presets(self, temp_dir, sample_multi_preset_json):
        """Test importing multiple presets from JSON file"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        
        key = manager.import_preset(sample_multi_preset_json)
        
        assert key is not None
        # Both presets should be imported
        assert manager.get_preset("preset_stm32f1") is not None
        assert manager.get_preset("preset_nrf52") is not None
    
    def test_import_invalid_json_returns_none(self, temp_dir, invalid_json_file):
        """Test importing invalid JSON returns None"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        
        key = manager.import_preset(invalid_json_file)
        assert key is None
    
    def test_create_config_from_current(self, temp_dir):
        """Test creating config from current settings"""
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        
        config = manager.create_config_from_current(
            name="Runtime Created",
            target="stm32f411ce",
            vendor="STMicroelectronics",
            flash_start=0x08000000,
            frequency=2000000,
            connect_mode="halt"
        )
        
        assert config.name == "Runtime Created"
        assert config.target == "stm32f411ce"
        assert config.default_frequency == 2000000
        assert config.connect_mode == "halt"


class TestGetDefaultFlashStart:
    """Tests for get_default_flash_start function"""
    
    def test_stm32_flash_start(self):
        """Test STM32 family uses 0x08000000"""
        assert get_default_flash_start("stm32f103") == 0x08000000
        assert get_default_flash_start("STM32H7") == 0x08000000
    
    def test_gd32_flash_start(self):
        """Test GD32 family uses 0x08000000 (STM32 compatible)"""
        assert get_default_flash_start("gd32f103") == 0x08000000
    
    def test_nrf_flash_start(self):
        """Test Nordic nRF uses 0x00000000"""
        assert get_default_flash_start("nrf52832") == 0x00000000
        assert get_default_flash_start("Nordic") == 0x00000000
    
    def test_nxp_lpc_flash_start(self):
        """Test NXP LPC uses 0x00000000"""
        assert get_default_flash_start("lpc1768") == 0x00000000
        assert get_default_flash_start("NXP") == 0x00000000
    
    def test_nxp_imxrt_flash_start(self):
        """Test NXP i.MX RT uses 0x60000000 (FlexSPI)"""
        assert get_default_flash_start("mimxrt1060") == 0x60000000
    
    def test_unknown_defaults_to_stm32_style(self):
        """Test unknown vendor defaults to 0x08000000"""
        assert get_default_flash_start("unknown") == 0x08000000


class TestEdgeCases:
    """Edge case and error handling tests"""
    
    def test_chip_config_handles_none_options(self):
        """Test ChipConfig handles None in options field"""
        data = {
            "name": "Test",
            "vendor": "Test",
            "chip_family": "Test",
            "target": "test",
            "options": None
        }
        # Should not raise
        config = ChipConfig.from_dict(data)
        # Options should be empty dict or None handled gracefully
        assert config is not None
    
    def test_manager_handles_corrupted_config_file(self, temp_dir):
        """Test manager handles corrupted user config file"""
        config_dir = temp_dir / "chip_configs"
        config_dir.mkdir(parents=True)
        
        # Write corrupted config
        config_file = config_dir / "user_configs.json"
        with open(config_file, 'w') as f:
            f.write("not valid json {{{")
        
        # Should not raise, just log error and start with empty configs
        manager = ChipConfigManager(config_dir=config_dir)
        assert len(manager.get_user_presets()) == 0
    
    def test_import_empty_file(self, temp_dir):
        """Test importing empty JSON object"""
        empty_file = temp_dir / "empty.json"
        with open(empty_file, 'w') as f:
            json.dump({}, f)
        
        manager = ChipConfigManager(config_dir=temp_dir / "chip_configs")
        key = manager.import_preset(empty_file)
        
        # Empty object should return None (no valid presets)
        assert key is None
