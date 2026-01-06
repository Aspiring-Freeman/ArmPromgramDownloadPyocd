# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
