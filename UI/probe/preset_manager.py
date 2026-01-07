#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preset Management Mixin
Provides preset loading, saving, importing, and exporting functionality
"""

import logging
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QFileDialog

from qfluentwidgets import InfoBar, InfoBarPosition

from Core.chip_config import ChipConfig, ChipConfigManager, get_default_flash_start

LOG = logging.getLogger(__name__)


class PresetManagerMixin:
    """Mixin class providing preset management methods for ProbePage"""
    
    # These must be defined by the class using this mixin
    _chip_config_mgr: ChipConfigManager
    _current_chip_config: Optional[ChipConfig]
    _config: object  # AppConfig
    
    # UI elements (defined by ProbePage)
    vendor_combo: object
    preset_combo: object
    preset_info: object
    target_combo: object
    target_search: object
    freq_combo: object
    mode_combo: object
    pack_edit: object
    log_message: object  # pyqtSignal
    config_applied: object  # pyqtSignal
    _all_targets: list
    
    def _load_presets(self):
        """Load chip presets into UI"""
        # Load vendors
        vendors = self._chip_config_mgr.get_vendors()
        self.vendor_combo.clear()
        self.vendor_combo.addItem("全部厂商")
        self.vendor_combo.addItems(vendors)
        
        # Load all presets
        self._update_preset_combo()
    
    def _update_preset_combo(self):
        """Update preset combo based on selected vendor"""
        vendor = self.vendor_combo.currentText()
        
        if vendor == "全部厂商" or not vendor:
            presets = self._chip_config_mgr.get_all_presets()
        else:
            presets = self._chip_config_mgr.get_presets_by_vendor(vendor)
        
        self.preset_combo.clear()
        self.preset_combo.addItem("-- 选择预设 --")
        
        for key, cfg in sorted(presets.items(), key=lambda x: x[1].name):
            self.preset_combo.addItem(f"{cfg.name} ({cfg.target})", key)
    
    def _on_vendor_changed(self, vendor: str):
        """Handle vendor selection change"""
        self._update_preset_combo()
    
    def _on_preset_changed(self, text: str):
        """Handle preset selection change - show info and auto-apply"""
        if not text or text.startswith("--"):
            self.preset_info.setText("")
            self._current_chip_config = None
            return
        
        # Get preset key from combo data
        idx = self.preset_combo.currentIndex()
        if idx <= 0:
            return
            
        key = self.preset_combo.itemData(idx)
        if not key:
            return
            
        config = self._chip_config_mgr.get_preset(key)
        if config:
            self._current_chip_config = config
            # Show preset info
            info_parts = [
                f"目标: {config.target}",
                f"Flash: 0x{config.flash_start:08X}",
                f"频率: {config.default_frequency // 1000}kHz",
                f"模式: {config.connect_mode}",
            ]
            if config.description:
                info_parts.append(config.description)
            if config.notes:
                info_parts.append(f"备注: {config.notes}")
            self.preset_info.setText(" | ".join(info_parts))
            
            # Auto-apply preset when selected
            self._apply_preset()
    
    def _apply_preset(self):
        """Apply selected preset to current settings"""
        if not self._current_chip_config:
            InfoBar.warning("提示", "请先选择一个预设", parent=self.window(), 
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        config = self._current_chip_config
        
        # Apply target - first filter to find the target, then select it
        target_found = False
        idx = self.target_combo.findText(config.target)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)
            target_found = True
        else:
            # Target not in current list, filter targets to find it
            self.target_search.setText(config.target)
            # _filter_targets is called via signal, manually filter and update
            filtered = [t for t in self._all_targets if config.target.lower() in t.lower()]
            self._update_target_combo(filtered)
            
            # Now try to find exact match
            idx = self.target_combo.findText(config.target)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
                target_found = True
            elif filtered:
                # Select first match if exact match not found
                self.target_combo.setCurrentIndex(0)
                target_found = True
        
        if not target_found:
            InfoBar.warning("提示", f"未找到目标芯片: {config.target}", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
        
        # Apply frequency
        freq_map = {100000: 0, 500000: 1, 1000000: 2, 2000000: 3, 4000000: 4, 8000000: 5, 10000000: 6}
        freq_idx = freq_map.get(config.default_frequency, 2)
        self.freq_combo.setCurrentIndex(freq_idx)
        
        # Apply connect mode
        mode_map = {"under-reset": 0, "halt": 1, "pre-reset": 2, "attach": 3}
        mode_idx = mode_map.get(config.connect_mode.lower(), 0)
        self.mode_combo.setCurrentIndex(mode_idx)
        
        # Apply pack file if specified
        if config.pack_file:
            self.pack_edit.setText(config.pack_file)
        
        # Emit signal for other components (e.g., flash page to update address)
        self.config_applied.emit(config)
        
        self.log_message.emit(f"已应用预设: {config.name}")
        InfoBar.success("成功", f"已应用预设: {config.name}", parent=self.window(),
                       position=InfoBarPosition.TOP_RIGHT)
    
    def apply_chip_config(self, config, show_notification: bool = True):
        """Apply chip config from external source (e.g., chip config page)
        
        Args:
            config: ChipConfig to apply
            show_notification: Whether to show success notification
        """
        if not config:
            return
        
        self._current_chip_config = config
        
        # Apply target - first filter to find the target, then select it
        target_found = False
        idx = self.target_combo.findText(config.target)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)
            target_found = True
        else:
            # Target not in current list, filter targets to find it
            self.target_search.setText(config.target)
            filtered = [t for t in self._all_targets if config.target.lower() in t.lower()]
            self._update_target_combo(filtered)
            
            idx = self.target_combo.findText(config.target)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
                target_found = True
            elif filtered:
                self.target_combo.setCurrentIndex(0)
                target_found = True
        
        # Apply frequency
        freq_map = {100000: 0, 500000: 1, 1000000: 2, 2000000: 3, 4000000: 4, 8000000: 5, 10000000: 6}
        freq_idx = freq_map.get(config.default_frequency, 2)
        self.freq_combo.setCurrentIndex(freq_idx)
        
        # Apply connect mode
        mode_map = {"under-reset": 0, "halt": 1, "pre-reset": 2, "attach": 3}
        mode_idx = mode_map.get(config.connect_mode.lower(), 0)
        self.mode_combo.setCurrentIndex(mode_idx)
        
        # Apply pack file if specified
        if config.pack_file:
            self.pack_edit.setText(config.pack_file)
        
        if show_notification:
            self.log_message.emit(f"已应用配置: {config.name}")
            InfoBar.success("成功", f"已应用配置: {config.name}", parent=self.window(),
                           position=InfoBarPosition.TOP_RIGHT)
    
    def _save_current_as_preset(self):
        """Save current settings as a new preset with enhanced dialog"""
        from UI.save_preset_dialog import SavePresetDialog
        
        target = self.target_combo.currentText()
        if not target:
            InfoBar.warning("提示", "请先选择目标芯片", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        # Get current settings to pre-fill dialog
        freq_map = {0: 100000, 1: 500000, 2: 1000000, 3: 2000000, 4: 4000000, 5: 8000000, 6: 10000000}
        freq = freq_map.get(self.freq_combo.currentIndex(), 1000000)
        
        mode_map = {0: "under-reset", 1: "halt", 2: "pre-reset", 3: "attach"}
        mode = mode_map.get(self.mode_combo.currentIndex(), "under-reset")
        
        # Determine vendor from target name
        vendor = "Unknown"
        target_lower = target.lower()
        if target_lower.startswith("stm32"):
            vendor = "STMicroelectronics"
        elif target_lower.startswith("gd32"):
            vendor = "GigaDevice"
        elif target_lower.startswith("mm32"):
            vendor = "MindMotion"
        elif target_lower.startswith("nrf"):
            vendor = "Nordic"
        elif target_lower.startswith("lpc") or target_lower.startswith("mimx"):
            vendor = "NXP"
        elif target_lower.startswith("at32"):
            vendor = "Artery"
        elif target_lower.startswith("apm32"):
            vendor = "APM/Geehy"
        elif target_lower.startswith("ch32"):
            vendor = "WCH"
        
        # Build initial data for dialog
        initial_data = {
            'name': f"{target.upper()} Custom",
            'target': target,
            'vendor': vendor,
            'chip_family': target[:5].upper() if len(target) >= 5 else target.upper(),
            'flash_start': hex(get_default_flash_start(target)),
            'frequency': freq,
            'connect_mode': mode,
            'pack_file': self.pack_edit.text(),
            'description': f"用户自定义预设 - {target}"
        }
        
        # Show dialog
        dialog = SavePresetDialog(self, initial_data)
        if dialog.exec() != 1:  # QDialog.Accepted
            return
        
        preset_data = dialog.get_preset_data()
        export_path = dialog.get_export_path()
        
        # Create config
        config = self._chip_config_mgr.create_config_from_current(
            name=preset_data['name'],
            target=preset_data['target'],
            vendor=preset_data['vendor'],
            flash_start=int(preset_data['flash_start'], 16) if preset_data['flash_start'].startswith('0x') else int(preset_data['flash_start']),
            frequency=preset_data['frequency'],
            connect_mode=preset_data['connect_mode'],
            pack_file=preset_data.get('pack_file', ''),
            description=preset_data.get('description', '')
        )
        
        # Save to user presets
        key = f"user_{preset_data['target']}_{preset_data['name']}".lower().replace(" ", "_")
        self._chip_config_mgr.add_user_preset(key, config)
        
        # Also export to file if user selected export option
        if dialog.should_export_to_file() and export_path:
            import json
            try:
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
                self.log_message.emit(f"预设已导出到: {export_path}")
            except Exception as e:
                self.log_message.emit(f"导出文件失败: {e}")
        
        # Refresh combo
        self._update_preset_combo()
        
        self.log_message.emit(f"已保存预设: {preset_data['name']}")
        InfoBar.success("成功", f"已保存预设: {preset_data['name']}", parent=self.window(),
                       position=InfoBarPosition.TOP_RIGHT)
    
    def _import_preset(self):
        """Import preset from JSON file"""
        from Core.config import config
        import os
        
        # Get last import dir or default to Doc/ChipConfigs
        last_import_dir = config.get('last_preset_import_dir', '')
        if not last_import_dir or not os.path.isdir(last_import_dir):
            project_root = Path(__file__).parent.parent.parent
            chip_configs_dir = project_root / "Doc" / "ChipConfigs"
            if chip_configs_dir.exists():
                last_import_dir = str(chip_configs_dir)
            else:
                last_import_dir = ""
        
        path, _ = QFileDialog.getOpenFileName(
            self, "导入芯片预设", last_import_dir, "JSON Files (*.json)")
        if not path:
            return
        
        # Remember directory
        config.set('last_preset_import_dir', os.path.dirname(path))
        
        result = self._chip_config_mgr.import_preset(Path(path))
        if result:
            self._update_preset_combo()
            self.log_message.emit(f"已导入预设: {result}")
            InfoBar.success("成功", f"已导入预设", parent=self.window(),
                           position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.error("失败", "导入预设失败", parent=self.window(),
                         position=InfoBarPosition.TOP_RIGHT)
    
    def _export_preset(self):
        """Export current preset to JSON file with enhanced path selection"""
        if not self._current_chip_config:
            InfoBar.warning("提示", "请先选择一个预设", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        from UI.save_preset_dialog import SavePresetDialog
        
        config = self._current_chip_config
        
        # Build initial data from current config
        initial_data = {
            'name': config.name,
            'target': config.target,
            'vendor': config.vendor,
            'chip_family': config.chip_family,
            'flash_start': hex(config.flash_start),
            'frequency': config.frequency,
            'connect_mode': config.connect_mode,
            'pack_file': config.pack_file or '',
            'description': config.description or ''
        }
        
        # Show dialog
        dialog = SavePresetDialog(self, initial_data, export_only=True)
        dialog.setWindowTitle("导出芯片预设")
        if dialog.exec() != 1:  # QDialog.Accepted
            return
        
        export_path = dialog.get_export_path()
        if not export_path:
            return
        
        import json
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            self.log_message.emit(f"已导出预设: {export_path}")
            InfoBar.success("成功", f"已导出预设到: {export_path}", parent=self.window(),
                           position=InfoBarPosition.TOP_RIGHT)
        except Exception as e:
            self.log_message.emit(f"导出失败: {e}")
            InfoBar.error("失败", f"导出失败: {e}", parent=self.window(),
                         position=InfoBarPosition.TOP_RIGHT)
    
    def get_current_chip_config(self) -> Optional[ChipConfig]:
        """Get currently selected/applied chip config"""
        return self._current_chip_config
