# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-01-10

### Added
- **Tooltip Helper Module**: New `UI/tooltip_helper.py` for theme-aware tooltips
  - Automatically adapts tooltip colors to light/dark theme
  - Centralized tooltip styling across all UI pages
- **UI Theme Tests**: Comprehensive theme compatibility tests
  - `tests/test_ui_theme.py` - 30+ test cases for theme handling
  - Validates transparent backgrounds, dialog styling, tooltip usage
- **Integration Tests**: New `tests/test_integration.py` for project structure validation
- **Logger Tests**: New `tests/test_logger.py` for logging module tests

### Changed
- **Auto-disconnect on Config Change**: Any configuration change while connected now auto-disconnects
  - File import: Disconnect when browsing/changing config file
  - Preset selection: Disconnect when preset changes
  - Pack import: Disconnect when device selection changes
  - Connection options: Disconnect when target/frequency/mode changes
  - Clear visual feedback with warning messages
- **Improved Theme Handling**: All UI pages now use TooltipHelper for consistent styling
- **Settings Page**: Better theme initialization and label visibility in dark mode
- **Chip Config Page**: Improved theme compatibility

### Fixed
- Config changes while connected not triggering disconnect
- Preset changes not requiring re-apply before reconnection
- Theme styling issues in dialogs and tooltips
- Label visibility in dark mode across multiple pages

## [1.4.0] - 2026-01-10

### Added
- **CMSIS-Pack Parser**: New `Core/pack_parser.py` module for parsing CMSIS-Pack (.pack) files
  - Extract device information (flash start, flash size, RAM info)
  - Support for Pack vendor and version info
- **Chip Detection Feature**: Detect connected chip model via CPUID register
  - New `ChipDetectDialog` for chip detection with configurable options
  - Reads CPUID (0xE000ED00), parses core type and architecture
  - Matches detected chip against Pack targets
  - Clear separation of "Chip Info", "Pack Targets", and "Current Config" in results
- **UI Redesign**: Probe page chip configuration with three RadioButton sources
  - File import: Load configuration from JSON file
  - Preset selection: Choose from saved presets
  - Pack import: Import from CMSIS-Pack device definitions
- **Erase Page Improvements**:
  - Added comprehensive chip configuration display card
  - Sector information display with address ranges
  - Address range validation with warnings
  - Auto-update sector info based on chip config
- **Preset Management**:
  - Delete preset button with confirmation dialog
  - Export dialog "use default filename" checkbox
  - Preset name auto-sync with export filename

### Changed
- Target combo increased width (200 → 250) for better readability
- Recent files display shortened paths with ellipsis for long paths
- Flash address now correctly uses Pack-sourced values in saved presets

### Fixed
- Duplicate signal connections in main_window.py (config_applied, preset_selected, theme_changed)
- qfluentwidgets ComboBox itemData() returns None - implemented `_preset_keys` dict mapping
- Theme styling for ChipDetectDialog in light/dark modes
- Recent files selection using `_recent_files_map` for full path lookup
- Removed unused imports (SpinBox in flash_page.py)

## [1.3.0] - 2026-01-07

### Added
- FM33LG04X chip preset for FMSH (复旦微) microcontrollers
- Auto-detection for FMSH chips (fm33/fm prefix)
- Cross-platform relative path support for pack files and PyOCD directory
  - Paths stored as relative in config.json for portability
  - Automatic conversion between relative and absolute paths

### Changed
- **UI Enhancement**: All frequency ComboBox changed to EditableComboBox
  - Supports custom frequency input (e.g., "3.5 MHz", "600 kHz")
  - Added 8 MHz and 10 MHz preset options
- **UI Enhancement**: Vendor ComboBox changed to EditableComboBox
  - Supports custom vendor input (no longer limited to preset list)
  - Removed "其他" option (can now type any vendor directly)
- Fixed theme styling for SavePresetDialog in dark mode
- Fixed settings page theme initialization order
- Improved pack path normalization for Windows/Linux compatibility

### Fixed
- Labels invisible in dark mode for Settings page and SavePresetDialog
- Windows absolute paths not working on Linux (and vice versa)

## [1.2.0] - 2026-01-07

### Added
- New unit tests for pyocd_wrapper module (111 tests total, 100% pass rate)
  - `test_pyocd_wrapper.py` - PyOCD wrapper tests with mocks

### Changed
- **[P1 Refactoring]** Split `Core/pyocd_wrapper.py` (888 lines) into modular subpackage:
  - `Core/pyocd/__init__.py` - Public API exports
  - `Core/pyocd/base.py` - Enums and dataclasses (ResetType, EraseMode, ConnectMode, ProbeInfo, FlashRegion)
  - `Core/pyocd/connection.py` - Connection management (connect, disconnect, list_probes)
  - `Core/pyocd/flash.py` - Flash programming (flash, flash_file)
  - `Core/pyocd/erase.py` - Erase operations (erase, mass_erase, erase_sector, erase_range)
  - `Core/pyocd/reset.py` - Reset operations (reset)
  - `Core/pyocd/wrapper.py` - Main PyOCDWrapper class combining mixins
- **[P1 Refactoring]** Split `UI/probe_page.py` (878 lines) into modular subpackage:
  - `UI/probe/__init__.py` - Public API exports
  - `UI/probe/scanner.py` - ProbeScanner background thread
  - `UI/probe/worker.py` - ConnectWorker background thread
  - `UI/probe/preset_manager.py` - PresetManagerMixin for preset operations
  - `UI/probe/page.py` - Main ProbePage widget
- Backward compatibility maintained - original import paths still work

### Notes
- This is a pure refactoring release, no functional changes
- All existing code using `from Core.pyocd_wrapper import ...` continues to work
- New code can use `from Core.pyocd import ...` for cleaner imports

## [1.1.0] - 2026-01-06

### Added
- Unit tests for core modules (83 tests, 100% pass rate)
  - `test_chip_config.py` - Chip configuration tests
  - `test_config.py` - Application config tests
  - `test_utils.py` - Utility function tests
- Dependency version checking at startup (PyQt6, qfluentwidgets)
- User config directory support for packaged applications
  - Windows: `%APPDATA%/ArmFlashTool`
  - macOS: `~/Library/Application Support/ArmFlashTool`
  - Linux: `~/.config/ArmFlashTool`
- Editable vendor combo box for custom chip vendors

### Changed
- Preset auto-apply when selected (no need to click "Apply" button)
- Improved notification system - single notification per operation
- Force disconnect with timeout for graceful shutdown

### Fixed
- Fixed bare `except:` statements for proper exception handling
- Fixed thread safety in CommandLogger (`_callbacks.copy()`)
- Fixed `flash_start = 0x00000000` not being applied (was treated as False)
- Fixed duplicate notifications on flash/erase operations
- Fixed preset not applying to probe page from chip config page
- Fixed program hang on Ctrl+C during connection
- Fixed spelling: `Package/Unkown` → `Package/Unknown`

### Improved
- Enhanced `.gitignore` (added Backup/, Mcu_Hex_Directories/, *.hex, *.bin, *.elf)
- Better error notifications (only show InfoBar on failure, StateToolTip on success)
- More robust shutdown sequence in closeEvent

## [1.0.0] - 2026-01-06

### Added
- Initial release of ARM Flash Programming Tool
- PyQt6 + Fluent Widgets modern UI
- Local PyOCD integration (v0.36.0)
- Multi-probe support (CMSIS-DAP, ST-Link, J-Link)
- Multi-vendor chip support (STM32, GD32, MM32, NXP, Nordic, Artery, etc.)
- CMSIS-Pack file support for chip definitions
- Flash programming with verification
- Multiple erase modes (chip erase, sector erase, mass erase)
- Chip preset configuration system
  - Save/load chip configurations
  - Import/export to JSON files
  - Project-level preset management (Doc/ChipConfigs/)
- Connection modes: Under Reset, Halt, Pre-Reset, Attach
- SWD frequency selection (100kHz - 10MHz)
- Reset type control (Default, Hardware, Software, System)
- Real-time operation logging
- Help documentation page
- Light/Dark theme support
- udev rules for Linux

### Technical Details
- Python 3.9+ required
- PyQt6 for GUI framework
- PyQt6-Fluent-Widgets for modern UI components
- Embedded PyOCD for probe communication
- JSON-based configuration storage

## [Unreleased]

### Planned
- GDB Server integration
- Batch programming mode
- Programming scripts support
- More chip family support
- Memory viewer/editor
