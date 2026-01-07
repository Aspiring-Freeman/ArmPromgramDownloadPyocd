#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probe Page - Backward Compatibility Layer

This module provides backward compatibility for existing code.
The actual implementation has been split into UI/probe/ submodule:
  - UI/probe/scanner.py: ProbeScanner thread
  - UI/probe/worker.py: ConnectWorker thread
  - UI/probe/preset_manager.py: Preset management mixin
  - UI/probe/page.py: Main ProbePage widget

For new code, prefer importing from UI.probe directly:
    from UI.probe import ProbePage, ProbeScanner, ConnectWorker
"""

# Re-export everything from the new module structure for backward compatibility
from UI.probe import (
    ProbeScanner,
    ConnectWorker,
    ProbePage,
)

__all__ = [
    'ProbeScanner',
    'ConnectWorker',
    'ProbePage',
]
