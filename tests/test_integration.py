#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the overall application
Tests cross-module interactions and data flow
"""

import pytest
from pathlib import Path
import json
import tempfile
import os

# Import after setting up path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_project_root():
    return Path(__file__).parent.parent


class TestProjectStructure:
    """Tests for project structure integrity"""
    
    @pytest.fixture
    def project_root(self):
        return get_project_root()
    
    def test_all_required_modules_exist(self, project_root):
        """Test all required modules exist"""
        required_modules = [
            'Core/__init__.py',
            'Core/chip_config.py',
            'Core/config.py',
            'Core/logger.py',
            'Core/pack_parser.py',
            'Core/pyocd_wrapper.py',
            'Core/utils.py',
            'UI/__init__.py',
            'UI/main_window.py',
            'UI/flash_page.py',
            'UI/erase_page.py',
            'UI/settings_page.py',
        ]
        
        for module in required_modules:
            filepath = project_root / module
            assert filepath.exists(), f"Required module {module} is missing"
    
    def test_main_entry_point_exists(self, project_root):
        """Test main.py entry point exists"""
        main_py = project_root / 'main.py'
        assert main_py.exists(), "main.py should exist"
        
        content = main_py.read_text(encoding='utf-8')
        assert 'if __name__' in content, "main.py should have entry point"
    
    def test_requirements_file_exists(self, project_root):
        """Test requirements.txt exists"""
        req_file = project_root / 'requirements.txt'
        assert req_file.exists(), "requirements.txt should exist"
        
        content = req_file.read_text(encoding='utf-8')
        # Check for key dependencies
        assert 'pyocd' in content.lower() or 'PyOCD' in content
        assert 'pyqt' in content.lower() or 'PyQt6' in content
    
    def test_config_json_has_valid_structure(self, project_root):
        """Test config.json has valid JSON structure"""
        config_file = project_root / 'config.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                try:
                    config = json.load(f)
                    assert isinstance(config, dict), "config.json should be a JSON object"
                except json.JSONDecodeError as e:
                    pytest.fail(f"config.json is not valid JSON: {e}")


class TestChipConfigIntegration:
    """Integration tests for chip config workflow"""
    
    def test_create_and_export_preset(self, tmp_path):
        """Test creating a preset and exporting it"""
        from Core.chip_config import ChipConfig, ChipConfigManager, ChipVendor
        
        # Create a config with all required fields
        config = ChipConfig(
            name="Test Chip",
            target="stm32f103c8",
            vendor=ChipVendor.ST.value,
            chip_family="STM32F1",
            flash_start=0x08000000,
            flash_size=0x10000,
            ram_size=0x5000,
        )
        
        # Create manager
        manager = ChipConfigManager()
        
        # Add preset with a key
        preset_key = "test_chip_stm32f1"
        manager.add_user_preset(preset_key, config)
        
        # Export it
        export_path = tmp_path / "exported.json"
        result = manager.export_preset(preset_key, export_path)
        assert result is True
        assert export_path.exists()
        
        # Verify exported content
        with open(export_path, 'r', encoding='utf-8') as f:
            exported = json.load(f)
        
        assert exported['name'] == "Test Chip"
        assert exported['target'] == "stm32f103c8"
        
        # Cleanup
        manager.delete_user_preset(preset_key)
    
    def test_import_and_use_preset(self, tmp_path):
        """Test importing a preset and using it"""
        from Core.chip_config import ChipConfigManager
        
        # Create a JSON file to import
        preset_data = {
            "name": "Imported Chip",
            "target": "nrf52840",
            "vendor": "Nordic",
            "chip_family": "nRF52",
            "flash_start": "0x00000000",
            "flash_size": "0x100000",
            "ram_size": "0x40000",
        }
        
        import_file = tmp_path / "import.json"
        with open(import_file, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f)
        
        # Import it
        manager = ChipConfigManager()
        result_key = manager.import_preset(import_file)
        
        # import_preset returns the key (string) if successful
        assert result_key is not None
        assert isinstance(result_key, str)
        
        # Get the imported config by key
        config = manager.get_preset(result_key)
        assert config is not None
        assert config.name == "Imported Chip"
        assert config.target == "nrf52840"
        
        # Cleanup
        manager.delete_user_preset(result_key)


class TestUtilsIntegration:
    """Integration tests for utils with other modules"""
    
    def test_address_parsing_with_chip_config(self):
        """Test address parsing works with ChipConfig"""
        from Core.utils import parse_address, format_address
        from Core.chip_config import ChipConfig, ChipVendor
        
        # Parse address from string
        addr = parse_address("0x08000000")
        
        # Create config with parsed address
        config = ChipConfig(
            name="Test",
            target="stm32f103c8",
            vendor=ChipVendor.ST.value,  # Use .value to get string
            chip_family="STM32F1",
            flash_start=addr,
        )
        
        assert config.flash_start == 0x08000000
        assert format_address(config.flash_start) == "0x08000000"
    
    def test_frequency_conversion_round_trip(self):
        """Test frequency conversion is consistent"""
        from Core.utils import freq_index_to_hz, freq_hz_to_index, FREQUENCY_OPTIONS
        
        for i, (name, hz) in enumerate(FREQUENCY_OPTIONS):
            # Convert index -> Hz -> index
            converted_hz = freq_index_to_hz(i)
            back_to_index = freq_hz_to_index(converted_hz)
            
            assert back_to_index == i, f"Round trip failed for {name}"
    
    def test_vendor_detection_with_preset_targets(self):
        """Test vendor detection works with builtin presets"""
        from Core.utils import detect_vendor
        from Core.chip_config import BUILTIN_PRESETS
        
        # Check a few builtin presets (they are ChipConfig objects)
        preset_list = list(BUILTIN_PRESETS.values())[:5]
        for preset in preset_list:
            # preset is a ChipConfig object
            target = preset.target if hasattr(preset, 'target') else ''
            vendor = detect_vendor(target)
            
            # Should return a non-empty string
            assert isinstance(vendor, str)
            assert len(vendor) > 0


class TestPackParserIntegration:
    """Integration tests for pack parser"""
    
    @pytest.fixture
    def project_root(self):
        return get_project_root()
    
    def test_pack_directory_structure(self, project_root):
        """Test pack directory exists and has expected structure"""
        pack_dir = project_root / 'Package'
        
        if pack_dir.exists():
            # Should have vendor subdirectories or pack files
            contents = list(pack_dir.iterdir())
            assert len(contents) > 0, "Package directory should not be empty"
    
    def test_pack_parser_handles_missing_file(self, tmp_path):
        """Test PackParser handles missing file gracefully"""
        from Core.pack_parser import PackParser
        
        parser = PackParser(str(tmp_path / "nonexistent.pack"))
        # parse() should return None for missing file
        result = parser.parse()
        assert result is None
