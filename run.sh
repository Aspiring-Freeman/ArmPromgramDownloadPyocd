#!/bin/bash
# ARM Flash Tool startup script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Please install Python 3.8+."
    exit 1
fi

# Activate virtual environment if exists
if [ -d "Driver/pyOCD/arm_cmsis_pyocd_platform" ]; then
    source "Driver/pyOCD/arm_cmsis_pyocd_platform/bin/activate"
fi

# Check dependencies
python3 -c "import PyQt6" 2>/dev/null || {
    echo "Installing PyQt6..."
    pip install PyQt6 PyQt6-Fluent-Widgets
}

# Run application
python3 main.py "$@"
