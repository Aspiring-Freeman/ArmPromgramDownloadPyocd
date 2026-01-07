#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyOCD Wrapper Module - Backward Compatibility Layer

This module provides backward compatibility for existing code.
The actual implementation has been split into Core/pyocd/ submodule:
  - Core/pyocd/base.py: Enums and data classes
  - Core/pyocd/connection.py: Connection management
  - Core/pyocd/flash.py: Flash programming
  - Core/pyocd/erase.py: Erase operations  
  - Core/pyocd/reset.py: Reset operations
  - Core/pyocd/wrapper.py: Main wrapper class combining mixins

For new code, prefer importing from Core.pyocd directly:
    from Core.pyocd import PyOCDWrapper, ConnectMode, ResetType
"""

# Re-export everything from the new module structure for backward compatibility
from Core.pyocd import (
    ResetType,
    EraseMode,
    ConnectMode,
    ProbeInfo,
    FlashRegion,
    PyOCDWrapper,
)

# Make all re-exported names available
__all__ = [
    'ResetType',
    'EraseMode',
    'ConnectMode',
    'ProbeInfo',
    'FlashRegion',
    'PyOCDWrapper',
]
