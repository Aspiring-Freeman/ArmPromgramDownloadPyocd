#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Core/config.py
Tests ConfigManager for application configuration
"""

import pytest
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from Core.config import ConfigManager


class TestConfigManager:
    """Tests for ConfigManager"""
    
    def test_create_config_manager(self, temp_dir):
        """Test creating a ConfigManager"""
        config_path = temp_dir / "test_config.json"
        manager = ConfigManager(str(config_path))
        assert manager is not None
    
    def test_config_manager_creates_default_file(self, temp_dir):
        """Test that ConfigManager creates config file with defaults"""
        config_path = temp_dir / "test_config.json"
        manager = ConfigManager(str(config_path))
        
        # File should be created
        assert config_path.exists()
    
    def test_get_set_value(self, temp_dir):
        """Test getting and setting values"""
        config_path = temp_dir / "test_config.json"
        manager = ConfigManager(str(config_path))
        
        # Set a value
        manager.set("test.key", "test_value")
        
        # Get the value back
        value = manager.get("test.key")
        assert value == "test_value"
    
    def test_get_with_default(self, temp_dir):
        """Test getting nonexistent key returns default"""
        config_path = temp_dir / "test_config.json"
        manager = ConfigManager(str(config_path))
        
        value = manager.get("nonexistent.key", default="default_value")
        assert value == "default_value"
    
    def test_nested_path_access(self, temp_dir):
        """Test accessing nested configuration paths"""
        config_path = temp_dir / "test_config.json"
        manager = ConfigManager(str(config_path))
        
        # Set nested value
        manager.set("level1.level2.level3", "deep_value")
        
        # Get nested value
        value = manager.get("level1.level2.level3")
        assert value == "deep_value"
    
    def test_config_persistence(self, temp_dir):
        """Test that config persists across manager instances"""
        config_path = temp_dir / "test_config.json"
        
        # Set value with first manager
        manager1 = ConfigManager(str(config_path))
        manager1.set("persistent.key", "persistent_value")
        
        # Read with second manager
        manager2 = ConfigManager(str(config_path))
        value = manager2.get("persistent.key")
        
        assert value == "persistent_value"
    
    def test_set_various_types(self, temp_dir):
        """Test setting different value types"""
        config_path = temp_dir / "test_config.json"
        manager = ConfigManager(str(config_path))
        
        # String
        manager.set("string_key", "string_value")
        assert manager.get("string_key") == "string_value"
        
        # Integer
        manager.set("int_key", 42)
        assert manager.get("int_key") == 42
        
        # Boolean
        manager.set("bool_key", True)
        assert manager.get("bool_key") is True
        
        # List
        manager.set("list_key", [1, 2, 3])
        assert manager.get("list_key") == [1, 2, 3]
        
        # Dict
        manager.set("dict_key", {"nested": "value"})
        assert manager.get("dict_key") == {"nested": "value"}
    
    def test_handles_corrupted_config_file(self, temp_dir):
        """Test handling of corrupted config file"""
        config_path = temp_dir / "corrupted_config.json"
        
        # Write corrupted JSON
        with open(config_path, 'w') as f:
            f.write("{invalid json")
        
        # Should handle gracefully and create fresh config
        manager = ConfigManager(str(config_path))
        # Should be able to use normally after recovery
        manager.set("recovery.test", "works")
        assert manager.get("recovery.test") == "works"


class TestConfigManagerDefaults:
    """Tests for ConfigManager default values"""
    
    def test_default_config_structure(self, temp_dir):
        """Test that default config has expected structure"""
        config_path = temp_dir / "test_config.json"
        manager = ConfigManager(str(config_path))
        
        # Check for common expected keys (adjust based on actual defaults)
        # These assertions should match your actual default config structure
        config_data = json.loads(config_path.read_text())
        assert isinstance(config_data, dict)
