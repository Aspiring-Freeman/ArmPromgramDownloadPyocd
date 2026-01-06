#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyOCD Wrapper Module
High-level interface for PyOCD operations using local Driver/pyOCD
"""

import logging
import time
import os
import traceback
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import threading

# Import from local pyocd (Driver/pyOCD/pyocd)
from pyocd.core.helpers import ConnectHelper
from pyocd.core.session import Session
from pyocd.flash.file_programmer import FileProgrammer
from pyocd.flash.eraser import FlashEraser
from pyocd.target import TARGET
from pyocd.target.pack import pack_target

from Core.logger import command_logger

LOG = logging.getLogger(__name__)


class ResetType(Enum):
    DEFAULT = "default"
    HARDWARE = "hw"
    SOFTWARE = "sw"
    SYSRESET = "sysresetreq"
    VECTRESET = "vectreset"


class EraseMode(Enum):
    CHIP = "chip"
    SECTOR = "sector"
    MASS = "mass"


class ConnectMode(Enum):
    HALT = "halt"
    PRE_RESET = "pre-reset"
    UNDER_RESET = "under-reset"
    ATTACH = "attach"


@dataclass
class ProbeInfo:
    unique_id: str
    description: str
    vendor_name: str
    product_name: str
    
    def __str__(self) -> str:
        return f"{self.description} ({self.unique_id[:8]}...)"


@dataclass
class FlashRegion:
    start: int
    size: int
    sector_size: int
    name: str
    
    @property
    def end(self) -> int:
        return self.start + self.size
    
    def __str__(self) -> str:
        return f"{self.name}: 0x{self.start:08X} - 0x{self.end:08X} ({self.size // 1024}KB)"


class PyOCDWrapper:
    """
    High-level PyOCD wrapper for ARM flash programming.
    Uses the local pyocd from Driver/pyOCD/
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
    
    def list_probes(self) -> List[ProbeInfo]:
        """List all connected debug probes"""
        probes = []
        try:
            all_probes = ConnectHelper.get_all_connected_probes(blocking=False)
            for probe in all_probes:
                info = ProbeInfo(
                    unique_id=probe.unique_id,
                    description=probe.description,
                    vendor_name=getattr(probe, 'vendor_name', 'Unknown'),
                    product_name=getattr(probe, 'product_name', 'Unknown'),
                )
                probes.append(info)
        except Exception as e:
            LOG.error(f"Failed to list probes: {e}")
        return probes
    
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
        except:
            pass
            
        return sorted(targets)
    
    def connect(
        self,
        target: str,
        probe_id: Optional[str] = None,
        frequency: int = 1000000,
        connect_mode: ConnectMode = ConnectMode.UNDER_RESET,
        pack_path: Optional[str] = None,
    ) -> bool:
        """Connect to target device"""
        # Don't use lock here - allow cancellation
        start_time = time.time()
        
        # Build equivalent command line for logging
        cmd_args = []
        if probe_id:
            cmd_args.extend(['--probe', probe_id[:16] + '...'])
        cmd_args.extend(['--target', target])
        cmd_args.extend(['--frequency', str(frequency)])
        cmd_args.extend(['--connect', connect_mode.value])
        if pack_path:
            cmd_args.extend(['--pack', pack_path])
        
        command_logger.log_command('gdbserver', cmd_args)
        
        try:
            self.disconnect()
            
            # Log connection parameters
            command_logger.log_target_info(target, pack_path)
            command_logger.log_connection(connect_mode.value, frequency)
            
            session_options = {
                'frequency': frequency,
                'connect_mode': connect_mode.value,
                'reset_type': 'default',
            }
            
            command_logger.log("")
            command_logger.log("🔍 Scanning for debug probes...")
            
            # Get probe
            probes = ConnectHelper.get_all_connected_probes(blocking=False)
            if not probes:
                command_logger.log_error("No debug probe found", 
                    "Please check:\n"
                    "  - Debug probe is connected via USB\n"
                    "  - USB cable is data-capable (not charge-only)\n"
                    "  - udev rules are installed (Linux)\n"
                    "  - Drivers are installed (Windows)")
                return False
            
            command_logger.log(f"   Found {len(probes)} probe(s)")
            
            # Select probe
            selected_probe = None
            if probe_id:
                for p in probes:
                    if probe_id in p.unique_id:
                        selected_probe = p
                        break
            if selected_probe:
                command_logger.log(f"   Selected probe matching ID: {probe_id[:16]}...")
            else:
                command_logger.log("   ⚠️ Probe ID not found, using first available")
                    
            if not selected_probe:
                selected_probe = probes[0]
            
            # Log probe info
            command_logger.log("")
            command_logger.log_probe_info(
                probe_id=selected_probe.unique_id,
                description=selected_probe.description,
                vendor=getattr(selected_probe, 'vendor_name', ''),
                product=getattr(selected_probe, 'product_name', '')
            )
            
            command_logger.log("")
            command_logger.log("📡 Creating session...")
            command_logger.log(f"   Options: {session_options}")
            
            self._session = ConnectHelper.session_with_chosen_probe(
                unique_id=selected_probe.unique_id,
                target_override=target,
                pack=pack_path,
                options=session_options,
                blocking=False  # Don't block on probe selection
            )
            
            if self._session is None:
                command_logger.log_error("Failed to create session",
                    "The debug probe was found but session creation failed.\n"
                    "This may indicate a probe firmware issue.")
                return False
            
            command_logger.log("   Session created successfully")
            command_logger.log("")
            command_logger.log("🔗 Opening session (connecting to target)...")
            command_logger.log("   This involves:")
            command_logger.log("   - SWD/JTAG initialization")
            command_logger.log("   - Target identification (IDCODE)")
            command_logger.log("   - CoreSight discovery")
            command_logger.log("   - Debug port activation")
            
            self._session.open()
            
            self._current_target = target
            
            # Log success with target info
            duration_ms = (time.time() - start_time) * 1000
            
            command_logger.log("")
            command_logger.log("✅ Connected to target:")
            if self._session.target:
                try:
                    core_name = self._session.target.part_number or target
                    command_logger.log(f"   Part:     {core_name}")
                    command_logger.log(f"   Vendor:   {getattr(self._session.target, 'vendor', 'Unknown')}")
                    
                    # Try to get memory map
                    memory_map = self._session.target.memory_map
                    flash_regions = [r for r in memory_map if r.is_flash]
                    ram_regions = [r for r in memory_map if r.is_ram]
                    
                    if flash_regions:
                        total_flash = sum(r.length for r in flash_regions)
                        command_logger.log(f"   Flash:    {total_flash // 1024} KB")
                    if ram_regions:
                        total_ram = sum(r.length for r in ram_regions)
                        command_logger.log(f"   RAM:      {total_ram // 1024} KB")
                except Exception as e:
                    command_logger.log(f"   (Could not retrieve full target info: {e})")
            
            command_logger.log_result(True, f"Connected to {target}", duration_ms)
            return True
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            error_msg = str(e)
            error_details = traceback.format_exc()
            
            command_logger.log("")
            command_logger.log_error(f"Connection failed: {error_msg}")
            
            # Provide helpful troubleshooting based on error type
            if "No ACK" in error_msg or "no ack" in error_msg.lower():
                command_logger.log("")
                command_logger.log("🔧 Troubleshooting 'No ACK':")
                command_logger.log("   1. Check SWD wiring (SWDIO, SWCLK, GND)")
                command_logger.log("   2. Verify target has power")
                command_logger.log("   3. Try lower frequency (100000 Hz)")
                command_logger.log("   4. Try 'under-reset' connect mode")
                command_logger.log("   5. Check if target is in low-power mode")
                command_logger.log("   6. Target may have debug disabled (option bytes)")
            elif "probe" in error_msg.lower():
                command_logger.log("")
                command_logger.log("🔧 Troubleshooting probe issues:")
                command_logger.log("   1. Reconnect USB cable")
                command_logger.log("   2. Try different USB port")
                command_logger.log("   3. Update probe firmware")
            elif "target" in error_msg.lower():
                command_logger.log("")
                command_logger.log("🔧 Troubleshooting target issues:")
                command_logger.log("   1. Verify target name is correct")
                command_logger.log("   2. Check if CMSIS-Pack is loaded")
                command_logger.log("   3. Use pyocd list --targets to see available targets")
            
            # Log full traceback for debugging
            command_logger.log("")
            command_logger.log("📋 Full error traceback:")
            for line in error_details.split('\n'):
                if line.strip():
                    command_logger.log(f"   {line}")
            
            command_logger.log_result(False, "Connection failed", duration_ms)
            
            if self._session:
                try:
                    self._session.close()
                except:
                    pass
            self._session = None
            return False
    
    def disconnect(self):
        """Disconnect from target"""
        with self._lock:
            if self._session:
                try:
                    self._session.close()
                except Exception as e:
                    LOG.warning(f"Disconnect error: {e}")
                finally:
                    self._session = None
                    self._current_target = None
    
    @property
    def is_connected(self) -> bool:
        return self._session is not None and self._session.is_open
    
    def get_flash_regions(self) -> List[FlashRegion]:
        """Get flash memory regions"""
        regions = []
        if not self.is_connected:
            return regions
            
        try:
            for region in self._session.target.memory_map:
                if region.is_flash:
                    regions.append(FlashRegion(
                        start=region.start,
                        size=region.length,
                        sector_size=getattr(region, 'sector_size', 0),
                        name=region.name or 'Flash'
                    ))
        except Exception as e:
            LOG.error(f"Failed to get flash regions: {e}")
        return regions
    
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
                
            programmer = FileProgrammer(
                self._session,
                chip_erase='sector',
                trust_crc=not verify
            )
            
            if progress_callback:
                progress_callback(0.1)
            
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
                # Mark session as disconnected
                self._session = None
                self._current_target = None
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
    
    def reset(
        self,
        reset_type: ResetType = ResetType.DEFAULT,
        halt: bool = False
    ) -> bool:
        """Reset target"""
        if not self.is_connected:
            command_logger.log_error("Not connected", "Please connect to target first")
            return False
        
        start_time = time.time()
        
        # Build equivalent command
        cmd_args = ['--target', self._current_target or 'unknown']
        if reset_type != ResetType.DEFAULT:
            cmd_args.extend(['--type', reset_type.value])
        if halt:
            cmd_args.append('--halt')
        
        command_logger.log_command('reset', cmd_args)
            
        try:
            command_logger.log(f"")
            command_logger.log(f"🔄 Reset operation:")
            command_logger.log(f"   Type: {reset_type.value}")
            command_logger.log(f"   Halt: {halt}")
            
            target = self._session.target
            reset_val = None if reset_type == ResetType.DEFAULT else reset_type.value
            
            if halt:
                target.reset_and_halt(reset_val)
            else:
                target.reset(reset_val)
            
            duration_ms = (time.time() - start_time) * 1000
            command_logger.log_result(True, f"Reset ({reset_type.value})", duration_ms)
            return True
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_details = traceback.format_exc()
            
            command_logger.log_error(f"Reset failed: {e}")
            command_logger.log(f"")
            command_logger.log(f"📋 Full error traceback:")
            for line in error_details.split('\n'):
                if line.strip():
                    command_logger.log(f"   {line}")
            
            command_logger.log_result(False, "Reset failed", duration_ms)
            return False
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.disconnect()
