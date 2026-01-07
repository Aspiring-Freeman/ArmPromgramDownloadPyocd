#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyOCD Wrapper Main Class
Combines all mixins into the main wrapper class
"""

import logging
import threading
from typing import Optional, List

# Import from local pyocd (Driver/pyOCD/pyocd)
from pyocd.core.session import Session
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
        """List all available targets"""
        targets = []
        
        # Builtin targets
        for name in TARGET.keys():
            if name_filter and name_filter.lower() not in name.lower():
                continue
            targets.append(name)
            
        # Pack targets
        try:
            pack_targets = pack_target.PackTargets.get_targets()
            for name in pack_targets.keys():
                if name_filter and name_filter.lower() not in name.lower():
                    continue
                if name not in targets:
                    targets.append(name)
        except Exception:
            pass
            
        return sorted(targets)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.disconnect()
