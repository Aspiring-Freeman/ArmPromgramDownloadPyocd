#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flash programming operations for PyOCD wrapper
Handles flash and flash_file methods
"""

import logging
import os
import time
import traceback
from typing import Optional, Callable

from pyocd.core.session import Session
from pyocd.flash.file_programmer import FileProgrammer

from Core.logger import command_logger

LOG = logging.getLogger(__name__)


class FlashMixin:
    """Mixin class providing flash programming methods"""
    
    _session: Optional[Session]
    _current_target: Optional[str]
    is_connected: bool
    
    def flash(
        self,
        file_path: str,
        base_address: Optional[int] = None,
        erase_mode: str = 'sector',
        no_reset: bool = False,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """Flash firmware to target"""
        if not self.is_connected:
            command_logger.log_error("Not connected", "Please connect to target first")
            return False
        
        start_time = time.time()
        
        # Build equivalent command
        cmd_args = [file_path]
        cmd_args.extend(['--target', self._current_target or 'unknown'])
        if base_address is not None:
            cmd_args.extend(['--base-address', f'0x{base_address:X}'])
        cmd_args.extend(['--erase', erase_mode])
        if no_reset:
            cmd_args.append('--no-reset')
        
        command_logger.log_command('flash', cmd_args)
            
        try:
            # Log file info
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
            command_logger.log_flash_info(file_path, file_size)
            
            if progress_callback:
                progress_callback(0, "Starting...")
            
            command_logger.log(f"")
            command_logger.log(f"⚡ Flash operation:")
            command_logger.log(f"   Erase mode: {erase_mode}")
            command_logger.log(f"   Reset after: {not no_reset}")
            if base_address is not None:
                command_logger.log(f"   Base address: 0x{base_address:08X}")
            
            # Halt target before programming to ensure clean state
            try:
                target = self._session.target
                if not target.is_halted():
                    command_logger.log(f"   Halting target before flash...")
                    target.halt()
            except Exception as halt_err:
                LOG.warning(f"Failed to halt target before flash: {halt_err}")
                
            programmer = FileProgrammer(
                self._session,
                chip_erase=erase_mode,
                no_reset=no_reset
            )
            
            if progress_callback:
                progress_callback(10, f"Loading {os.path.basename(file_path)}")
            
            command_logger.log(f"")
            command_logger.log(f"📝 Programming...")
            
            programmer.program(file_path, base_address=base_address)
            
            if progress_callback:
                progress_callback(100, "Complete!")
            
            duration_ms = (time.time() - start_time) * 1000
            speed = (file_size / 1024) / (duration_ms / 1000) if file_size and duration_ms > 0 else 0
            
            command_logger.log_result(True, f"Flashed {os.path.basename(file_path)}", duration_ms)
            if speed > 0:
                command_logger.log(f"   Speed: {speed:.2f} KB/s")
            
            return True
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_details = traceback.format_exc()
            
            command_logger.log_error(f"Flash failed: {e}")
            command_logger.log(f"")
            command_logger.log(f"📋 Full error traceback:")
            for line in error_details.split('\n'):
                if line.strip():
                    command_logger.log(f"   {line}")
            
            command_logger.log_result(False, "Flash operation failed", duration_ms)
            return False
    
    def flash_file(
        self,
        file_path: str,
        base_address: Optional[int] = None,
        verify: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """Flash a file (hex/bin/elf) to target - convenience wrapper
        
        Args:
            file_path: Path to firmware file (.hex, .bin, .elf)
            base_address: Base address for binary files (auto-detected for hex/elf)
            verify: Verify after programming
            progress_callback: Callback(progress: 0.0-1.0)
        """
        if not self.is_connected:
            command_logger.log_error("Not connected", "Please connect to target first")
            return False
        
        start_time = time.time()
        
        # Build equivalent command
        cmd_args = [file_path]
        cmd_args.extend(['--target', self._current_target or 'unknown'])
        if base_address is not None:
            cmd_args.extend(['--base-address', f'0x{base_address:X}'])
        if not verify:
            cmd_args.append('--trust-crc')
        
        command_logger.log_command('flash', cmd_args)
            
        try:
            # Log file info
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
            command_logger.log_flash_info(file_path, file_size)
            
            # Detect file type
            ext = os.path.splitext(file_path)[1].lower()
            file_type = {
                '.hex': 'Intel HEX',
                '.bin': 'Raw Binary',
                '.elf': 'ELF Executable',
                '.axf': 'AXF/ELF Executable',
            }.get(ext, 'Unknown')
            
            command_logger.log(f"   Type: {file_type}")
            
            if progress_callback:
                progress_callback(0.0)
            
            command_logger.log(f"")
            command_logger.log(f"⚡ Programming target...")
            command_logger.log(f"   Verify: {verify}")
            
            # 创建进度回调包装器，将 PyOCD 的进度值转换为 0.0-1.0
            def pyocd_progress(value):
                """PyOCD progress callback wrapper"""
                if progress_callback:
                    # PyOCD 返回 0.0-1.0 的进度值
                    progress_callback(value)
                
            programmer = FileProgrammer(
                self._session,
                progress=pyocd_progress if progress_callback else None,
                chip_erase='sector',
                trust_crc=not verify
            )
            
            # FileProgrammer auto-detects file format:
            # - .hex: Intel HEX format (address embedded)
            # - .bin: Raw binary (needs base_address)
            # - .elf: ELF executable (address from sections)
            programmer.program(file_path, base_address=base_address)
            
            if progress_callback:
                progress_callback(1.0)
            
            duration_ms = (time.time() - start_time) * 1000
            speed = (file_size / 1024) / (duration_ms / 1000) if file_size and duration_ms > 0 else 0
            
            command_logger.log_result(True, f"Flashed {os.path.basename(file_path)}", duration_ms)
            if speed > 0:
                command_logger.log(f"   Speed: {speed:.2f} KB/s")
            
            return True
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_details = traceback.format_exc()
            
            command_logger.log_error(f"Flash failed: {e}")
            command_logger.log(f"")
            command_logger.log(f"📋 Full error traceback:")
            for line in error_details.split('\n'):
                if line.strip():
                    command_logger.log(f"   {line}")
            
            command_logger.log_result(False, "Flash operation failed", duration_ms)
            return False
