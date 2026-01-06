#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common utilities and constants
Centralized definitions to avoid duplication across modules
"""

from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass

# =============================================================================
# SWD Frequency Constants
# =============================================================================

# Frequency options: (Hz value, display name)
FREQUENCY_OPTIONS: List[Tuple[int, str]] = [
    (100000, "100 kHz"),
    (500000, "500 kHz"),
    (1000000, "1 MHz"),
    (2000000, "2 MHz"),
    (4000000, "4 MHz"),
    (8000000, "8 MHz"),
    (10000000, "10 MHz"),
]

# Index to Hz mapping
FREQ_INDEX_TO_HZ: Dict[int, int] = {i: f[0] for i, f in enumerate(FREQUENCY_OPTIONS)}

# Hz to index mapping
FREQ_HZ_TO_INDEX: Dict[int, int] = {f[0]: i for i, f in enumerate(FREQUENCY_OPTIONS)}

# Default frequency
DEFAULT_FREQUENCY = 1000000  # 1 MHz


def get_frequency_display_names() -> List[str]:
    """Get list of frequency display names for combo boxes"""
    return [f[1] for f in FREQUENCY_OPTIONS]


def freq_index_to_hz(index: int) -> int:
    """Convert combo box index to frequency in Hz"""
    return FREQ_INDEX_TO_HZ.get(index, DEFAULT_FREQUENCY)


def freq_hz_to_index(freq_hz: int) -> int:
    """Convert frequency in Hz to combo box index"""
    return FREQ_HZ_TO_INDEX.get(freq_hz, 2)  # Default to 1 MHz (index 2)


# =============================================================================
# Address Parsing Utilities
# =============================================================================

def parse_address(text: str, default: int = 0) -> int:
    """
    Parse address string to integer.
    
    Supports:
    - Hex with prefix: "0x08000000", "0X08000000"
    - Plain decimal: "134217728"
    - Empty string returns default
    
    Args:
        text: Address string to parse
        default: Default value if parsing fails or text is empty
        
    Returns:
        Parsed address as integer
        
    Raises:
        ValueError: If text cannot be parsed as a valid address
    """
    text = text.strip()
    if not text:
        return default
    
    try:
        if text.lower().startswith('0x'):
            return int(text, 16)
        else:
            return int(text)
    except ValueError:
        raise ValueError(f"Invalid address format: '{text}'")


def format_address(address: int, width: int = 8) -> str:
    """
    Format address as hex string.
    
    Args:
        address: Address integer
        width: Number of hex digits (default 8 for 32-bit)
        
    Returns:
        Formatted string like "0x08000000"
    """
    return f"0x{address:0{width}X}"


def is_valid_address(text: str) -> bool:
    """Check if text is a valid address string"""
    try:
        parse_address(text)
        return True
    except ValueError:
        return False


# =============================================================================
# File Type Detection
# =============================================================================

# File extension to type name mapping
FILE_TYPE_NAMES: Dict[str, str] = {
    ".hex": "Intel HEX",
    ".bin": "Binary",
    ".elf": "ELF",
    ".axf": "ARM Executable",
}


def get_file_type_name(file_path: str) -> str:
    """
    Get human-readable file type name from file path.
    
    Args:
        file_path: Path to file
        
    Returns:
        Type name like "Intel HEX" or "Unknown"
    """
    import os
    ext = os.path.splitext(file_path)[1].lower()
    return FILE_TYPE_NAMES.get(ext, "Unknown")


def get_file_info(file_path: str) -> Tuple[str, int]:
    """
    Get file type and size.
    
    Args:
        file_path: Path to file
        
    Returns:
        Tuple of (type_name, size_in_bytes)
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    import os
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    type_name = get_file_type_name(file_path)
    size = os.path.getsize(file_path)
    return type_name, size


# =============================================================================
# Vendor Detection
# =============================================================================

# Target prefix to vendor mapping
VENDOR_PREFIXES: Dict[str, str] = {
    "stm32": "STMicroelectronics",
    "gd32": "GigaDevice", 
    "mm32": "MindMotion",
    "nrf": "Nordic",
    "lpc": "NXP",
    "mimx": "NXP",
    "mk": "NXP",
    "at32": "Artery",
    "apm32": "APM/Geehy",
    "ch32": "WCH",
    "hc32": "HDSC",
    "air": "Luatos",
    "max32": "Maxim/ADI",
    "rp2": "Raspberry Pi",
    "cy8c": "Infineon/Cypress",
}


def detect_vendor(target: str) -> str:
    """
    Detect chip vendor from target name.
    
    Args:
        target: PyOCD target name like "stm32f103c8"
        
    Returns:
        Vendor name or "Unknown"
    """
    target_lower = target.lower()
    for prefix, vendor in VENDOR_PREFIXES.items():
        if target_lower.startswith(prefix):
            return vendor
    return "Unknown"


def detect_chip_family(target: str) -> str:
    """
    Extract chip family from target name.
    
    Args:
        target: PyOCD target name like "stm32f103c8"
        
    Returns:
        Family name like "STM32F1"
    """
    target_upper = target.upper()
    if len(target_upper) >= 7:
        return target_upper[:7]
    elif len(target_upper) >= 5:
        return target_upper[:5]
    return target_upper


# =============================================================================
# Validation Utilities
# =============================================================================

def validate_frequency(freq: int) -> bool:
    """Check if frequency is in valid range"""
    return 10000 <= freq <= 50000000  # 10 kHz to 50 MHz


def validate_flash_address(address: int, min_addr: int = 0x00000000, 
                           max_addr: int = 0xFFFFFFFF) -> bool:
    """Check if address is in valid range for flash"""
    return min_addr <= address <= max_addr


# =============================================================================
# Size Formatting
# =============================================================================

def format_size(size_bytes: int) -> str:
    """
    Format byte size to human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string like "128 KB" or "1.5 MB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
