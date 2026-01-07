#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest configuration and fixtures for ARM Flash Programming Tool tests
"""

import pytest
import sys
import tempfile
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Add local PyOCD to path (same as main.py does)
LOCAL_PYOCD_PATH = PROJECT_ROOT / "Driver" / "pyOCD"
if LOCAL_PYOCD_PATH.exists():
    sys.path.insert(0, str(LOCAL_PYOCD_PATH))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_chip_config_dict():
    """Sample chip configuration dictionary"""
    return {
        "name": "Test STM32F4",
        "vendor": "STMicroelectronics",
        "chip_family": "STM32F4",
        "target": "stm32f407vg",
        "flash_start": 0x08000000,
        "flash_size": 1024 * 1024,  # 1 MB
        "ram_start": 0x20000000,
        "ram_size": 192 * 1024,  # 192 KB
        "default_frequency": 2000000,
        "connect_mode": "under-reset",
        "reset_type": "default",
        "pack_file": "",
        "options": {},
        "description": "Test configuration for STM32F407VG",
        "notes": ""
    }


@pytest.fixture
def sample_chip_config_json(temp_dir, sample_chip_config_dict):
    """Create a sample chip config JSON file"""
    config_file = temp_dir / "test_chip.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(sample_chip_config_dict, f, indent=2)
    return config_file


@pytest.fixture
def sample_multi_preset_json(temp_dir):
    """Create a JSON file with multiple presets"""
    presets = {
        "preset_stm32f1": {
            "name": "STM32F1 Test",
            "vendor": "STMicroelectronics",
            "chip_family": "STM32F1",
            "target": "stm32f103c8",
            "flash_start": 0x08000000,
            "default_frequency": 1000000,
            "connect_mode": "under-reset"
        },
        "preset_nrf52": {
            "name": "nRF52 Test",
            "vendor": "Nordic",
            "chip_family": "nRF52",
            "target": "nrf52832",
            "flash_start": 0x00000000,
            "default_frequency": 1000000,
            "connect_mode": "halt"
        }
    }
    config_file = temp_dir / "multi_presets.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=2)
    return config_file


@pytest.fixture
def invalid_json_file(temp_dir):
    """Create an invalid JSON file"""
    invalid_file = temp_dir / "invalid.json"
    with open(invalid_file, 'w') as f:
        f.write("{not valid json")
    return invalid_file


@pytest.fixture
def sample_hex_file(temp_dir):
    """Create a sample Intel HEX file"""
    hex_content = """:020000040800F2
:10000000000400208D010008910100089301000861
:10001000950100089701000899010008000000004F
:040000050800009550
:00000001FF
"""
    hex_file = temp_dir / "test_firmware.hex"
    with open(hex_file, 'w') as f:
        f.write(hex_content)
    return hex_file


@pytest.fixture
def sample_bin_file(temp_dir):
    """Create a sample binary file"""
    bin_file = temp_dir / "test_firmware.bin"
    # Write some test data
    with open(bin_file, 'wb') as f:
        f.write(b'\x00\x04\x00\x20' + b'\x00' * 1020)  # 1KB test file
    return bin_file
