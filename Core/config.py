#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Manager

Supports both portable mode (config in project directory) and
installed mode (config in user's app data directory).
"""

import json
import logging
import platform
from typing import Any, Dict, List
from pathlib import Path

LOG = logging.getLogger(__name__)


def get_user_config_dir() -> Path:
    """
    Get user-specific configuration directory.
    
    Returns platform-appropriate config directory:
    - Windows: %APPDATA%/ArmFlashTool
    - macOS: ~/Library/Application Support/ArmFlashTool
    - Linux: ~/.config/ArmFlashTool
    """
    system = platform.system()
    
    if system == "Windows":
        base = Path.home() / "AppData" / "Roaming"
    elif system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux and others
        base = Path.home() / ".config"
    
    config_dir = base / "ArmFlashTool"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path(project_root: Path = None, portable: bool = None) -> Path:
    """
    Determine the configuration file path.
    
    Args:
        project_root: Project root directory for portable mode
        portable: Force portable mode if True, user dir if False, auto-detect if None
    
    Returns:
        Path to config.json
    """
    if portable is None:
        # Auto-detect: use portable mode if project directory is writable
        if project_root:
            test_file = project_root / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
                portable = True
            except (PermissionError, OSError):
                portable = False
        else:
            portable = False
    
    if portable and project_root:
        return project_root / "config.json"
    else:
        return get_user_config_dir() / "config.json"


class ConfigManager:
    """Application configuration manager"""
    
    DEFAULT_CONFIG = {
        "app": {"name": "ARM Flash Tool", "version": "1.0.0"},
        "pyocd": {
            "default_frequency": 1000000,
            "connect_mode": "under-reset",
            "last_target": "",
            "last_pack": "",
        },
        "ui": {"theme": "auto", "window_width": 1200, "window_height": 800},
        "flash": {
            "verify": True,
            "reset_after": True,
            "erase_before": True,
        },
        "settings": {
            "theme": "light",
            "default_frequency": 1000000,
            "connect_retries": 3,
            "pack_directory": "",
            "default_verify": True,
            "default_reset": True,
        },
        "recent_files": [],
        "recent_targets": [],
        "recent_packs": [],
    }
    
    def __init__(self, config_path: str):
        self._path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load()
        
    def _load(self):
        try:
            if self._path.exists():
                with open(self._path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                self._config = self.DEFAULT_CONFIG.copy()
                self._save()
        except Exception as e:
            LOG.error(f"Config load error: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
            
    def _save(self):
        """Save configuration with atomic operation to prevent corruption
        
        Uses temporary file + rename pattern to ensure config integrity
        even if program crashes during write.
        """
        try:
            # Write to temporary file first
            temp_path = self._path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            
            # Atomic replace: only overwrites config.json if temp write succeeded
            import os
            os.replace(temp_path, self._path)
        except Exception as e:
            LOG.error(f"Config save error: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value (supports dot notation)"""
        keys = key.split('.')
        val = self._config
        try:
            for k in keys:
                val = val[k]
            return val
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any, save: bool = True):
        """Set config value"""
        keys = key.split('.')
        cfg = self._config
        for k in keys[:-1]:
            cfg = cfg.setdefault(k, {})
        cfg[keys[-1]] = value
        if save:
            self._save()
            
    def save(self):
        self._save()
    
    @property
    def data(self) -> Dict[str, Any]:
        """Access raw config data"""
        return self._config
        
    def get_theme(self) -> str:
        return self.get('ui.theme', 'auto')
    
    def set_theme(self, theme: str):
        self.set('ui.theme', theme)
        
    def get_recent_files(self) -> List[str]:
        return self.get('recent_files', [])
    
    def add_recent_file(self, path: str, max_items: int = 10):
        recent = self.get_recent_files()
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.set('recent_files', recent[:max_items])
        
    def get_recent_targets(self) -> List[str]:
        return self.get('recent_targets', [])
    
    def add_recent_target(self, target: str, max_items: int = 10):
        recent = self.get_recent_targets()
        if target in recent:
            recent.remove(target)
        recent.insert(0, target)
        self.set('recent_targets', recent[:max_items])
        
    def get_window_geometry(self) -> tuple:
        return (
            self.get('ui.window_x'),
            self.get('ui.window_y'),
            self.get('ui.window_width', 1200),
            self.get('ui.window_height', 800)
        )
        
    def set_window_geometry(self, x: int, y: int, w: int, h: int):
        self.set('ui.window_x', x, False)
        self.set('ui.window_y', y, False)
        self.set('ui.window_width', w, False)
        self.set('ui.window_height', h, True)
        
    # Pack file history
    def get_recent_packs(self) -> List[str]:
        return self.get('recent_packs', [])
    
    def add_recent_pack(self, path: str, max_items: int = 10):
        recent = self.get_recent_packs()
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.set('recent_packs', recent[:max_items])
        
    # Last used settings
    def get_last_target(self) -> str:
        return self.get('pyocd.last_target', '')
    
    def set_last_target(self, target: str):
        self.set('pyocd.last_target', target)
        
    def get_last_pack(self) -> str:
        return self.get('pyocd.last_pack', '')
    
    def set_last_pack(self, pack: str):
        self.set('pyocd.last_pack', pack)
        
    def get_last_frequency(self) -> int:
        return self.get('pyocd.default_frequency', 1000000)
    
    def set_last_frequency(self, freq: int):
        self.set('pyocd.default_frequency', freq)
        
    # Flash settings
    def get_flash_verify(self) -> bool:
        return self.get('flash.verify', True)
    
    def set_flash_verify(self, verify: bool):
        self.set('flash.verify', verify)
        
    def get_flash_reset(self) -> bool:
        return self.get('flash.reset_after', True)
    
    def set_flash_reset(self, reset: bool):
        self.set('flash.reset_after', reset)
    
    def get_flash_address(self) -> str:
        """Get last used flash address"""
        return self.get('flash.last_address', '')
    
    def set_flash_address(self, address: str):
        """Save last used flash address"""
        self.set('flash.last_address', address)
    
    def get_flash_auto_address(self) -> bool:
        """Get auto address detection setting"""
        return self.get('flash.auto_address', True)
    
    def set_flash_auto_address(self, auto: bool):
        """Save auto address detection setting"""
        self.set('flash.auto_address', auto)


# Global singleton instance - lazy initialization
_config_instance = None

def get_config() -> ConfigManager:
    """Get the global config instance"""
    global _config_instance
    if _config_instance is None:
        from pathlib import Path
        config_path = Path(__file__).parent.parent / "config.json"
        _config_instance = ConfigManager(str(config_path))
    return _config_instance

# Convenience alias for simpler imports
config = property(lambda self: get_config())

class _ConfigProxy:
    """Proxy class to allow 'from Core.config import config' usage"""
    def __getattr__(self, name):
        return getattr(get_config(), name)
    
    def __setattr__(self, name, value):
        setattr(get_config(), name, value)

config = _ConfigProxy()