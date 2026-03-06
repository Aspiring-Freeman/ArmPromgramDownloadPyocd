#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flash memory information utilities

Provides pure functions for resolving flash parameters from chip configs 
and CMSIS-Pack files. These functions are UI-independent and can be easily
unit tested.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Core.chip_config import ChipConfig

LOG = logging.getLogger(__name__)


@dataclass
class FlashInfo:
    """Resolved flash memory parameters
    
    Attributes:
        flash_start: Flash base address (default 0x08000000 for STM32)
        flash_size: Flash total size in bytes
        sector_size: Flash sector size in bytes
        target_name: Target device name string
        pack_device: Device name from CMSIS-Pack if available
    """
    flash_start: int = 0x08000000
    flash_size: int = 128 * 1024  # 128KB default
    sector_size: int = 0x800      # 2KB default
    target_name: str = "Unknown"
    pack_device: str | None = None


def resolve_flash_info(chip_config: ChipConfig, target_name: str = "") -> FlashInfo:
    """
    Resolve complete flash parameters from chip config + pack file.
    
    Priority: pack file info > chip_config fields > heuristic guess
    
    This is a pure function that can be easily unit tested without Qt dependencies.
    
    Args:
        chip_config: ChipConfig dataclass with flash_start, flash_size, pack_file, etc.
        target_name: Override target name if different from config
        
    Returns:
        FlashInfo with all parameters resolved
        
    Example:
        >>> config = ChipConfig(target="STM32F103C8", flash_start=0x08000000)
        >>> info = resolve_flash_info(config)
        >>> print(f"Flash at 0x{info.flash_start:08X}, {info.flash_size // 1024}KB")
    """
    info = FlashInfo(
        flash_start=getattr(chip_config, 'flash_start', 0x08000000),
        flash_size=getattr(chip_config, 'flash_size', 0),
        target_name=target_name or getattr(chip_config, 'target', 'Unknown'),
    )
    
    # Try to enrich from pack file
    pack_file = getattr(chip_config, 'pack_file', '')
    if pack_file:
        _enrich_from_pack(info, pack_file, chip_config)
    
    # Fill remaining unknowns with heuristics
    if info.flash_size == 0:
        info.flash_size = _estimate_flash_size(info.target_name)
    
    # Update sector size based on device family or flash size
    info.sector_size = _estimate_sector_size(info)
    
    return info


def _enrich_from_pack(info: FlashInfo, pack_file: str, chip_config: ChipConfig) -> None:
    """Enrich FlashInfo with data from CMSIS-Pack file
    
    Args:
        info: FlashInfo instance to update in-place
        pack_file: Path to CMSIS-Pack file
        chip_config: Original chip config for fallback lookups
    """
    try:
        from Core.pack_parser import PackParser
        from Core.chip_config import normalize_pack_path
        
        pack_path = normalize_pack_path(pack_file)
        parser = PackParser(pack_path)
        pack_info = parser.parse()
        
        if not pack_info or not pack_info.devices:
            return
        
        # Try to find matching device in pack
        device = pack_info.get_device(info.target_name)
        
        # Fallback: try chip_family
        if device is None:
            chip_family = getattr(chip_config, 'chip_family', '')
            if chip_family:
                device = pack_info.get_device(chip_family)
        
        # Fallback: use first device
        if device is None:
            device = pack_info.devices[0]
            LOG.info(f"Using first pack device: {device.name}")
        
        if device:
            info.pack_device = device.name
            
            # Only override flash_size if config has 0
            if info.flash_size == 0:
                info.flash_size = device.flash_size
            
            # Only override flash_start if config has default STM32 value
            # and pack has different value (likely correct for this chip)
            if info.flash_start == 0x08000000 and device.flash_start != 0x08000000:
                info.flash_start = device.flash_start
            
            # FM33 series typically has 512B sectors
            if 'fm33' in device.name.lower():
                info.sector_size = 0x200  # 512B for FM33
                
    except Exception as e:
        LOG.warning(f"Failed to get flash info from pack: {e}")


def _estimate_flash_size(target_name: str) -> int:
    """Estimate flash size from target name suffix
    
    Many ARM MCUs encode flash size in the part number:
    - xx01: 64KB
    - xx02: 128KB
    - xx04: 256KB
    
    Args:
        target_name: Target device name
        
    Returns:
        Estimated flash size in bytes
    """
    if '01' in target_name:
        return 64 * 1024   # 64KB
    if '02' in target_name:
        return 128 * 1024  # 128KB
    if '04' in target_name:
        return 256 * 1024  # 256KB
    return 128 * 1024  # Safe default


def _estimate_sector_size(info: FlashInfo) -> int:
    """Estimate sector size from flash size if not already set from pack
    
    Args:
        info: FlashInfo with flash_size populated
        
    Returns:
        Estimated sector size in bytes
    """
    # If already set from pack (e.g., FM33 series), keep it
    if info.sector_size != 0x800:
        return info.sector_size
    
    # Estimate based on total flash size
    if info.flash_size <= 64 * 1024:      # <= 64KB
        return 0x400   # 1KB
    if info.flash_size <= 256 * 1024:     # <= 256KB
        return 0x800   # 2KB
    if info.flash_size <= 1024 * 1024:    # <= 1MB
        return 0x1000  # 4KB
    return 0x4000  # 16KB for large flash
