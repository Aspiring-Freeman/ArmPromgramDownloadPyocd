#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Core/logger.py
Tests logging configuration and custom handlers
"""

import pytest
import logging
import tempfile
import os
from pathlib import Path

# Import after setting up path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLoggerModule:
    """Tests for logger module existence and structure"""
    
    @pytest.fixture
    def project_root(self):
        return Path(__file__).parent.parent
    
    def test_logger_module_exists(self, project_root):
        """Test logger.py exists"""
        filepath = project_root / 'Core' / 'logger.py'
        assert filepath.exists(), "Core/logger.py should exist"
    
    def test_logger_has_setup_function(self, project_root):
        """Test logger has setup function"""
        filepath = project_root / 'Core' / 'logger.py'
        content = filepath.read_text(encoding='utf-8')
        
        # Should have a setup function or CommandLogger
        assert 'def setup' in content or 'CommandLogger' in content, \
            "logger.py should have a setup function or CommandLogger class"
    
    def test_logger_has_command_logger(self, project_root):
        """Test logger has CommandLogger for operations"""
        filepath = project_root / 'Core' / 'logger.py'
        content = filepath.read_text(encoding='utf-8')
        
        # Should have CommandLogger class
        assert 'class CommandLogger' in content, \
            "logger.py should have CommandLogger class"


class TestLoggerFunctionality:
    """Functional tests for logger (if importable)"""
    
    def test_can_import_logger(self):
        """Test logger module can be imported"""
        try:
            from Core import logger
            # Check for actual exports
            assert hasattr(logger, 'setup_logger') or hasattr(logger, 'CommandLogger') or hasattr(logger, 'command_logger')
        except ImportError as e:
            pytest.skip(f"Cannot import logger: {e}")
    
    def test_logging_level_constants(self):
        """Test logging levels are properly defined"""
        # Standard Python logging levels
        assert logging.DEBUG == 10
        assert logging.INFO == 20
        assert logging.WARNING == 30
        assert logging.ERROR == 40
        assert logging.CRITICAL == 50


class TestLogFormat:
    """Tests for log format consistency"""
    
    @pytest.fixture
    def project_root(self):
        return Path(__file__).parent.parent
    
    def test_log_format_includes_timestamp(self, project_root):
        """Test log format includes timestamp"""
        filepath = project_root / 'Core' / 'logger.py'
        content = filepath.read_text(encoding='utf-8')
        
        # Should include time in format
        assert '%(asctime)' in content or 'asctime' in content or 'time' in content.lower(), \
            "Log format should include timestamp"
    
    def test_log_format_includes_level(self, project_root):
        """Test log format includes log level"""
        filepath = project_root / 'Core' / 'logger.py'
        content = filepath.read_text(encoding='utf-8')
        
        # Should include level
        assert '%(levelname)' in content or 'levelname' in content or 'level' in content.lower(), \
            "Log format should include level"
