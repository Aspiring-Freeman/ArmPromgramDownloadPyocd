#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMSIS-Pack Parser
Parses .pack files (ZIP archives) to extract chip information from PDSC files
"""

import logging
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

LOG = logging.getLogger(__name__)


@dataclass
class DeviceMemory:
    """Memory region information from CMSIS-Pack"""
    name: str                    # Memory region name (e.g., "IROM1", "Flash", "SRAM1")
    start: int                   # Start address
    size: int                    # Size in bytes
    access: str = "rwx"          # Access permissions
    default: bool = True         # Is default memory
    startup: bool = False        # Is startup memory (boot from here)
    
    def __str__(self):
        return f"{self.name}: 0x{self.start:08X} - 0x{self.start + self.size - 1:08X} ({self.size // 1024}KB)"


@dataclass
class FlashAlgorithm:
    """Flash algorithm information"""
    name: str                    # Algorithm file name
    start: int                   # Flash start address
    size: int                    # Flash size
    ram_start: int = 0x20000000  # RAM start for algorithm
    ram_size: int = 0x8000       # RAM size for algorithm
    default: bool = True


@dataclass
class DeviceInfo:
    """Complete device information from CMSIS-Pack"""
    # Basic info
    name: str                                    # Device name (e.g., "STM32H503CBTx")
    vendor: str = ""                             # Vendor name
    family: str = ""                             # Device family
    sub_family: str = ""                         # Device sub-family
    
    # Processor info
    core: str = "Cortex-M"                       # CPU core type
    core_version: str = ""                       # Core version
    clock: int = 0                               # Max clock frequency
    fpu: bool = False                            # Has FPU
    mpu: bool = False                            # Has MPU
    dsp: bool = False                            # Has DSP
    trust_zone: bool = False                     # Has TrustZone
    endian: str = "Little-endian"                # Endianness
    
    # Memory regions
    memories: List[DeviceMemory] = field(default_factory=list)
    
    # Flash algorithms
    algorithms: List[FlashAlgorithm] = field(default_factory=list)
    
    # Debug info
    svd_file: str = ""                           # SVD file path
    debug_clock: int = 5000000                   # Default debug clock
    
    # Description
    description: str = ""
    
    @property
    def flash_start(self) -> int:
        """Get primary flash start address"""
        # First try to find from algorithms
        for algo in self.algorithms:
            if algo.default:
                return algo.start
        
        # Then try memories
        for mem in self.memories:
            if mem.startup or "flash" in mem.name.lower() or mem.name == "IROM1":
                return mem.start
        
        # Default fallback based on vendor
        return 0x08000000 if "stm32" in self.name.lower() else 0x00000000
    
    @property
    def flash_size(self) -> int:
        """Get primary flash size"""
        for algo in self.algorithms:
            if algo.default:
                return algo.size
        
        for mem in self.memories:
            if mem.startup or "flash" in mem.name.lower() or mem.name == "IROM1":
                return mem.size
        return 0
    
    @property
    def ram_start(self) -> int:
        """Get primary RAM start address"""
        for mem in self.memories:
            if "sram" in mem.name.lower() or "ram" in mem.name.lower() or mem.name == "IRAM1":
                if mem.default:
                    return mem.start
        
        # Fallback: return first RAM-like memory
        for mem in self.memories:
            if "sram" in mem.name.lower() or "ram" in mem.name.lower() or mem.name == "IRAM1":
                return mem.start
        
        return 0x20000000
    
    @property
    def ram_size(self) -> int:
        """Get primary RAM size"""
        for mem in self.memories:
            if "sram" in mem.name.lower() or "ram" in mem.name.lower() or mem.name == "IRAM1":
                if mem.default:
                    return mem.size
        
        for mem in self.memories:
            if "sram" in mem.name.lower() or "ram" in mem.name.lower() or mem.name == "IRAM1":
                return mem.size
        return 0


@dataclass
class PackInfo:
    """CMSIS-Pack package information"""
    vendor: str = ""
    name: str = ""
    description: str = ""
    version: str = ""
    devices: List[DeviceInfo] = field(default_factory=list)
    
    def get_device(self, name: str) -> Optional[DeviceInfo]:
        """Find device by name (case-insensitive partial match)"""
        if not name:
            return None
        
        name_lower = name.lower()
        
        # Exact match first
        for dev in self.devices:
            if dev.name.lower() == name_lower:
                return dev
        
        # Partial match
        for dev in self.devices:
            if name_lower in dev.name.lower():
                return dev
        
        return None
    
    def get_device_names(self) -> List[str]:
        """Get all device names"""
        return [d.name for d in self.devices]


class PackParser:
    """CMSIS-Pack (.pack) file parser"""
    
    def __init__(self, pack_path: str):
        """
        Initialize parser with pack file path
        
        Args:
            pack_path: Path to .pack file
        """
        self.pack_path = Path(pack_path)
        self._pack_info: Optional[PackInfo] = None
    
    def parse(self) -> Optional[PackInfo]:
        """
        Parse the pack file and extract device information
        
        Returns:
            PackInfo object with all devices, or None if parsing failed
        """
        if not self.pack_path.exists():
            LOG.error(f"Pack file not found: {self.pack_path}")
            return None
        
        try:
            with zipfile.ZipFile(self.pack_path, 'r') as zf:
                # Find PDSC file
                pdsc_file = None
                for name in zf.namelist():
                    if name.endswith('.pdsc'):
                        pdsc_file = name
                        break
                
                if not pdsc_file:
                    LOG.error(f"No PDSC file found in pack: {self.pack_path}")
                    return None
                
                # Parse PDSC
                pdsc_content = zf.read(pdsc_file).decode('utf-8')
                self._pack_info = self._parse_pdsc(pdsc_content)
                return self._pack_info
                
        except zipfile.BadZipFile:
            LOG.error(f"Invalid pack file (not a valid ZIP): {self.pack_path}")
            return None
        except Exception as e:
            LOG.exception(f"Error parsing pack file: {e}")
            return None
    
    def _parse_pdsc(self, content: str) -> PackInfo:
        """Parse PDSC XML content"""
        root = ET.fromstring(content)
        
        pack_info = PackInfo(
            vendor=self._get_text(root, 'vendor', ''),
            name=self._get_text(root, 'name', ''),
            description=self._get_text(root, 'description', ''),
        )
        
        # Get version from releases
        releases = root.find('releases')
        if releases is not None:
            release = releases.find('release')
            if release is not None:
                pack_info.version = release.get('version', '')
        
        # Parse devices
        devices_elem = root.find('devices')
        if devices_elem is not None:
            for family in devices_elem.findall('.//family'):
                self._parse_family(family, pack_info)
        
        LOG.info(f"Parsed pack: {pack_info.vendor}.{pack_info.name} v{pack_info.version}, "
                f"{len(pack_info.devices)} devices")
        
        return pack_info
    
    def _parse_family(self, family_elem: ET.Element, pack_info: PackInfo):
        """Parse device family element"""
        family_name = family_elem.get('Dfamily', '')
        vendor_name = family_elem.get('Dvendor', '').split(':')[0]  # "STMicroelectronics:13" -> "STMicroelectronics"
        
        # Get family-level processor info
        family_processor = self._parse_processor(family_elem.find('processor'))
        family_description = self._get_text(family_elem, 'description', '')
        family_debug_clock = self._parse_debug_clock(family_elem)
        
        # Parse sub-families
        for subfamily in family_elem.findall('subFamily'):
            subfamily_name = subfamily.get('DsubFamily', '')
            
            # Get subfamily-level info (inherits from family)
            sub_processor = self._merge_processor(family_processor, 
                                                   self._parse_processor(subfamily.find('processor')))
            sub_memories = self._parse_memories(subfamily)
            sub_algorithms = self._parse_algorithms(subfamily)
            sub_svd = self._parse_svd(subfamily)
            
            # Parse devices in subfamily
            for device in subfamily.findall('device'):
                dev_name = device.get('Dname', '')
                
                # Device-level overrides
                dev_memories = self._parse_memories(device) or sub_memories
                dev_algorithms = self._parse_algorithms(device) or sub_algorithms
                dev_svd = self._parse_svd(device) or sub_svd
                
                device_info = DeviceInfo(
                    name=dev_name,
                    vendor=vendor_name or pack_info.vendor,
                    family=family_name,
                    sub_family=subfamily_name,
                    core=sub_processor.get('core', 'Cortex-M'),
                    core_version=sub_processor.get('core_version', ''),
                    clock=sub_processor.get('clock', 0),
                    fpu=sub_processor.get('fpu', False),
                    mpu=sub_processor.get('mpu', False),
                    dsp=sub_processor.get('dsp', False),
                    trust_zone=sub_processor.get('tz', False),
                    endian=sub_processor.get('endian', 'Little-endian'),
                    memories=dev_memories,
                    algorithms=dev_algorithms,
                    svd_file=dev_svd,
                    debug_clock=family_debug_clock,
                    description=family_description,
                )
                pack_info.devices.append(device_info)
        
        # Also check for devices directly under family (no subfamily)
        for device in family_elem.findall('device'):
            dev_name = device.get('Dname', '')
            dev_memories = self._parse_memories(device) or self._parse_memories(family_elem)
            dev_algorithms = self._parse_algorithms(device) or self._parse_algorithms(family_elem)
            dev_svd = self._parse_svd(device) or self._parse_svd(family_elem)
            
            device_info = DeviceInfo(
                name=dev_name,
                vendor=vendor_name or pack_info.vendor,
                family=family_name,
                sub_family='',
                core=family_processor.get('core', 'Cortex-M'),
                core_version=family_processor.get('core_version', ''),
                clock=family_processor.get('clock', 0),
                fpu=family_processor.get('fpu', False),
                mpu=family_processor.get('mpu', False),
                dsp=family_processor.get('dsp', False),
                trust_zone=family_processor.get('tz', False),
                endian=family_processor.get('endian', 'Little-endian'),
                memories=dev_memories,
                algorithms=dev_algorithms,
                svd_file=dev_svd,
                debug_clock=family_debug_clock,
                description=family_description,
            )
            pack_info.devices.append(device_info)
    
    def _parse_processor(self, proc_elem: Optional[ET.Element]) -> Dict[str, Any]:
        """Parse processor element"""
        if proc_elem is None:
            return {}
        
        result = {}
        
        if proc_elem.get('Dcore'):
            result['core'] = proc_elem.get('Dcore')
        if proc_elem.get('DcoreVersion'):
            result['core_version'] = proc_elem.get('DcoreVersion')
        if proc_elem.get('Dclock'):
            try:
                result['clock'] = int(proc_elem.get('Dclock'))
            except (ValueError, TypeError):
                pass
        
        # FPU: "0", "1", "NO_FPU", "SP_FPU", "DP_FPU"
        fpu = proc_elem.get('Dfpu', '0')
        result['fpu'] = fpu not in ('0', 'NO_FPU')
        
        # MPU: "0", "1", "MPU"
        mpu = proc_elem.get('Dmpu', '0')
        result['mpu'] = mpu not in ('0',)
        
        # DSP
        dsp = proc_elem.get('Ddsp', '')
        result['dsp'] = dsp.upper() == 'DSP'
        
        # TrustZone
        tz = proc_elem.get('Dtz', '')
        result['tz'] = tz.upper() not in ('', 'NO_TZ')
        
        if proc_elem.get('Dendian'):
            result['endian'] = proc_elem.get('Dendian')
        
        return result
    
    def _merge_processor(self, parent: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
        """Merge processor info (child overrides parent)"""
        result = parent.copy()
        result.update(child)
        return result
    
    def _parse_memories(self, elem: ET.Element) -> List[DeviceMemory]:
        """Parse memory elements"""
        memories = []
        
        for mem in elem.findall('memory'):
            name = mem.get('name', mem.get('id', 'Unknown'))
            try:
                start = int(mem.get('start', '0'), 0)
                size = int(mem.get('size', '0'), 0)
            except ValueError:
                continue
            
            access = mem.get('access', 'rwx')
            default = mem.get('default', '0') == '1'
            startup = mem.get('startup', '0') == '1'
            
            memories.append(DeviceMemory(
                name=name,
                start=start,
                size=size,
                access=access,
                default=default,
                startup=startup,
            ))
        
        return memories
    
    def _parse_algorithms(self, elem: ET.Element) -> List[FlashAlgorithm]:
        """Parse flash algorithm elements"""
        algorithms = []
        
        for algo in elem.findall('algorithm'):
            name = algo.get('name', '')
            try:
                start = int(algo.get('start', '0'), 0)
                size = int(algo.get('size', '0'), 0)
                ram_start = int(algo.get('RAMstart', '0x20000000'), 0)
                ram_size = int(algo.get('RAMsize', '0x8000'), 0)
            except ValueError:
                continue
            
            default = algo.get('default', '0') == '1'
            
            algorithms.append(FlashAlgorithm(
                name=name,
                start=start,
                size=size,
                ram_start=ram_start,
                ram_size=ram_size,
                default=default,
            ))
        
        return algorithms
    
    def _parse_svd(self, elem: ET.Element) -> str:
        """Parse SVD file path from debug element"""
        debug = elem.find('debug')
        if debug is not None:
            return debug.get('svd', '')
        return ''
    
    def _parse_debug_clock(self, elem: ET.Element) -> int:
        """Parse debug clock from debugconfig element"""
        debug_config = elem.find('debugconfig')
        if debug_config is not None:
            try:
                return int(debug_config.get('clock', '5000000'))
            except ValueError:
                pass
        return 5000000
    
    def _get_text(self, elem: ET.Element, tag: str, default: str = '') -> str:
        """Get text content of child element"""
        child = elem.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return default
    
    @property
    def pack_info(self) -> Optional[PackInfo]:
        """Get parsed pack info (call parse() first)"""
        return self._pack_info


def parse_pack_file(pack_path: str) -> Optional[PackInfo]:
    """
    Convenience function to parse a pack file
    
    Args:
        pack_path: Path to .pack file
        
    Returns:
        PackInfo object or None if parsing failed
    """
    parser = PackParser(pack_path)
    return parser.parse()


def get_device_from_pack(pack_path: str, device_name: str) -> Optional[DeviceInfo]:
    """
    Get device info from pack file
    
    Args:
        pack_path: Path to .pack file
        device_name: Device name to search for
        
    Returns:
        DeviceInfo or None if not found
    """
    pack_info = parse_pack_file(pack_path)
    if pack_info:
        return pack_info.get_device(device_name)
    return None


if __name__ == "__main__":
    # Test
    import sys
    logging.basicConfig(level=logging.DEBUG)
    
    if len(sys.argv) > 1:
        pack_path = sys.argv[1]
        pack_info = parse_pack_file(pack_path)
        if pack_info:
            print(f"Pack: {pack_info.vendor}.{pack_info.name} v{pack_info.version}")
            print(f"Devices: {len(pack_info.devices)}")
            for dev in pack_info.devices[:10]:  # Show first 10
                print(f"  - {dev.name}: Flash=0x{dev.flash_start:08X} ({dev.flash_size//1024}KB), "
                      f"RAM=0x{dev.ram_start:08X} ({dev.ram_size//1024}KB)")
