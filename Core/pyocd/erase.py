#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Erase operations for PyOCD wrapper
Handles erase, mass_erase, erase_sector, erase_range methods
"""

import logging
import time
import traceback
from typing import Optional, List, Callable

from pyocd.core.session import Session
from pyocd.flash.eraser import FlashEraser

from Core.logger import command_logger
from Core.pyocd.base import EraseMode, FlashRegion

LOG = logging.getLogger(__name__)


class EraseMixin:
    """Mixin class providing erase methods"""
    
    _session: Optional[Session]
    _current_target: Optional[str]
    is_connected: bool
    get_flash_regions: Callable[[], List[FlashRegion]]
    
    def erase(
        self,
        mode: EraseMode = EraseMode.CHIP,
        addresses: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """Erase flash memory"""
        if not self.is_connected:
            command_logger.log_error("Not connected", "Please connect to target first")
            return False
        
        start_time = time.time()
        
        # Build equivalent command
        cmd_args = ['--target', self._current_target or 'unknown']
        if mode == EraseMode.CHIP:
            cmd_args.append('--chip')
        elif mode == EraseMode.MASS:
            cmd_args.append('--mass')
        elif mode == EraseMode.SECTOR and addresses:
            cmd_args.extend(addresses)
        
        command_logger.log_command('erase', cmd_args)
            
        try:
            if progress_callback:
                progress_callback(0, f"Starting {mode.value} erase...")
            
            command_logger.log(f"")
            command_logger.log(f"🗑️ Erase operation:")
            command_logger.log(f"   Mode: {mode.value}")
            if addresses:
                command_logger.log(f"   Addresses: {addresses}")
                
            eraser_mode = {
                EraseMode.CHIP: FlashEraser.Mode.CHIP,
                EraseMode.MASS: FlashEraser.Mode.MASS,
                EraseMode.SECTOR: FlashEraser.Mode.SECTOR,
            }[mode]
            
            eraser = FlashEraser(self._session, eraser_mode)
            eraser.erase(addresses or [])
            
            if progress_callback:
                progress_callback(100, "Complete!")
            
            duration_ms = (time.time() - start_time) * 1000
            command_logger.log_result(True, f"Erase ({mode.value}) complete", duration_ms)
            return True
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            error_details = traceback.format_exc()
            
            command_logger.log_error(f"Erase failed: {e}")
            command_logger.log(f"")
            
            # Provide troubleshooting hints
            if "No such device" in error_msg or "disconnected" in error_msg.lower():
                command_logger.log("🔧 Troubleshooting USB disconnect during erase:")
                command_logger.log("   1. Check USB cable connection")
                command_logger.log("   2. Ensure target board has stable power")
                command_logger.log("   3. Try using a powered USB hub")
                command_logger.log("   4. Reconnect and try again")
                # Mark session as disconnected
                self._session = None
                self._current_target = None
            elif "timeout" in error_msg.lower():
                command_logger.log("🔧 Troubleshooting timeout during erase:")
                command_logger.log("   1. Target may need more time for erase")
                command_logger.log("   2. Try lowering SWD frequency")
            
            command_logger.log(f"")
            command_logger.log(f"📋 Full error traceback:")
            for line in error_details.split('\n'):
                if line.strip():
                    command_logger.log(f"   {line}")
            
            command_logger.log_result(False, "Erase operation failed", duration_ms)
            return False
    
    def mass_erase(self, progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """Perform mass/chip erase"""
        if not self.is_connected:
            command_logger.log_error("Not connected", "Please connect to target first")
            return False
        
        start_time = time.time()
        
        # Build equivalent command
        cmd_args = ['--target', self._current_target or 'unknown', '--chip']
        command_logger.log_command('erase', cmd_args)
            
        try:
            if progress_callback:
                progress_callback(0.0)
            
            command_logger.log(f"")
            command_logger.log(f"🗑️ Mass erase operation...")
            command_logger.log(f"   ⚠️ This may take several seconds...")
            command_logger.log(f"   ⚠️ Do not disconnect USB or power during erase!")
                
            eraser = FlashEraser(self._session, FlashEraser.Mode.CHIP)
            eraser.erase([])
            
            if progress_callback:
                progress_callback(1.0)
            
            duration_ms = (time.time() - start_time) * 1000
            command_logger.log_result(True, "Mass erase complete", duration_ms)
            return True
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            error_details = traceback.format_exc()
            
            command_logger.log_error(f"Mass erase failed: {e}")
            command_logger.log(f"")
            
            # Provide troubleshooting hints
            if "No such device" in error_msg or "disconnected" in error_msg.lower():
                command_logger.log("🔧 Troubleshooting USB disconnect during erase:")
                command_logger.log("   1. Check USB cable connection")
                command_logger.log("   2. Ensure target board has stable power")
                command_logger.log("   3. Try using a powered USB hub")
                command_logger.log("   4. Reconnect and try again")
                # Properly close session to clean up resources
                self._force_close_session()
            elif "timeout" in error_msg.lower():
                command_logger.log("🔧 Troubleshooting timeout during erase:")
                command_logger.log("   1. Target may need more time for erase")
                command_logger.log("   2. Try lowering SWD frequency")
                command_logger.log("   3. Check target board power supply")
            elif "protection" in error_msg.lower() or "locked" in error_msg.lower():
                command_logger.log("🔧 Troubleshooting protected flash:")
                command_logger.log("   1. Flash may be read/write protected")
                command_logger.log("   2. Check option bytes configuration")
                command_logger.log("   3. May need to unlock via bootloader")
            
            command_logger.log(f"")
            command_logger.log(f"📋 Full error traceback:")
            for line in error_details.split('\n'):
                if line.strip():
                    command_logger.log(f"   {line}")
            
            command_logger.log_result(False, "Mass erase failed", duration_ms)
            return False
    
    def erase_sector(self, sector: int, progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """Erase specific sector"""
        if not self.is_connected:
            command_logger.log_error("Not connected", "Please connect to target first")
            return False
        
        start_time = time.time()
            
        try:
            if progress_callback:
                progress_callback(0.0)
            
            # Get flash region to calculate sector address
            regions = self.get_flash_regions()
            if not regions:
                command_logger.log_error("No flash regions found")
                return False
            
            region = regions[0]
            sector_addr = region.start + (sector * region.sector_size)
            addr_str = f"0x{sector_addr:08X}"
            
            # Build equivalent command
            cmd_args = ['--target', self._current_target or 'unknown', addr_str]
            command_logger.log_command('erase', cmd_args)
            
            command_logger.log(f"")
            command_logger.log(f"🗑️ Sector erase:")
            command_logger.log(f"   Sector: {sector}")
            command_logger.log(f"   Address: {addr_str}")
            command_logger.log(f"   Size: {region.sector_size} bytes")
            
            eraser = FlashEraser(self._session, FlashEraser.Mode.SECTOR)
            eraser.erase([addr_str])
            
            if progress_callback:
                progress_callback(1.0)
            
            duration_ms = (time.time() - start_time) * 1000
            command_logger.log_result(True, f"Sector {sector} erased", duration_ms)
            return True
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_details = traceback.format_exc()
            
            command_logger.log_error(f"Sector erase failed: {e}")
            command_logger.log(f"")
            command_logger.log(f"📋 Full error traceback:")
            for line in error_details.split('\n'):
                if line.strip():
                    command_logger.log(f"   {line}")
            
            command_logger.log_result(False, "Sector erase failed", duration_ms)
            return False
    
    def erase_range(
        self, 
        start: int, 
        end: int,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """Erase address range"""
        if not self.is_connected:
            command_logger.log_error("Not connected", "Please connect to target first")
            return False
        
        start_time = time.time()
        addr_str = f"0x{start:08X}-0x{end:08X}"
        
        # Build equivalent command
        cmd_args = ['--target', self._current_target or 'unknown', addr_str]
        command_logger.log_command('erase', cmd_args)
            
        try:
            if progress_callback:
                progress_callback(0.0)
            
            command_logger.log(f"")
            command_logger.log(f"🗑️ Range erase:")
            command_logger.log(f"   Start: 0x{start:08X}")
            command_logger.log(f"   End:   0x{end:08X}")
            command_logger.log(f"   Size:  {(end - start) // 1024} KB")
                
            eraser = FlashEraser(self._session, FlashEraser.Mode.SECTOR)
            eraser.erase([addr_str])
            
            if progress_callback:
                progress_callback(1.0)
            
            duration_ms = (time.time() - start_time) * 1000
            command_logger.log_result(True, f"Range 0x{start:08X}-0x{end:08X} erased", duration_ms)
            return True
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_details = traceback.format_exc()
            
            command_logger.log_error(f"Range erase failed: {e}")
            command_logger.log(f"")
            command_logger.log(f"📋 Full error traceback:")
            for line in error_details.split('\n'):
                if line.strip():
                    command_logger.log(f"   {line}")
            
            command_logger.log_result(False, "Range erase failed", duration_ms)
            return False
