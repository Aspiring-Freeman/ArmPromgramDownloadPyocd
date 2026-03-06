#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Allow running as: python -m arm_flash_tool"""

import sys
from main import main

if __name__ == "__main__":
    sys.exit(main() or 0)
