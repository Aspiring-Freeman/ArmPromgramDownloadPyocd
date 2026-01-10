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
from typing import Tuple, Optional

from version import __version__, __author__

# Project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Local PyOCD path
LOCAL_PYOCD_PATH = PROJECT_ROOT / "Driver" / "pyOCD"

# Minimum required versions for dependencies
MIN_VERSIONS = {
    "PyQt6": (6, 4, 0),
    "qfluentwidgets": (1, 4, 0),
}


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse version string to tuple of integers"""
    try:
        # Handle versions like "1.4.0", "6.4.2", "1.4.0.post1"
        parts = version_str.split('.')
        result = []
        for part in parts[:3]:  # Only take first 3 parts
            # Remove any non-numeric suffix
            num = ''.join(c for c in part if c.isdigit())
            if num:
                result.append(int(num))
        return tuple(result) if result else (0, 0, 0)
    except Exception:
        return (0, 0, 0)


def check_dependencies() -> bool:
    """
    Check if required dependencies are installed with compatible versions.
    
    Returns:
        True if all dependencies are satisfied, False otherwise
    """
    all_ok = True
    
    # Check PyQt6
    try:
        from PyQt6.QtCore import PYQT_VERSION_STR
        version = parse_version(PYQT_VERSION_STR)
        min_ver = MIN_VERSIONS["PyQt6"]
        if version < min_ver:
            print(f"⚠️  PyQt6 version {PYQT_VERSION_STR} is below minimum {'.'.join(map(str, min_ver))}")
            all_ok = False
    except ImportError:
        print("❌ PyQt6 is not installed. Please install: pip install PyQt6>=6.4.0")
        return False
    
    # Check qfluentwidgets
    try:
        import qfluentwidgets
        version_str = getattr(qfluentwidgets, '__version__', '0.0.0')
        version = parse_version(version_str)
        min_ver = MIN_VERSIONS["qfluentwidgets"]
        if version < min_ver:
            print(f"⚠️  qfluentwidgets version {version_str} is below minimum {'.'.join(map(str, min_ver))}")
            print("   Some UI features may not work correctly.")
            print("   Recommended: pip install qfluentwidgets>=1.4.0")
            # Don't fail, just warn - older versions may still work
    except ImportError:
        print("❌ qfluentwidgets is not installed. Please install: pip install qfluentwidgets>=1.4.0")
        return False
    
    return all_ok


def check_virtual_env():
    """Check if running in virtual environment and warn if not"""
    in_venv = hasattr(sys, 'real_prefix') or \
               (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if not in_venv:
        print("⚠️  Warning: Not running in a virtual environment!")
        print("   Some USB/HID dependencies may not work correctly.")
        print("   Recommended: Create and activate a venv first.")
        print()


def check_pyocd_version():
    """Check and display vendored pyOCD version"""
    try:
        from version import get_pyocd_version
        pyocd_ver = get_pyocd_version()
        print(f"[INFO] Vendored PyOCD: {pyocd_ver}")
        
        # Check if version is too old or incompatible
        if "unknown" in pyocd_ver.lower():
            print("⚠️  Warning: Could not determine PyOCD version.")
            print("   Some features may not work as expected.")
    except Exception as e:
        print(f"⚠️  Warning: Error checking PyOCD version: {e}")


def check_pyocd_submodule() -> bool:
    """
    Check if local PyOCD submodule is properly initialized.
    
    Returns:
        True if PyOCD is available (local or fallback), False if neither works
    """
    # First, try to load custom PyOCD path from config
    custom_pyocd_path = get_custom_pyocd_path()
    
    if custom_pyocd_path:
        pyocd_path = Path(custom_pyocd_path)
        # Check if custom path is valid
        pyocd_init = pyocd_path / "pyocd" / "__init__.py"
        pyocd_direct = pyocd_path / "__init__.py"
        
        if pyocd_init.exists():
            sys.path.insert(0, str(pyocd_path))
            print(f"[OK] Using custom PyOCD path: {pyocd_path}")
            return True
        elif pyocd_direct.exists() and "pyocd" in str(pyocd_path).lower():
            # The path itself is the pyocd module
            sys.path.insert(0, str(pyocd_path.parent))
            print(f"[OK] Using custom PyOCD module: {pyocd_path}")
            return True
        else:
            print(f"[WARN] Custom PyOCD path invalid: {pyocd_path}")
            print("  Falling back to default...")
    
    # Check for essential PyOCD files in local path
    pyocd_init = LOCAL_PYOCD_PATH / "pyocd" / "__init__.py"
    pyocd_main = LOCAL_PYOCD_PATH / "pyocd" / "__main__.py"
    
    if LOCAL_PYOCD_PATH.exists() and pyocd_init.exists() and pyocd_main.exists():
        # Local PyOCD is available
        sys.path.insert(0, str(LOCAL_PYOCD_PATH))
        return True
    
    # Local PyOCD not available, print warning
    print("=" * 70)
    print("[WARN] WARNING: Local PyOCD submodule not found or incomplete!")
    print("=" * 70)
    print(f"\nExpected location: {LOCAL_PYOCD_PATH}")
    print("\nThis project uses a local PyOCD version for consistency.")
    print("Please initialize the submodule with:")
    print("\n    git submodule update --init --recursive")
    print("\nOr clone with submodules:")
    print("\n    git clone --recurse-submodules <repository-url>")
    print("\n" + "=" * 70)
    
    # Try to fall back to pip-installed pyocd
    try:
        import pyocd
        print("\n[OK] Fallback: Using pip-installed PyOCD instead.")
        print(f"  Version: {getattr(pyocd, '__version__', 'unknown')}")
        print("  Note: For best compatibility, please initialize the local submodule.\n")
        return True
    except ImportError:
        print("\n[ERROR] No PyOCD installation found!")
        print("  Please either:")
        print("    1. Initialize the submodule: git submodule update --init --recursive")
        print("    2. Install PyOCD via pip: pip install pyocd")
        print("    3. Set custom PyOCD path in Settings")
        print("")
        return False


def get_custom_pyocd_path() -> str:
    """
    Get custom PyOCD path from config file (before full config load).
    
    Returns:
        Custom PyOCD path string, or empty string if not set
    """
    import json
    
    # Try portable config first
    config_path = PROJECT_ROOT / "config.json"
    if not config_path.exists():
        # Try user config directory
        import platform
        system = platform.system()
        if system == "Windows":
            config_path = Path.home() / "AppData" / "Roaming" / "ArmFlashTool" / "config.json"
        elif system == "Darwin":
            config_path = Path.home() / "Library" / "Application Support" / "ArmFlashTool" / "config.json"
        else:
            config_path = Path.home() / ".config" / "ArmFlashTool" / "config.json"
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get("settings", {}).get("pyocd_path", "")
        except Exception:
            pass
    
    return ""


# Check PyOCD availability before proceeding
if not check_pyocd_submodule():
    print("Cannot start application without PyOCD. Exiting.")
    sys.exit(1)

# Check other dependencies
if not check_dependencies():
    print("Missing required dependencies. Exiting.")
    sys.exit(1)

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
from Core.config import ConfigManager, get_config_path
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
    # Environment checks
    check_virtual_env()
    check_pyocd_version()
    
    setup_high_dpi()
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("ARM Flash Programming Tool")
    app.setApplicationVersion(__version__)
    
    # Set default font
    font = QFont()
    font.setFamily("Microsoft YaHei" if sys.platform == "win32" else "Noto Sans CJK SC")
    font.setPointSize(10)
    app.setFont(font)
    
    # Load configuration
    # Use portable mode (config in project dir) if writable, otherwise use user config dir
    config_path = get_config_path(PROJECT_ROOT)
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
