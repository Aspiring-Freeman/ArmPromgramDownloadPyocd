#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chip Configuration Manager
Manages chip presets for different vendors and chip families
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

LOG = logging.getLogger(__name__)


class ChipVendor(Enum):
    """Supported chip vendors"""
    ST = "STMicroelectronics"
    GD = "GigaDevice"
    MM = "MindMotion"
    NXP = "NXP"
    NORDIC = "Nordic"
    MICROCHIP = "Microchip"
    INFINEON = "Infineon"
    NUVOTON = "Nuvoton"
    ARTERY = "Artery"
    APM = "APM/Geehy"
    WCH = "WCH"
    UNKNOWN = "Unknown"


@dataclass
class ChipConfig:
    """Chip configuration preset"""
    # Basic info
    name: str                           # Config name (e.g., "STM32H503 Dev Board")
    vendor: str                         # Vendor name
    chip_family: str                    # Chip family (e.g., "STM32H5")
    target: str                         # PyOCD target name (e.g., "stm32h503cbtx")
    
    # Memory configuration
    flash_start: int = 0x08000000       # Flash start address
    flash_size: int = 0                 # Flash size in bytes (0 = auto detect)
    ram_start: int = 0x20000000         # RAM start address
    ram_size: int = 0                   # RAM size in bytes (0 = auto detect)
    
    # Connection settings
    default_frequency: int = 1000000    # Default SWD frequency
    connect_mode: str = "under-reset"   # Connect mode
    reset_type: str = "default"         # Reset type
    
    # Pack info
    pack_file: str = ""                 # CMSIS-Pack file path (relative or absolute)
    
    # Additional options
    options: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    description: str = ""               # Description
    notes: str = ""                     # User notes
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChipConfig':
        """
        Create ChipConfig from dictionary with validation.
        
        Args:
            data: Dictionary with chip configuration
            
        Returns:
            ChipConfig instance
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Handle older configs without all fields
        defaults = {
            'name': 'Unknown',
            'vendor': 'Unknown',
            'chip_family': '',
            'target': 'cortex_m',
            'flash_start': 0x08000000,
            'flash_size': 0,
            'ram_start': 0x20000000,
            'ram_size': 0,
            'default_frequency': 1000000,
            'connect_mode': 'under-reset',
            'reset_type': 'default',
            'pack_file': '',
            'options': {},
            'description': '',
            'notes': ''
        }
        defaults.update(data)
        
        # Validate required fields
        if not defaults.get('target'):
            raise ValueError("'target' field is required and cannot be empty")
        
        # Validate and normalize flash_start
        flash_start = defaults.get('flash_start', 0x08000000)
        if isinstance(flash_start, str):
            try:
                flash_start = int(flash_start, 16) if flash_start.lower().startswith('0x') else int(flash_start)
            except ValueError:
                raise ValueError(f"Invalid flash_start address: {flash_start}")
        if not (0x00000000 <= flash_start <= 0xFFFFFFFF):
            raise ValueError(f"flash_start out of range: 0x{flash_start:08X}")
        defaults['flash_start'] = flash_start
        
        # Validate and normalize ram_start
        ram_start = defaults.get('ram_start', 0x20000000)
        if isinstance(ram_start, str):
            try:
                ram_start = int(ram_start, 16) if ram_start.lower().startswith('0x') else int(ram_start)
            except ValueError:
                raise ValueError(f"Invalid ram_start address: {ram_start}")
        defaults['ram_start'] = ram_start
        
        # Validate frequency
        freq = defaults.get('default_frequency', 1000000)
        if isinstance(freq, str):
            freq = int(freq)
        if not (10000 <= freq <= 50000000):  # 10kHz to 50MHz
            LOG.warning(f"Frequency {freq} out of typical range, using default")
            freq = 1000000
        defaults['default_frequency'] = freq
        
        # Validate connect_mode
        valid_modes = ['halt', 'pre-reset', 'under-reset', 'attach']
        if defaults.get('connect_mode') not in valid_modes:
            LOG.warning(f"Invalid connect_mode '{defaults.get('connect_mode')}', using 'under-reset'")
            defaults['connect_mode'] = 'under-reset'
        
        # Only pass fields that exist in the dataclass
        valid_fields = {k: v for k, v in defaults.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


# Built-in presets for common chips
BUILTIN_PRESETS: Dict[str, ChipConfig] = {
    # STMicroelectronics
    "stm32f1": ChipConfig(
        name="STM32F1 Series",
        vendor="STMicroelectronics",
        chip_family="STM32F1",
        target="stm32f103c8",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="STM32F1 series (Cortex-M3)",
    ),
    "stm32f4": ChipConfig(
        name="STM32F4 Series",
        vendor="STMicroelectronics",
        chip_family="STM32F4",
        target="stm32f407vg",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=2000000,
        description="STM32F4 series (Cortex-M4F)",
    ),
    "stm32h5": ChipConfig(
        name="STM32H5 Series",
        vendor="STMicroelectronics",
        chip_family="STM32H5",
        target="stm32h503cbtx",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        connect_mode="under-reset",
        description="STM32H5 series (Cortex-M33)",
        notes="Requires CMSIS-Pack: Keil.STM32H5xx_DFP",
    ),
    "stm32h7": ChipConfig(
        name="STM32H7 Series",
        vendor="STMicroelectronics",
        chip_family="STM32H7",
        target="stm32h743xi",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=2000000,
        description="STM32H7 series (Cortex-M7)",
    ),
    "stm32g0": ChipConfig(
        name="STM32G0 Series",
        vendor="STMicroelectronics",
        chip_family="STM32G0",
        target="stm32g071rb",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="STM32G0 series (Cortex-M0+)",
    ),
    "stm32g4": ChipConfig(
        name="STM32G4 Series",
        vendor="STMicroelectronics",
        chip_family="STM32G4",
        target="stm32g474re",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=2000000,
        description="STM32G4 series (Cortex-M4F)",
    ),
    "stm32l4": ChipConfig(
        name="STM32L4 Series",
        vendor="STMicroelectronics",
        chip_family="STM32L4",
        target="stm32l476rg",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="STM32L4 series (Cortex-M4F, Low Power)",
    ),
    
    # GigaDevice
    "gd32f1": ChipConfig(
        name="GD32F1 Series",
        vendor="GigaDevice",
        chip_family="GD32F1",
        target="gd32f103c8",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="GD32F1 series (STM32F1 compatible)",
    ),
    "gd32f3": ChipConfig(
        name="GD32F3 Series",
        vendor="GigaDevice",
        chip_family="GD32F3",
        target="gd32f303cc",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="GD32F3 series (Cortex-M4)",
    ),
    "gd32e1": ChipConfig(
        name="GD32E1 Series",
        vendor="GigaDevice",
        chip_family="GD32E1",
        target="gd32e103c8",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="GD32E1 series (Enhanced)",
    ),
    
    # MindMotion
    "mm32f0": ChipConfig(
        name="MM32F0 Series",
        vendor="MindMotion",
        chip_family="MM32F0",
        target="mm32f031c6",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="MM32F0 series (Cortex-M0)",
    ),
    "mm32spin": ChipConfig(
        name="MM32SPIN Series",
        vendor="MindMotion",
        chip_family="MM32SPIN",
        target="mm32spin27pf",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="MM32SPIN series (Motor Control)",
    ),
    
    # NXP
    "lpc1768": ChipConfig(
        name="LPC1768",
        vendor="NXP",
        chip_family="LPC17xx",
        target="lpc1768",
        flash_start=0x00000000,
        ram_start=0x10000000,
        default_frequency=1000000,
        description="NXP LPC1768 (Cortex-M3)",
    ),
    "lpc55s69": ChipConfig(
        name="LPC55S69",
        vendor="NXP",
        chip_family="LPC55xx",
        target="lpc55s69",
        flash_start=0x00000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="NXP LPC55S69 (Cortex-M33, TrustZone)",
    ),
    "mimxrt1060": ChipConfig(
        name="i.MX RT1060",
        vendor="NXP",
        chip_family="i.MX RT",
        target="mimxrt1060",
        flash_start=0x60000000,
        ram_start=0x20200000,
        default_frequency=1000000,
        description="NXP i.MX RT1060 (Cortex-M7, FlexSPI)",
    ),
    
    # Nordic
    "nrf52832": ChipConfig(
        name="nRF52832",
        vendor="Nordic",
        chip_family="nRF52",
        target="nrf52832",
        flash_start=0x00000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="Nordic nRF52832 (Cortex-M4F, BLE)",
    ),
    "nrf52840": ChipConfig(
        name="nRF52840",
        vendor="Nordic",
        chip_family="nRF52",
        target="nrf52840",
        flash_start=0x00000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="Nordic nRF52840 (Cortex-M4F, BLE/Thread/Zigbee)",
    ),
    
    # Artery (雅特力)
    "at32f403a": ChipConfig(
        name="AT32F403A",
        vendor="Artery",
        chip_family="AT32F403A",
        target="at32f403acgu7",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="Artery AT32F403A (Cortex-M4F)",
    ),
    "at32f435": ChipConfig(
        name="AT32F435",
        vendor="Artery",
        chip_family="AT32F435",
        target="at32f435zmt7",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=2000000,
        description="Artery AT32F435 (Cortex-M4F, High Performance)",
    ),
    
    # APM/Geehy (极海)
    "apm32f1": ChipConfig(
        name="APM32F1 Series",
        vendor="APM/Geehy",
        chip_family="APM32F1",
        target="apm32f103c8",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="APM32F1 series (STM32F1 compatible)",
    ),
    
    # WCH (沁恒)
    "ch32v3": ChipConfig(
        name="CH32V3 Series",
        vendor="WCH",
        chip_family="CH32V3",
        target="ch32v307",
        flash_start=0x08000000,
        ram_start=0x20000000,
        default_frequency=1000000,
        description="WCH CH32V3 series (RISC-V)",
        notes="Requires WCH-specific tools for RISC-V",
    ),
}


class ChipConfigManager:
    """Manages chip configuration presets"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self._config_dir = config_dir or Path.home() / ".arm_flash_tool" / "chip_configs"
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        self._user_configs: Dict[str, ChipConfig] = {}
        self._load_user_configs()
    
    def _load_user_configs(self):
        """Load user-defined configs from disk"""
        config_file = self._config_dir / "user_configs.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, cfg_data in data.items():
                        self._user_configs[key] = ChipConfig.from_dict(cfg_data)
                LOG.info(f"Loaded {len(self._user_configs)} user chip configs")
            except Exception as e:
                LOG.error(f"Failed to load user configs: {e}")
    
    def _save_user_configs(self):
        """Save user-defined configs to disk"""
        config_file = self._config_dir / "user_configs.json"
        try:
            data = {key: cfg.to_dict() for key, cfg in self._user_configs.items()}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            LOG.info(f"Saved {len(self._user_configs)} user chip configs")
        except Exception as e:
            LOG.error(f"Failed to save user configs: {e}")
    
    def get_all_presets(self) -> Dict[str, ChipConfig]:
        """Get all presets (builtin + user)"""
        all_configs = dict(BUILTIN_PRESETS)
        all_configs.update(self._user_configs)
        return all_configs
    
    def get_builtin_presets(self) -> Dict[str, ChipConfig]:
        """Get only builtin presets"""
        return dict(BUILTIN_PRESETS)
    
    def get_user_presets(self) -> Dict[str, ChipConfig]:
        """Get only user presets"""
        return dict(self._user_configs)
    
    def get_preset(self, key: str) -> Optional[ChipConfig]:
        """Get a specific preset"""
        if key in self._user_configs:
            return self._user_configs[key]
        return BUILTIN_PRESETS.get(key)
    
    def get_presets_by_vendor(self, vendor: str) -> Dict[str, ChipConfig]:
        """Get presets filtered by vendor"""
        all_configs = self.get_all_presets()
        return {k: v for k, v in all_configs.items() 
                if v.vendor.lower() == vendor.lower()}
    
    def get_vendors(self) -> List[str]:
        """Get list of all vendors"""
        all_configs = self.get_all_presets()
        vendors = set(cfg.vendor for cfg in all_configs.values())
        return sorted(vendors)
    
    def add_user_preset(self, key: str, config: ChipConfig):
        """Add or update a user preset"""
        self._user_configs[key] = config
        self._save_user_configs()
    
    def delete_user_preset(self, key: str) -> bool:
        """Delete a user preset"""
        if key in self._user_configs:
            del self._user_configs[key]
            self._save_user_configs()
            return True
        return False
    
    def export_preset(self, key: str, file_path: Path) -> bool:
        """Export a preset to JSON file"""
        config = self.get_preset(key)
        if not config:
            return False
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            LOG.error(f"Failed to export preset: {e}")
            return False
    
    def import_preset(self, file_path: Path, key: Optional[str] = None) -> Optional[str]:
        """Import a preset from JSON file. Returns the key if successful.
        Supports both single preset format and multiple presets format.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if it's a single preset (must have 'name' and 'target')
            if isinstance(data, dict) and 'name' in data and 'target' in data:
                # Single preset format
                config = ChipConfig.from_dict(data)
                
                # Generate key if not provided
                if not key:
                    key = f"user_{config.target}_{config.chip_family}".lower().replace(" ", "_")
                
                self._user_configs[key] = config
                self._save_user_configs()
                LOG.info(f"Imported single preset: {key}")
                return key
            elif isinstance(data, dict):
                # Multiple presets format - import all
                # Validate that values look like chip configs (must have 'target' field)
                count = 0
                first_key = None
                for preset_key, cfg_data in data.items():
                    # Skip if not a valid chip config dict
                    if not isinstance(cfg_data, dict) or 'target' not in cfg_data:
                        LOG.debug(f"Skipping invalid entry: {preset_key}")
                        continue
                    try:
                        self._user_configs[preset_key] = ChipConfig.from_dict(cfg_data)
                        if first_key is None:
                            first_key = preset_key
                        count += 1
                    except Exception as e:
                        LOG.warning(f"Failed to import preset {preset_key}: {e}")
                
                if count > 0:
                    self._save_user_configs()
                    LOG.info(f"Imported {count} presets from file")
                    return first_key
                else:
                    LOG.error("No valid chip presets found in file")
                    return None
            else:
                LOG.error("Invalid file format: expected JSON object")
                return None
                
        except json.JSONDecodeError as e:
            LOG.error(f"Invalid JSON file: {e}")
            return None
        except Exception as e:
            LOG.error(f"Failed to import preset: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def export_all_user_presets(self, file_path: Path) -> bool:
        """Export all user presets to a single JSON file"""
        try:
            data = {key: cfg.to_dict() for key, cfg in self._user_configs.items()}
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            LOG.error(f"Failed to export all presets: {e}")
            return False
    
    def import_all_presets(self, file_path: Path, overwrite: bool = False) -> int:
        """Import multiple presets from JSON file. Returns count of imported presets.
        Supports both single preset format and multiple presets format.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                LOG.error("Invalid file format: expected JSON object")
                return 0
            
            count = 0
            
            # Check if it's a single preset (must have 'name' and 'target')
            if 'name' in data and 'target' in data:
                # Single preset format
                config = ChipConfig.from_dict(data)
                key = f"user_{config.target}_{config.chip_family}".lower().replace(" ", "_")
                if overwrite or key not in self._user_configs:
                    self._user_configs[key] = config
                    count = 1
            else:
                # Multiple presets format - validate each entry
                for key, cfg_data in data.items():
                    # Skip if not a valid chip config dict
                    if not isinstance(cfg_data, dict) or 'target' not in cfg_data:
                        continue
                    if not overwrite and key in self._user_configs:
                        continue
                    try:
                        self._user_configs[key] = ChipConfig.from_dict(cfg_data)
                        count += 1
                    except Exception as e:
                        LOG.warning(f"Failed to import preset {key}: {e}")
            
            if count > 0:
                self._save_user_configs()
            return count
            
        except json.JSONDecodeError as e:
            LOG.error(f"Invalid JSON file: {e}")
            return 0
        except Exception as e:
            LOG.error(f"Failed to import presets: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def create_config_from_current(
        self,
        name: str,
        target: str,
        vendor: str = "Unknown",
        chip_family: str = "",
        flash_start: int = 0x08000000,
        frequency: int = 1000000,
        connect_mode: str = "under-reset",
        pack_file: str = "",
        description: str = "",
    ) -> ChipConfig:
        """Create a new config from current settings"""
        return ChipConfig(
            name=name,
            vendor=vendor,
            chip_family=chip_family or target.split("_")[0] if "_" in target else target[:8],
            target=target,
            flash_start=flash_start,
            default_frequency=frequency,
            connect_mode=connect_mode,
            pack_file=pack_file,
            description=description,
        )


# Convenience function to get flash start address for common vendors
def get_default_flash_start(vendor_or_target: str) -> int:
    """Get default flash start address based on vendor or target name"""
    vendor_lower = vendor_or_target.lower()
    
    # Check by vendor
    if any(x in vendor_lower for x in ['stm32', 'gd32', 'mm32', 'at32', 'apm32', 'ch32', 'hk32']):
        return 0x08000000
    elif any(x in vendor_lower for x in ['nrf', 'nordic']):
        return 0x00000000
    elif any(x in vendor_lower for x in ['lpc', 'nxp']):
        return 0x00000000
    elif 'mimxrt' in vendor_lower:
        return 0x60000000  # FlexSPI
    elif any(x in vendor_lower for x in ['sam', 'atmel', 'microchip']):
        return 0x00000000
    
    # Default to STM32-style
    return 0x08000000
