#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reset operations for PyOCD wrapper
Handles reset method
"""

import logging
import time
import traceback
from typing import Optional

from pyocd.core.session import Session

from Core.logger import command_logger
from Core.pyocd.base import ResetType

LOG = logging.getLogger(__name__)


class ResetMixin:
    """Mixin class providing reset methods"""
    
    _session: Optional[Session]
    _current_target: Optional[str]
    is_connected: bool
    
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
