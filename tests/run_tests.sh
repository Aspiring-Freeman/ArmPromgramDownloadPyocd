#!/bin/bash
# Quick test script - runs fast, non-USB tests only

echo "========================================"
echo "Running Quick Safety Tests"
echo "========================================"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests excluding slow and USB tests
pytest tests/ \
    -m "not slow and not usb and not hardware" \
    -v \
    --tb=short \
    --color=yes

TEST_RESULT=$?

echo ""
echo "========================================"
if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ All quick tests passed!"
else
    echo "❌ Some tests failed (exit code: $TEST_RESULT)"
fi
echo "========================================"

exit $TEST_RESULT
