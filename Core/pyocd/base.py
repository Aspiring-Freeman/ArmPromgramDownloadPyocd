#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base classes, enums, and data classes for PyOCD wrapper
"""

from dataclasses import dataclass
from enum import Enum


class ResetType(Enum):
    """Reset type enumeration"""
    DEFAULT = "default"
    HARDWARE = "hw"
    SOFTWARE = "sw"
    SYSRESET = "sysresetreq"
    VECTRESET = "vectreset"


class EraseMode(Enum):
    """Erase mode enumeration"""
    CHIP = "chip"
    SECTOR = "sector"
    MASS = "mass"


class ConnectMode(Enum):
    """Connection mode enumeration"""
    HALT = "halt"
    PRE_RESET = "pre-reset"
    UNDER_RESET = "under-reset"
    ATTACH = "attach"


@dataclass
class ProbeInfo:
    """Debug probe information"""
    unique_id: str
    description: str
    vendor_name: str
    product_name: str
    
    def __str__(self) -> str:
        return f"{self.description} ({self.unique_id[:8]}...)"


@dataclass
class FlashRegion:
    """Flash memory region information"""
    start: int
    size: int
    sector_size: int
    name: str
    
    @property
    def end(self) -> int:
        return self.start + self.size
    
    def __str__(self) -> str:
        return f"{self.name}: 0x{self.start:08X} - 0x{self.end:08X} ({self.size // 1024}KB)"
