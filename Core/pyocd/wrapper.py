#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyOCD Wrapper Main Class
Combines all mixins into the main wrapper class
"""

import logging
import threading
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# Import from local pyocd (Driver/pyOCD/pyocd)
from pyocd.core.session import Session
from pyocd.core.helpers import ConnectHelper
from pyocd.target import TARGET
from pyocd.target.pack import pack_target

from Core.pyocd.base import (
    ResetType,
    EraseMode,
    ConnectMode,
    ProbeInfo,
    FlashRegion,
)
from Core.pyocd.connection import ConnectionMixin
from Core.pyocd.flash import FlashMixin
from Core.pyocd.erase import EraseMixin
from Core.pyocd.reset import ResetMixin

LOG = logging.getLogger(__name__)


@dataclass
class ChipDetectionResult:
    """Result of chip detection"""
    success: bool = False
    error: str = ""
    
    # CPU ID info
    cpuid: int = 0
    implementer: str = ""
    variant: int = 0
    architecture: str = ""
    partno: int = 0
    core_type: str = ""
    
    # Vendor-specific IDs
    vendor_id: int = 0
    device_id: int = 0
    revision_id: int = 0
    
    # Matched targets from packs
    matched_targets: List[str] = None
    
    def __post_init__(self):
        if self.matched_targets is None:
            self.matched_targets = []


class PyOCDWrapper(ConnectionMixin, FlashMixin, EraseMixin, ResetMixin):
    """
    High-level PyOCD wrapper for ARM flash programming.
    Uses the local pyocd from Driver/pyOCD/
    
    This class combines functionality from multiple mixins:
    - ConnectionMixin: connect, disconnect, list_probes, get_flash_regions
    - FlashMixin: flash, flash_file
    - EraseMixin: erase, mass_erase, erase_sector, erase_range
    - ResetMixin: reset
    """
    
    def __init__(self, pack_paths: Optional[List[str]] = None):
        self._session: Optional[Session] = None
        self._pack_paths = pack_paths or []
        self._current_target: Optional[str] = None
        self._lock = threading.Lock()
        
        self._load_packs()
        
    def _load_packs(self):
        """Load CMSIS-Pack targets"""
        for pack_path in self._pack_paths:
            try:
                pack_target.PackTargets.populate_targets_from_pack(pack_path)
                LOG.info(f"Loaded pack: {pack_path}")
            except Exception as e:
                LOG.warning(f"Failed to load pack {pack_path}: {e}")
    
    def list_targets(self, name_filter: Optional[str] = None) -> List[str]:
        """List all available targets (builtin + pack targets)"""
        targets = []
        
        # All targets are in TARGET dict (both builtin and pack)
        for name in TARGET.keys():
            if name_filter and name_filter.lower() not in name.lower():
                continue
            targets.append(name)
            
        return sorted(targets)
    
    def detect_chip(self, probe_id: Optional[str] = None, frequency: int = 1000000,
                    pack_path: Optional[str] = None, target_hint: Optional[str] = None) -> ChipDetectionResult:
        """
        Detect connected chip by reading CPU ID and vendor-specific registers.
        Also lists available targets from the provided pack file.
        
        Args:
            probe_id: Optional probe unique ID
            frequency: SWD frequency
            pack_path: Optional CMSIS-Pack path for target support
            target_hint: Optional target name hint (e.g., 'fm33lg04x')
        
        Returns ChipDetectionResult with detected information and matched targets.
        """
        result = ChipDetectionResult()
        session = None
        available_pack_targets = []  # All targets from pack
        
        try:
            # Get probe
            probes = ConnectHelper.get_all_connected_probes(blocking=False)
            if not probes:
                result.error = "未找到调试器"
                return result
            
            # Select probe
            selected_probe = None
            if probe_id:
                for p in probes:
                    if probe_id in p.unique_id:
                        selected_probe = p
                        break
            if not selected_probe:
                selected_probe = probes[0]
            
            # Determine target to use
            # Priority: target_hint > pack targets > cortex_m
            target_to_use = 'cortex_m'
            target_validated = False  # Whether the target was found in pack
            
            # If pack path provided, get ALL available targets from pack
            if pack_path:
                try:
                    from Core.chip_config import normalize_pack_path
                    from Core.pack_parser import PackParser
                    pack_path = normalize_pack_path(pack_path)
                    
                    # Parse pack to get available device names BEFORE loading into pyocd
                    # This gives us the list of targets that will be available
                    parser = PackParser(pack_path)
                    pack_info = parser.parse()
                    if pack_info and pack_info.devices:
                        available_pack_targets = [d.name.lower() for d in pack_info.devices]
                        LOG.info(f"Pack contains targets: {available_pack_targets}")
                    
                    # Load pack into pyocd (adds to TARGET dict)
                    pack_target.PackTargets.populate_targets_from_pack(pack_path)
                    
                    # Now check if targets are available
                    if available_pack_targets:
                        # Try to match target_hint with available targets
                        if target_hint:
                            hint_lower = target_hint.lower().strip()
                            for name in available_pack_targets:
                                if hint_lower == name.lower():
                                    # Exact match
                                    target_to_use = name
                                    target_validated = True
                                    break
                            
                            if not target_validated:
                                # Partial match
                                for name in available_pack_targets:
                                    if hint_lower in name.lower() or name.lower() in hint_lower:
                                        target_to_use = name
                                        target_validated = True
                                        break
                        
                        # If no hint or no match, use first pack target
                        if not target_validated:
                            target_to_use = available_pack_targets[0]
                            target_validated = True
                            
                except Exception as e:
                    LOG.warning(f"Failed to load pack targets: {e}")
            
            # If target hint provided but no pack, check builtin targets
            if target_hint and not target_validated:
                all_targets = self.list_targets()
                hint_lower = target_hint.lower()
                for t in all_targets:
                    if hint_lower == t.lower():
                        target_to_use = t
                        target_validated = True
                        break
                if not target_validated:
                    for t in all_targets:
                        if hint_lower in t.lower() or t.lower() in hint_lower:
                            target_to_use = t
                            target_validated = True
                            break
            
            LOG.info(f"Chip detection using target: {target_to_use} (validated: {target_validated})")
            
            # Store available pack targets in result
            if available_pack_targets:
                result.matched_targets = [f"Pack可用目标:"] + [f"  • {t}" for t in available_pack_targets]
            
            # Warn if target hint didn't match
            if target_hint and not target_validated:
                result.matched_targets = result.matched_targets or []
                result.matched_targets.insert(0, f"⚠ 目标 '{target_hint}' 未在Pack中找到")
            
            # Connect with chosen target
            session_options = {
                'frequency': frequency,
                'connect_mode': 'under-reset',
                'reset_type': 'default',
            }
            
            session = ConnectHelper.session_with_chosen_probe(
                unique_id=selected_probe.unique_id,
                target_override=target_to_use,
                pack=pack_path,
                options=session_options,
                blocking=False
            )
            
            if session is None:
                result.error = "无法创建调试会话"
                return result
            
            session.open()
            target = session.target
            
            # Add actual connected target info
            result.matched_targets = result.matched_targets or []
            actual_target_info = f"✓ 使用目标: {target_to_use}"
            if hasattr(target, 'part_number') and target.part_number:
                actual_target_info += f" ({target.part_number})"
            result.matched_targets.insert(0, actual_target_info)
            
            # Read CPUID register (0xE000ED00)
            try:
                cpuid = target.read32(0xE000ED00)
                result.cpuid = cpuid
                
                # Parse CPUID
                implementer = (cpuid >> 24) & 0xFF
                result.variant = (cpuid >> 20) & 0xF
                arch = (cpuid >> 16) & 0xF
                result.partno = (cpuid >> 4) & 0xFFF
                
                # Implementer
                implementers = {0x41: "ARM", 0x44: "DEC", 0x4D: "Motorola/Freescale", 
                               0x51: "Qualcomm", 0x54: "Texas Instruments"}
                result.implementer = implementers.get(implementer, f"Unknown (0x{implementer:02X})")
                
                # Architecture
                arch_names = {0xC: "ARMv6-M", 0xF: "ARMv7-M/ARMv8-M"}
                result.architecture = arch_names.get(arch, f"Unknown (0x{arch:X})")
                
                # Core type from part number
                core_types = {
                    0xC20: "Cortex-M0",
                    0xC21: "Cortex-M1", 
                    0xC23: "Cortex-M3",
                    0xC24: "Cortex-M4",
                    0xC27: "Cortex-M7",
                    0xC30: "Cortex-M0 (FMSH)",  # FM33 series uses modified M0
                    0xC60: "Cortex-M0+",
                    0xD20: "Cortex-M23",
                    0xD21: "Cortex-M33",
                    0xD22: "Cortex-M55",
                }
                result.core_type = core_types.get(result.partno, f"Unknown (0x{result.partno:03X})")
                
            except Exception as e:
                LOG.warning(f"Failed to read CPUID: {e}")
            
            # Try to read vendor-specific ID registers
            vendor_id_addrs = [
                (0x1FFFFC00, "FM33 UID"),      # FMSH FM33系列
                (0x1FFFF7E8, "STM32 UID"),     # STM32
                (0xE0042000, "STM32 DBGMCU"),
                (0x40015800, "STM32 F0 DBGMCU"),
                (0x40013800, "GD32 DBGMCU"),
                (0x1FFFF7AC, "GD32 UID"),
            ]
            
            for addr, desc in vendor_id_addrs:
                try:
                    id_val = target.read32(addr)
                    if id_val != 0 and id_val != 0xFFFFFFFF:
                        result.vendor_id = id_val
                        result.device_id = id_val & 0xFFF
                        result.revision_id = (id_val >> 16) & 0xFFFF
                        LOG.info(f"Found ID at {desc} (0x{addr:08X}): 0x{id_val:08X}")
                        break
                except Exception:
                    pass
            
            # Get memory info
            try:
                memory_map = target.memory_map
                flash_regions = [r for r in memory_map if r.is_flash]
                ram_regions = [r for r in memory_map if r.is_ram]
                
                if flash_regions:
                    result.matched_targets.append(f"Flash: {sum(r.length for r in flash_regions) // 1024}KB @ 0x{flash_regions[0].start:08X}")
                if ram_regions:
                    result.matched_targets.append(f"RAM: {sum(r.length for r in ram_regions) // 1024}KB @ 0x{ram_regions[0].start:08X}")
            except Exception:
                pass
            
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            LOG.error(f"Chip detection failed: {e}")
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass
        
        return result
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.disconnect()
