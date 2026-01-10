#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Core/pack_parser.py
Tests CMSIS-Pack parsing functionality with various PDSC structures
"""

import pytest
import tempfile
import zipfile
import os
from pathlib import Path

from Core.pack_parser import (
    PackParser, PackInfo, DeviceInfo, DeviceMemory, FlashAlgorithm
)


class TestDeviceMemory:
    """Tests for DeviceMemory dataclass"""
    
    def test_memory_creation(self):
        """Test creating a memory region"""
        mem = DeviceMemory(
            name="IROM1",
            start=0x08000000,
            size=512 * 1024,
            access="rx",
            startup=True
        )
        assert mem.name == "IROM1"
        assert mem.start == 0x08000000
        assert mem.size == 512 * 1024
        assert mem.startup is True
    
    def test_memory_str(self):
        """Test memory string representation"""
        mem = DeviceMemory(name="Flash", start=0x00000000, size=256 * 1024)
        s = str(mem)
        assert "Flash" in s
        assert "0x00000000" in s
        assert "256KB" in s


class TestDeviceInfo:
    """Tests for DeviceInfo dataclass"""
    
    def test_flash_start_from_algorithm(self):
        """Test flash_start property from algorithms"""
        dev = DeviceInfo(
            name="TestChip",
            algorithms=[
                FlashAlgorithm(name="flash.FLM", start=0x08000000, size=256*1024, default=True)
            ]
        )
        assert dev.flash_start == 0x08000000
    
    def test_flash_start_from_memory(self):
        """Test flash_start property from memories when no algorithm"""
        dev = DeviceInfo(
            name="TestChip",
            memories=[
                DeviceMemory(name="IROM1", start=0x00000000, size=256*1024, startup=True)
            ]
        )
        assert dev.flash_start == 0x00000000
    
    def test_flash_start_stm32_fallback(self):
        """Test flash_start fallback for STM32"""
        dev = DeviceInfo(name="STM32F103C8")
        assert dev.flash_start == 0x08000000
    
    def test_flash_start_generic_fallback(self):
        """Test flash_start fallback for generic chip"""
        dev = DeviceInfo(name="FM33LG04X")
        assert dev.flash_start == 0x00000000
    
    def test_flash_size_from_algorithm(self):
        """Test flash_size property"""
        dev = DeviceInfo(
            name="TestChip",
            algorithms=[
                FlashAlgorithm(name="flash.FLM", start=0x08000000, size=512*1024, default=True)
            ]
        )
        assert dev.flash_size == 512 * 1024
    
    def test_ram_start(self):
        """Test ram_start property"""
        dev = DeviceInfo(
            name="TestChip",
            memories=[
                DeviceMemory(name="IRAM1", start=0x20000000, size=64*1024, default=True)
            ]
        )
        assert dev.ram_start == 0x20000000
    
    def test_ram_size(self):
        """Test ram_size property"""
        dev = DeviceInfo(
            name="TestChip",
            memories=[
                DeviceMemory(name="SRAM", start=0x20000000, size=32*1024, default=True)
            ]
        )
        assert dev.ram_size == 32 * 1024


class TestPackInfo:
    """Tests for PackInfo dataclass"""
    
    def test_get_device_exact_match(self):
        """Test getting device by exact name"""
        pack = PackInfo(
            vendor="TestVendor",
            name="TestPack",
            devices=[
                DeviceInfo(name="CHIP_A"),
                DeviceInfo(name="CHIP_B"),
            ]
        )
        dev = pack.get_device("CHIP_A")
        assert dev is not None
        assert dev.name == "CHIP_A"
    
    def test_get_device_case_insensitive(self):
        """Test case insensitive device lookup"""
        pack = PackInfo(
            devices=[DeviceInfo(name="STM32F103C8")]
        )
        dev = pack.get_device("stm32f103c8")
        assert dev is not None
        assert dev.name == "STM32F103C8"
    
    def test_get_device_partial_match(self):
        """Test partial match device lookup"""
        pack = PackInfo(
            devices=[DeviceInfo(name="FM33LG048C")]
        )
        dev = pack.get_device("FM33LG04")
        assert dev is not None
        assert "FM33LG04" in dev.name
    
    def test_get_device_not_found(self):
        """Test device not found"""
        pack = PackInfo(devices=[DeviceInfo(name="CHIP_A")])
        dev = pack.get_device("NONEXISTENT")
        assert dev is None
    
    def test_get_device_names(self):
        """Test getting all device names"""
        pack = PackInfo(
            devices=[
                DeviceInfo(name="CHIP_A"),
                DeviceInfo(name="CHIP_B"),
                DeviceInfo(name="CHIP_C"),
            ]
        )
        names = pack.get_device_names()
        assert len(names) == 3
        assert "CHIP_A" in names
        assert "CHIP_B" in names


class TestPackParser:
    """Tests for PackParser class"""
    
    @pytest.fixture
    def sample_pdsc_content(self):
        """Sample PDSC XML content for testing"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xs:noNamespaceSchemaLocation="PACK.xsd">
  <vendor>TestVendor</vendor>
  <name>TestPack</name>
  <description>Test CMSIS Pack</description>
  <releases>
    <release version="1.0.0" date="2026-01-10">Initial release</release>
  </releases>
  <devices>
    <family Dfamily="TestFamily" Dvendor="TestVendor:99">
      <processor Dcore="Cortex-M0" DcoreVersion="r0p0" Dfpu="NO_FPU" Dendian="Little-endian"/>
      <description>Test device family</description>
      <subFamily DsubFamily="TestSubFamily">
        <processor Dcore="Cortex-M0" Dclock="48000000"/>
        <device Dname="TEST001">
          <memory name="IROM1" start="0x00000000" size="0x40000" startup="true" default="true"/>
          <memory name="IRAM1" start="0x20000000" size="0x8000" default="true"/>
          <algorithm name="Flash/TEST_256.FLM" start="0x00000000" size="0x40000" default="true"/>
        </device>
        <device Dname="TEST002">
          <memory name="IROM1" start="0x00000000" size="0x80000" startup="true" default="true"/>
          <memory name="IRAM1" start="0x20000000" size="0x10000" default="true"/>
          <algorithm name="Flash/TEST_512.FLM" start="0x00000000" size="0x80000" default="true"/>
        </device>
      </subFamily>
    </family>
  </devices>
</package>'''
    
    @pytest.fixture
    def temp_pack_file(self, sample_pdsc_content):
        """Create a temporary pack file for testing"""
        with tempfile.NamedTemporaryFile(suffix='.pack', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zf:
                zf.writestr('TestVendor.TestPack.pdsc', sample_pdsc_content)
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)
    
    def test_parse_valid_pack(self, temp_pack_file):
        """Test parsing a valid pack file"""
        parser = PackParser(temp_pack_file)
        pack_info = parser.parse()
        
        assert pack_info is not None
        assert pack_info.vendor == "TestVendor"
        assert pack_info.name == "TestPack"
        assert pack_info.version == "1.0.0"
        assert len(pack_info.devices) == 2
    
    def test_parse_device_info(self, temp_pack_file):
        """Test device information is parsed correctly"""
        parser = PackParser(temp_pack_file)
        pack_info = parser.parse()
        
        dev = pack_info.get_device("TEST001")
        assert dev is not None
        assert dev.name == "TEST001"
        assert dev.family == "TestFamily"
        assert dev.sub_family == "TestSubFamily"
        assert dev.flash_start == 0x00000000
        assert dev.flash_size == 0x40000  # 256KB
        assert dev.ram_start == 0x20000000
        assert dev.ram_size == 0x8000  # 32KB
    
    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file"""
        parser = PackParser("/nonexistent/path/file.pack")
        pack_info = parser.parse()
        assert pack_info is None
    
    def test_parse_invalid_zip(self):
        """Test parsing invalid ZIP file"""
        with tempfile.NamedTemporaryFile(suffix='.pack', delete=False) as f:
            f.write(b"This is not a valid ZIP file")
            temp_path = f.name
        
        try:
            parser = PackParser(temp_path)
            pack_info = parser.parse()
            assert pack_info is None
        finally:
            os.unlink(temp_path)
    
    def test_parse_zip_without_pdsc(self):
        """Test parsing ZIP without PDSC file"""
        with tempfile.NamedTemporaryFile(suffix='.pack', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zf:
                zf.writestr('readme.txt', 'No PDSC here')
            temp_path = f.name
        
        try:
            parser = PackParser(temp_path)
            pack_info = parser.parse()
            assert pack_info is None
        finally:
            os.unlink(temp_path)


class TestPackParserMalformedPDSC:
    """Tests for handling malformed PDSC content"""
    
    @pytest.fixture
    def create_pack_with_pdsc(self):
        """Factory to create pack files with custom PDSC content"""
        created_files = []
        
        def _create(pdsc_content):
            with tempfile.NamedTemporaryFile(suffix='.pack', delete=False) as f:
                with zipfile.ZipFile(f, 'w') as zf:
                    zf.writestr('test.pdsc', pdsc_content)
                created_files.append(f.name)
                return f.name
        
        yield _create
        
        for f in created_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_minimal_pdsc(self, create_pack_with_pdsc):
        """Test parsing minimal PDSC with only required elements"""
        pdsc = '''<?xml version="1.0"?>
<package>
  <vendor>Min</vendor>
  <name>MinPack</name>
  <devices>
    <family Dfamily="MinFamily" Dvendor="Min:1">
      <device Dname="MinDevice"/>
    </family>
  </devices>
</package>'''
        pack_path = create_pack_with_pdsc(pdsc)
        parser = PackParser(pack_path)
        pack_info = parser.parse()
        
        assert pack_info is not None
        assert pack_info.vendor == "Min"
        assert len(pack_info.devices) >= 1
    
    def test_pdsc_missing_vendor(self, create_pack_with_pdsc):
        """Test PDSC without vendor element"""
        pdsc = '''<?xml version="1.0"?>
<package>
  <name>NoVendorPack</name>
  <devices>
    <family Dfamily="TestFamily" Dvendor="Test:1">
      <device Dname="TestDevice"/>
    </family>
  </devices>
</package>'''
        pack_path = create_pack_with_pdsc(pdsc)
        parser = PackParser(pack_path)
        pack_info = parser.parse()
        
        assert pack_info is not None
        assert pack_info.vendor == ""  # Empty but not None
    
    def test_pdsc_empty_devices(self, create_pack_with_pdsc):
        """Test PDSC with empty devices section"""
        pdsc = '''<?xml version="1.0"?>
<package>
  <vendor>Test</vendor>
  <name>EmptyPack</name>
  <devices></devices>
</package>'''
        pack_path = create_pack_with_pdsc(pdsc)
        parser = PackParser(pack_path)
        pack_info = parser.parse()
        
        assert pack_info is not None
        assert len(pack_info.devices) == 0
    
    def test_pdsc_hex_addresses(self, create_pack_with_pdsc):
        """Test parsing hex addresses in various formats"""
        pdsc = '''<?xml version="1.0"?>
<package>
  <vendor>Test</vendor>
  <name>HexTest</name>
  <devices>
    <family Dfamily="HexFamily" Dvendor="Test:1">
      <device Dname="HexDevice">
        <memory name="IROM1" start="0x08000000" size="0x100000" startup="true"/>
        <memory name="IRAM1" start="0x20000000" size="0x20000"/>
      </device>
    </family>
  </devices>
</package>'''
        pack_path = create_pack_with_pdsc(pdsc)
        parser = PackParser(pack_path)
        pack_info = parser.parse()
        
        dev = pack_info.get_device("HexDevice")
        assert dev is not None
        assert dev.flash_start == 0x08000000
        assert dev.flash_size == 0x100000  # 1MB
        assert dev.ram_start == 0x20000000


class TestPackParserRealWorld:
    """Integration tests with real pack structure patterns"""
    
    @pytest.fixture
    def stm32_like_pdsc(self):
        """PDSC similar to real STM32 packs"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<package>
  <vendor>STMicroelectronics</vendor>
  <name>STM32F1xx_DFP</name>
  <description>STM32F1 Series Device Support</description>
  <releases>
    <release version="2.4.0" date="2025-01-01">Update</release>
  </releases>
  <devices>
    <family Dfamily="STM32F1" Dvendor="STMicroelectronics:13">
      <processor Dcore="Cortex-M3" DcoreVersion="r2p1" Dfpu="NO_FPU" Dmpu="MPU" Dendian="Little-endian"/>
      <description>STM32F1 family</description>
      <subFamily DsubFamily="STM32F103">
        <processor Dclock="72000000"/>
        <device Dname="STM32F103C8">
          <memory name="IROM1" start="0x08000000" size="0x10000" startup="true" default="true"/>
          <memory name="IRAM1" start="0x20000000" size="0x5000" default="true"/>
          <algorithm name="Flash/STM32F10x_128.FLM" start="0x08000000" size="0x10000" default="true"/>
        </device>
        <device Dname="STM32F103CB">
          <memory name="IROM1" start="0x08000000" size="0x20000" startup="true" default="true"/>
          <memory name="IRAM1" start="0x20000000" size="0x5000" default="true"/>
          <algorithm name="Flash/STM32F10x_128.FLM" start="0x08000000" size="0x20000" default="true"/>
        </device>
      </subFamily>
    </family>
  </devices>
</package>'''
    
    def test_stm32_pack_parsing(self, stm32_like_pdsc):
        """Test parsing STM32-like pack"""
        with tempfile.NamedTemporaryFile(suffix='.pack', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zf:
                zf.writestr('STM.pdsc', stm32_like_pdsc)
            temp_path = f.name
        
        try:
            parser = PackParser(temp_path)
            pack_info = parser.parse()
            
            assert pack_info is not None
            assert "STM" in pack_info.vendor
            assert len(pack_info.devices) == 2
            
            # Check STM32F103C8 (Blue Pill)
            dev = pack_info.get_device("STM32F103C8")
            assert dev is not None
            assert dev.flash_start == 0x08000000
            assert dev.flash_size == 0x10000  # 64KB
            assert dev.ram_start == 0x20000000
            assert dev.ram_size == 0x5000  # 20KB
            assert dev.core == "Cortex-M3"
            
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
