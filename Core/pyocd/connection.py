#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Connection management for PyOCD wrapper
Handles connect, disconnect, and probe listing operations
"""

import logging
import time
import traceback
from typing import Optional, List

# Import from local pyocd (Driver/pyOCD/pyocd)
from pyocd.core.helpers import ConnectHelper
from pyocd.core.session import Session

from Core.logger import command_logger
from Core.pyocd.base import ConnectMode, ProbeInfo, FlashRegion
from Core.chip_config import normalize_pack_path

LOG = logging.getLogger(__name__)


class ConnectionMixin:
    """Mixin class providing connection management methods"""
    
    _session: Optional[Session]
    _current_target: Optional[str]
    _lock: object  # threading.Lock
    
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
    
    def connect(
        self,
        target: str,
        probe_id: Optional[str] = None,
        frequency: int = 1000000,
        connect_mode: ConnectMode = ConnectMode.UNDER_RESET,
        pack_path: Optional[str] = None,
    ) -> bool:
        """
        Connect to target device.
        
        Note: Uses a separate lock for connection state to allow cancellation
        while preventing concurrent connect/disconnect operations.
        """
        # Use lock to prevent concurrent connect/disconnect
        with self._lock:
            return self._connect_internal(target, probe_id, frequency, connect_mode, pack_path)
    
    def _connect_internal(
        self,
        target: str,
        probe_id: Optional[str] = None,
        frequency: int = 1000000,
        connect_mode: ConnectMode = ConnectMode.UNDER_RESET,
        pack_path: Optional[str] = None,
    ) -> bool:
        """Internal connect implementation - must be called with lock held"""
        start_time = time.time()
        
        # Normalize pack path for cross-platform compatibility
        if pack_path:
            pack_path = normalize_pack_path(pack_path)
            LOG.debug(f"Using pack path: {pack_path}")
        
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
                
                if not selected_probe:
                    # 严格模式：指定了probe_id但未找到，直接报错而不是自动选择
                    command_logger.log_error("Specified probe not found",
                        f"Could not find probe with ID: {probe_id[:16]}...\n"
                        f"Available probes ({len(probes)}):")
                    for i, p in enumerate(probes, 1):
                        command_logger.log(f"  {i}. {p.unique_id} ({p.description})")
                    command_logger.log("\nTip: Please select the correct probe or remove the probe_id filter.")
                    return False
            else:
                # 未指定probe_id，使用第一个可用探针
                selected_probe = probes[0]
            
            if selected_probe:
                command_logger.log(f"   Selected probe: {selected_probe.unique_id[:16]}...")
            
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
                except Exception:
                    pass
            self._session = None
            return False
    
    def disconnect(self, force: bool = False):
        """Disconnect from target
        
        Args:
            force: If True, skip lock acquisition (use during shutdown)
        """
        if force:
            # Force disconnect without lock - used during shutdown
            self._force_close_session()
            return
            
        # Try to acquire lock with timeout to avoid hanging
        acquired = self._lock.acquire(timeout=2.0)
        try:
            self._force_close_session()
        finally:
            if acquired:
                self._lock.release()
    
    def _force_close_session(self):
        """Close session without lock - internal use only"""
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
