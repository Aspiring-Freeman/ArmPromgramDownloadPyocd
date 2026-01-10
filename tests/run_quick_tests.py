#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test runner - cross-platform
Runs fast, non-USB tests only
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run quick safety tests"""
    print("=" * 60)
    print("Running Quick Safety Tests")
    print("=" * 60)
    print()
    
    # Change to tests directory
    tests_dir = Path(__file__).parent
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-m", "not slow and not usb and not hardware",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    # Run tests
    result = subprocess.run(cmd)
    
    print()
    print("=" * 60)
    if result.returncode == 0:
        print("✅ All quick tests passed!")
    else:
        print(f"❌ Some tests failed (exit code: {result.returncode})")
    print("=" * 60)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
