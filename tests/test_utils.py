#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Core/utils.py
Tests address parsing, frequency conversion, vendor detection, and file utilities
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from Core.utils import (
    # Address utilities
    parse_address,
    format_address,
    is_valid_address,
    validate_flash_address,
    # Frequency utilities
    freq_index_to_hz,
    freq_hz_to_index,
    get_frequency_display_names,
    validate_frequency,
    FREQUENCY_OPTIONS,
    DEFAULT_FREQUENCY,
    # Vendor detection
    detect_vendor,
    detect_chip_family,
    VENDOR_PREFIXES,
    # File utilities
    get_file_type_name,
    get_file_info,
    FILE_TYPE_NAMES,
    # Size formatting
    format_size,
)


class TestAddressParsing:
    """Tests for address parsing utilities"""
    
    def test_parse_hex_address_with_0x_prefix(self):
        """Test parsing hex address with 0x prefix"""
        assert parse_address("0x08000000") == 0x08000000
        assert parse_address("0X08000000") == 0x08000000
        assert parse_address("0x00000000") == 0x00000000
        assert parse_address("0xFFFFFFFF") == 0xFFFFFFFF
    
    def test_parse_hex_address_lowercase(self):
        """Test parsing lowercase hex addresses"""
        assert parse_address("0x08000000") == 0x08000000
        assert parse_address("0xabcdef00") == 0xABCDEF00
    
    def test_parse_decimal_address(self):
        """Test parsing decimal addresses"""
        assert parse_address("134217728") == 134217728  # 0x08000000
        assert parse_address("0") == 0
        assert parse_address("4294967295") == 0xFFFFFFFF
    
    def test_parse_address_with_whitespace(self):
        """Test parsing addresses with leading/trailing whitespace"""
        assert parse_address("  0x08000000  ") == 0x08000000
        assert parse_address("\t0x08000000\n") == 0x08000000
    
    def test_parse_empty_address_returns_default(self):
        """Test empty string returns default value"""
        assert parse_address("") == 0
        assert parse_address("", default=0x08000000) == 0x08000000
        assert parse_address("   ", default=0x20000000) == 0x20000000
    
    def test_parse_invalid_address_raises_error(self):
        """Test invalid addresses raise ValueError"""
        with pytest.raises(ValueError, match="Invalid address format"):
            parse_address("not_an_address")
        with pytest.raises(ValueError, match="Invalid address format"):
            parse_address("0xGGGGGGGG")
        with pytest.raises(ValueError, match="Invalid address format"):
            parse_address("12.34")
    
    def test_format_address_default_width(self):
        """Test formatting address with default 8-digit width"""
        assert format_address(0x08000000) == "0x08000000"
        assert format_address(0x00000000) == "0x00000000"
        assert format_address(0xFFFFFFFF) == "0xFFFFFFFF"
    
    def test_format_address_custom_width(self):
        """Test formatting address with custom width"""
        assert format_address(0x1000, width=4) == "0x1000"
        assert format_address(0x100, width=4) == "0x0100"
        assert format_address(0x1, width=2) == "0x01"
    
    def test_is_valid_address(self):
        """Test address validation"""
        assert is_valid_address("0x08000000") is True
        assert is_valid_address("134217728") is True
        assert is_valid_address("") is True  # Empty is valid (uses default)
        assert is_valid_address("invalid") is False
        assert is_valid_address("0xZZZZ") is False
    
    def test_validate_flash_address_default_range(self):
        """Test flash address validation with default range"""
        assert validate_flash_address(0x00000000) is True
        assert validate_flash_address(0x08000000) is True
        assert validate_flash_address(0xFFFFFFFF) is True
    
    def test_validate_flash_address_custom_range(self):
        """Test flash address validation with custom range"""
        # STM32 flash range
        assert validate_flash_address(
            0x08000000, 
            min_addr=0x08000000, 
            max_addr=0x08100000
        ) is True
        assert validate_flash_address(
            0x07FFFFFF, 
            min_addr=0x08000000, 
            max_addr=0x08100000
        ) is False


class TestFrequencyConversion:
    """Tests for SWD frequency conversion utilities"""
    
    def test_frequency_options_structure(self):
        """Test FREQUENCY_OPTIONS has correct structure"""
        assert len(FREQUENCY_OPTIONS) >= 5
        for freq_hz, display_name in FREQUENCY_OPTIONS:
            assert isinstance(freq_hz, int)
            assert isinstance(display_name, str)
            assert freq_hz > 0
    
    def test_freq_index_to_hz(self):
        """Test converting combo box index to Hz"""
        # Index 0 should be 100 kHz
        assert freq_index_to_hz(0) == 100000
        # Index 2 should be 1 MHz
        assert freq_index_to_hz(2) == 1000000
        # Invalid index returns default
        assert freq_index_to_hz(999) == DEFAULT_FREQUENCY
    
    def test_freq_hz_to_index(self):
        """Test converting Hz to combo box index"""
        assert freq_hz_to_index(100000) == 0
        assert freq_hz_to_index(1000000) == 2
        # Unknown frequency returns default index (2 = 1 MHz)
        assert freq_hz_to_index(999999) == 2
    
    def test_get_frequency_display_names(self):
        """Test getting display names for combo box"""
        names = get_frequency_display_names()
        assert len(names) == len(FREQUENCY_OPTIONS)
        assert "100 kHz" in names
        assert "1 MHz" in names
    
    def test_validate_frequency(self):
        """Test frequency validation"""
        # Valid frequencies
        assert validate_frequency(100000) is True
        assert validate_frequency(1000000) is True
        assert validate_frequency(10000000) is True
        # Edge cases
        assert validate_frequency(10000) is True  # 10 kHz minimum
        assert validate_frequency(50000000) is True  # 50 MHz maximum
        # Invalid frequencies
        assert validate_frequency(9999) is False  # Below minimum
        assert validate_frequency(50000001) is False  # Above maximum


class TestVendorDetection:
    """Tests for vendor detection from target names"""
    
    def test_detect_stm32_vendor(self):
        """Test detecting STMicroelectronics from STM32 targets"""
        assert detect_vendor("stm32f103c8") == "STMicroelectronics"
        assert detect_vendor("STM32F407VG") == "STMicroelectronics"
        assert detect_vendor("stm32h743xi") == "STMicroelectronics"
    
    def test_detect_gd32_vendor(self):
        """Test detecting GigaDevice from GD32 targets"""
        assert detect_vendor("gd32f103c8") == "GigaDevice"
        assert detect_vendor("GD32F303CC") == "GigaDevice"
    
    def test_detect_nordic_vendor(self):
        """Test detecting Nordic from nRF targets"""
        assert detect_vendor("nrf52832") == "Nordic"
        assert detect_vendor("nRF52840") == "Nordic"
    
    def test_detect_nxp_vendor(self):
        """Test detecting NXP from LPC and i.MX targets"""
        assert detect_vendor("lpc1768") == "NXP"
        assert detect_vendor("lpc55s69") == "NXP"
        assert detect_vendor("mimxrt1060") == "NXP"
    
    def test_detect_unknown_vendor(self):
        """Test unknown vendor detection"""
        assert detect_vendor("unknown_target") == "Unknown"
        assert detect_vendor("cortex_m4") == "Unknown"
    
    def test_detect_chip_family(self):
        """Test chip family extraction"""
        assert detect_chip_family("stm32f103c8") == "STM32F1"
        assert detect_chip_family("stm32h743xi") == "STM32H7"
        assert detect_chip_family("nrf52") == "NRF52"
        # Short targets
        assert detect_chip_family("abc") == "ABC"


class TestFileUtilities:
    """Tests for file type detection and info"""
    
    def test_get_file_type_name_hex(self):
        """Test Intel HEX file type detection"""
        assert get_file_type_name("firmware.hex") == "Intel HEX"
        assert get_file_type_name("/path/to/file.HEX") == "Intel HEX"
    
    def test_get_file_type_name_bin(self):
        """Test binary file type detection"""
        assert get_file_type_name("firmware.bin") == "Binary"
        assert get_file_type_name("test.BIN") == "Binary"
    
    def test_get_file_type_name_elf(self):
        """Test ELF file type detection"""
        assert get_file_type_name("firmware.elf") == "ELF"
        assert get_file_type_name("application.axf") == "ARM Executable"
    
    def test_get_file_type_name_unknown(self):
        """Test unknown file type"""
        assert get_file_type_name("firmware.txt") == "Unknown"
        assert get_file_type_name("no_extension") == "Unknown"
    
    def test_get_file_info_existing_file(self, sample_hex_file):
        """Test getting file info for existing file"""
        type_name, size = get_file_info(str(sample_hex_file))
        assert type_name == "Intel HEX"
        assert size > 0
    
    def test_get_file_info_binary_file(self, sample_bin_file):
        """Test getting file info for binary file"""
        type_name, size = get_file_info(str(sample_bin_file))
        assert type_name == "Binary"
        assert size == 1024  # 1KB as we created
    
    def test_get_file_info_nonexistent_raises_error(self):
        """Test FileNotFoundError for nonexistent file"""
        with pytest.raises(FileNotFoundError):
            get_file_info("/nonexistent/path/file.hex")


class TestSizeFormatting:
    """Tests for human-readable size formatting"""
    
    def test_format_bytes(self):
        """Test formatting bytes"""
        assert format_size(0) == "0 B"
        assert format_size(100) == "100 B"
        assert format_size(1023) == "1023 B"
    
    def test_format_kilobytes(self):
        """Test formatting kilobytes"""
        assert format_size(1024) == "1.0 KB"
        assert format_size(2048) == "2.0 KB"
        assert format_size(1536) == "1.5 KB"
    
    def test_format_megabytes(self):
        """Test formatting megabytes"""
        assert format_size(1024 * 1024) == "1.00 MB"
        assert format_size(1024 * 1024 * 2) == "2.00 MB"
        assert format_size(int(1024 * 1024 * 1.5)) == "1.50 MB"


class TestEdgeCases:
    """Edge case tests for robustness"""
    
    def test_address_boundary_values(self):
        """Test address parsing at boundary values"""
        # 32-bit boundaries
        assert parse_address("0x00000000") == 0
        assert parse_address("0xFFFFFFFF") == 0xFFFFFFFF
        
    def test_frequency_round_trip(self):
        """Test that frequency conversion is reversible"""
        for idx, (freq_hz, _) in enumerate(FREQUENCY_OPTIONS):
            assert freq_hz_to_index(freq_index_to_hz(idx)) == idx
    
    def test_vendor_prefixes_coverage(self):
        """Test all defined vendor prefixes work correctly"""
        for prefix, expected_vendor in VENDOR_PREFIXES.items():
            target = f"{prefix}xyz123"
            assert detect_vendor(target) == expected_vendor, f"Failed for prefix: {prefix}"
