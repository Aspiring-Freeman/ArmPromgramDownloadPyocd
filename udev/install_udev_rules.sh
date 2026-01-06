#!/bin/bash
# Install udev rules for ARM debug probes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULES_FILE="$SCRIPT_DIR/99-arm-debug-probes.rules"

if [ ! -f "$RULES_FILE" ]; then
    echo "Error: Rules file not found: $RULES_FILE"
    exit 1
fi

echo "Installing udev rules for ARM debug probes..."
sudo cp "$RULES_FILE" /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Done! Please unplug and replug your debug probe."
echo ""
echo "If you still have permission issues, try:"
echo "  sudo usermod -aG plugdev $USER"
echo "Then log out and log back in."
