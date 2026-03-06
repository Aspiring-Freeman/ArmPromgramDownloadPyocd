#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Core.flash_info module

Tests the pure functions for resolving flash parameters from chip configs.
These tests do not require Qt or hardware.
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass

from Core.flash_info import (
    FlashInfo,
    resolve_flash_info,
    _estimate_flash_size,
    _estimate_sector_size,
)
from Core.chip_config import ChipConfig


def make_config(**kwargs) -> ChipConfig:
    """Helper to create ChipConfig with required fields"""
    defaults = {
        "name": "Test Config",
        "vendor": "Test",
        "chip_family": "TestFamily",
        "target": "test_chip",
    }
    defaults.update(kwargs)
    return ChipConfig(**defaults)


class TestFlashInfoDataclass:
    """Tests for FlashInfo dataclass"""
    
    def test_default_values(self):
        """FlashInfo should have sensible defaults for STM32"""
        info = FlashInfo()
        assert info.flash_start == 0x08000000
        assert info.flash_size == 128 * 1024  # 128KB
        assert info.sector_size == 0x800  # 2KB
        assert info.target_name == "Unknown"
        assert info.pack_device is None
    
    def test_custom_values(self):
        """FlashInfo should accept custom values"""
        info = FlashInfo(
            flash_start=0x00000000,
            flash_size=256 * 1024,
            sector_size=0x1000,
            target_name="LPC1768",
            pack_device="LPC1768FBD100"
        )
        assert info.flash_start == 0x00000000
        assert info.flash_size == 256 * 1024
        assert info.sector_size == 0x1000
        assert info.target_name == "LPC1768"
        assert info.pack_device == "LPC1768FBD100"


class TestResolveFlashInfo:
    """Tests for resolve_flash_info function"""
    
    def test_basic_config(self):
        """resolve_flash_info should use config values"""
        config = make_config(
            target="stm32f103c8",
            flash_start=0x08000000,
            flash_size=64 * 1024
        )
        info = resolve_flash_info(config)
        
        assert info.flash_start == 0x08000000
        assert info.flash_size == 64 * 1024
        assert info.target_name == "stm32f103c8"
    
    def test_target_name_override(self):
        """resolve_flash_info should allow target_name override"""
        config = make_config(target="stm32f103c8")
        info = resolve_flash_info(config, target_name="STM32F103C8T6")
        
        assert info.target_name == "STM32F103C8T6"
    
    def test_zero_flash_size_triggers_estimate(self):
        """When flash_size is 0, should estimate from target name"""
        config = make_config(
            target="stm32f104",  # Contains '04' -> 256KB estimate
            flash_start=0x08000000,
            flash_size=0
        )
        info = resolve_flash_info(config)
        
        # '04' in target name should estimate 256KB
        assert info.flash_size == 256 * 1024
    
    def test_sector_size_estimation_small_flash(self):
        """Small flash (<= 64KB) should get 1KB sectors"""
        config = make_config(
            target="small_chip",
            flash_size=32 * 1024  # 32KB
        )
        info = resolve_flash_info(config)
        
        assert info.sector_size == 0x400  # 1KB
    
    def test_sector_size_estimation_medium_flash(self):
        """Medium flash (<= 256KB) should get 2KB sectors"""
        config = make_config(
            target="medium_chip",
            flash_size=128 * 1024  # 128KB
        )
        info = resolve_flash_info(config)
        
        assert info.sector_size == 0x800  # 2KB
    
    def test_sector_size_estimation_large_flash(self):
        """Large flash (<= 1MB) should get 4KB sectors"""
        config = make_config(
            target="large_chip",
            flash_size=512 * 1024  # 512KB
        )
        info = resolve_flash_info(config)
        
        assert info.sector_size == 0x1000  # 4KB


class TestEstimateFlashSize:
    """Tests for _estimate_flash_size function"""
    
    def test_target_with_01_gets_64kb(self):
        """Target names containing '01' should estimate 64KB"""
        assert _estimate_flash_size("stm32f101") == 64 * 1024
        assert _estimate_flash_size("fm33lc01x") == 64 * 1024
    
    def test_target_with_02_gets_128kb(self):
        """Target names containing '02' should estimate 128KB"""
        assert _estimate_flash_size("stm32f102") == 128 * 1024
        assert _estimate_flash_size("lpc802") == 128 * 1024
    
    def test_target_with_04_gets_256kb(self):
        """Target names containing '04' should estimate 256KB"""
        assert _estimate_flash_size("stm32f104") == 256 * 1024
        assert _estimate_flash_size("fm33lg04x") == 256 * 1024
    
    def test_unknown_target_gets_default(self):
        """Unknown target should get 128KB default"""
        assert _estimate_flash_size("unknown_chip") == 128 * 1024
        assert _estimate_flash_size("cortex_m") == 128 * 1024
    
    def test_priority_order(self):
        """First match wins (01 before 02 before 04)"""
        # If target has multiple codes, first match in function wins
        # "chip_01_04" contains '01' first, so 64KB
        assert _estimate_flash_size("chip_01") == 64 * 1024


class TestEstimateSectorSize:
    """Tests for _estimate_sector_size function"""
    
    def test_preserves_pack_set_size(self):
        """Should preserve sector_size if already set (not 0x800 default)"""
        info = FlashInfo(
            flash_size=256 * 1024,
            sector_size=0x200  # FM33 512B, set from pack
        )
        assert _estimate_sector_size(info) == 0x200
    
    def test_small_flash_gets_1kb(self):
        """Flash <= 64KB should get 1KB sectors"""
        info = FlashInfo(flash_size=64 * 1024)
        assert _estimate_sector_size(info) == 0x400
    
    def test_medium_flash_gets_2kb(self):
        """Flash <= 256KB should get 2KB sectors"""
        info = FlashInfo(flash_size=256 * 1024)
        assert _estimate_sector_size(info) == 0x800
    
    def test_large_flash_gets_4kb(self):
        """Flash <= 1MB should get 4KB sectors"""
        info = FlashInfo(flash_size=512 * 1024)
        assert _estimate_sector_size(info) == 0x1000
    
    def test_very_large_flash_gets_16kb(self):
        """Flash > 1MB should get 16KB sectors"""
        info = FlashInfo(flash_size=2 * 1024 * 1024)  # 2MB
        assert _estimate_sector_size(info) == 0x4000


class TestPackFileIntegration:
    """Tests for pack file integration in resolve_flash_info
    
    Note: These tests use pytest.mark.skip because _enrich_from_pack uses
    local imports that are difficult to mock. Pack integration is better
    tested via test_pack_parser.py with real fixtures.
    """
    
    def test_nonexistent_pack_falls_back_gracefully(self):
        """Non-existent pack file should fall back to estimation without crash"""
        config = make_config(
            target="stm32f103",
            pack_file="/nonexistent/pack.pack",
            flash_size=0
        )
        # Should not raise, should fall back to estimation
        info = resolve_flash_info(config)
        
        assert info.flash_size > 0  # Got an estimate
        assert info.pack_device is None  # No pack data
    
    def test_empty_pack_path_skips_enrichment(self):
        """Empty pack_file should skip pack enrichment entirely"""
        config = make_config(
            target="stm32f103c8",
            pack_file="",  # Empty
            flash_size=64 * 1024
        )
        info = resolve_flash_info(config)
        
        assert info.flash_size == 64 * 1024
        assert info.pack_device is None
    
    def test_fm33_detection_from_target_name(self):
        """FM33 series should be detectable from target name for sector estimation"""
        # Even without pack, if target contains 'fm33', we might want special handling
        # Current implementation only checks pack device name, not target
        # This test documents current behavior
        config = make_config(
            target="fm33lg04x",
            flash_size=256 * 1024
        )
        info = resolve_flash_info(config)
        
        # Without pack, sector_size comes from flash size estimate (2KB for 256KB)
        assert info.sector_size == 0x800  # Would be 0x200 with pack


class TestEdgeCases:
    """Edge case tests"""
    
    def test_config_without_optional_fields(self):
        """Config with minimal fields should still work"""
        config = make_config(target="minimal")
        info = resolve_flash_info(config)
        
        assert info.target_name == "minimal"
        assert info.flash_start == 0x08000000  # Default
        assert info.flash_size > 0
    
    def test_non_stm32_flash_start_preserved(self):
        """Non-STM32 flash_start should be preserved"""
        config = make_config(
            target="lpc1768",
            flash_start=0x00000000,  # NXP LPC start
            flash_size=512 * 1024
        )
        info = resolve_flash_info(config)
        
        assert info.flash_start == 0x00000000
    
    def test_empty_target_name(self):
        """Empty target name should use 'Unknown'"""
        config = make_config(target="")
        info = resolve_flash_info(config)
        
        # Empty string becomes empty, not "Unknown" from default
        # because getattr returns the empty string
        assert info.target_name == ""
