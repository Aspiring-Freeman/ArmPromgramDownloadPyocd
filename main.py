#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARM Flash Programming Tool
Main entry point

A modern ARM chip programming tool based on PyOCD with Qt Fluent Design UI.
Uses the local PyOCD library from Driver/pyOCD/

Author: Noah
License: MIT
"""

import sys
import os
import logging
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Add local pyocd to path FIRST (use workspace's pyocd, not pip installed)
LOCAL_PYOCD_PATH = PROJECT_ROOT / "Driver" / "pyOCD"
if LOCAL_PYOCD_PATH.exists():
    sys.path.insert(0, str(LOCAL_PYOCD_PATH))

# Add project root for Core and UI modules
sys.path.insert(0, str(PROJECT_ROOT))

# High DPI support - must be set before QApplication creation
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from qfluentwidgets import FluentTranslator

from Core.pyocd_wrapper import PyOCDWrapper
from Core.config import ConfigManager
from Core.logger import setup_logger
from UI.main_window import MainWindow


def setup_high_dpi():
    """Setup high DPI support"""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def get_pack_files() -> list:
    """Get all .pack files from Package directory"""
    pack_files = []
    
    # Main Package directory
    package_dir = PROJECT_ROOT / "Package"
    if package_dir.exists():
        for pack_file in package_dir.rglob("*.pack"):
            pack_files.append(str(pack_file))
            
    # Also check pyOCD's Package folder
    pyocd_pack_dir = LOCAL_PYOCD_PATH / "Package"
    if pyocd_pack_dir.exists():
        for pack_file in pyocd_pack_dir.rglob("*.pack"):
            pack_files.append(str(pack_file))
            
    return pack_files


def main():
    """Main entry point"""
    setup_high_dpi()
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("ARM Flash Programming Tool")
    app.setApplicationVersion("1.0.0")
    
    # Set default font
    font = QFont()
    font.setFamily("Microsoft YaHei" if sys.platform == "win32" else "Noto Sans CJK SC")
    font.setPointSize(10)
    app.setFont(font)
    
    # Load configuration
    config_path = PROJECT_ROOT / "config.json"
    config = ConfigManager(str(config_path))
    
    # Setup logging
    log_level = logging.DEBUG if "--debug" in sys.argv else logging.INFO
    logger = setup_logger("ArmFlashTool", level=log_level)
    logger.info("Starting ARM Flash Programming Tool...")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Using local PyOCD from: {LOCAL_PYOCD_PATH}")
    
    # Install translator
    translator = FluentTranslator()
    app.installTranslator(translator)
    
    # Get pack files
    pack_files = get_pack_files()
    logger.info(f"Found {len(pack_files)} pack files")
    
    # Create PyOCD wrapper
    try:
        pyocd_wrapper = PyOCDWrapper(pack_paths=pack_files)
        logger.info("PyOCD wrapper initialized")
    except Exception as e:
        logger.error(f"Failed to initialize PyOCD: {e}")
        import traceback
        traceback.print_exc()
        pyocd_wrapper = PyOCDWrapper()
    
    # Create and show main window
    window = MainWindow(pyocd_wrapper, config)
    window.show()
    
    logger.info("Application started")
    
    # Run event loop
    exit_code = app.exec()
    
    # Cleanup
    pyocd_wrapper.disconnect()
    logger.info("Application exiting")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
