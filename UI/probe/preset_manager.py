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
    
    # Preset key mapping (index -> key) since qfluentwidgets ComboBox doesn't support itemData
    _preset_keys: dict
    
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
        
        # Build index -> key mapping (qfluentwidgets ComboBox doesn't support itemData)
        self._preset_keys = {0: None}  # Index 0 is placeholder
        
        idx = 1
        for key, cfg in sorted(presets.items(), key=lambda x: x[1].name):
            self.preset_combo.addItem(f"{cfg.name} ({cfg.target})")
            self._preset_keys[idx] = key
            idx += 1
    
    def _on_vendor_changed(self, vendor: str):
        """Handle vendor selection change"""
        self._update_preset_combo()
    
    def _on_preset_changed(self, text: str):
        """Handle preset selection change - show info only, don't auto-apply"""
        if not text or text.startswith("--"):
            self.preset_info.setText("")
            self._current_chip_config = None
            return
        
        # Get preset key from mapping
        idx = self.preset_combo.currentIndex()
        if idx <= 0:
            return
        
        # Initialize _preset_keys if not exists
        if not hasattr(self, '_preset_keys'):
            self._preset_keys = {}
            
        key = self._preset_keys.get(idx)
        if not key:
            # Fallback: try to extract target from text "Name (target)"
            if "(" in text and text.endswith(")"):
                target = text.rsplit("(", 1)[1].rstrip(")")
                # Find preset by target
                all_presets = self._chip_config_mgr.get_all_presets()
                for k, cfg in all_presets.items():
                    if cfg.target == target:
                        key = k
                        break
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
            
            # Auto-apply flash address (emit signal so flash page updates)
            # Full apply (target, freq, mode) still requires clicking "应用预设"
            self.config_applied.emit(config)
    
    def _apply_preset(self):
        """Apply selected preset to current settings"""
        # If no current config, try to get from combo
        if not self._current_chip_config:
            text = self.preset_combo.currentText()
            if text and not text.startswith("--"):
                # Try to extract target from text "Name (target)"
                if "(" in text and text.endswith(")"):
                    target = text.rsplit("(", 1)[1].rstrip(")")
                    all_presets = self._chip_config_mgr.get_all_presets()
                    for k, cfg in all_presets.items():
                        if cfg.target == target:
                            self._current_chip_config = cfg
                            break
        
        if not self._current_chip_config:
            InfoBar.warning("提示", "请先选择一个预设", parent=self.window(), 
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        config = self._current_chip_config
        
        # Apply target - first filter to find the target, then select it
        target_found = False
        target_name = config.target.lower()
        
        # Try exact match first
        idx = self.target_combo.findText(config.target)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)
            target_found = True
        else:
            # Target not in current list, filter targets to find similar ones
            self.target_search.setText(config.target)
            
            # More flexible matching: match if target contains the search term or vice versa
            filtered = [t for t in self._all_targets 
                       if target_name in t.lower() or t.lower() in target_name]
            
            if not filtered:
                # Try matching just the base name (without suffix like 'xx')
                base_target = target_name.rstrip('x').rstrip('_')
                filtered = [t for t in self._all_targets if base_target in t.lower()]
            
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
                # Show info instead of warning
                self.log_message.emit(f"目标芯片 '{config.target}' 未找到精确匹配，已选择类似: {filtered[0]}")
        
        if not target_found:
            # Only show as info in the preset_info label, not as popup warning
            self.preset_info.setText(f"⚠ 目标芯片 '{config.target}' 在列表中未找到，请手动选择或使用Pack")
        
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
        
        # Use current chip config if available (e.g., from Pack import)
        # This preserves flash_start from Pack or previously applied preset
        if self._current_chip_config:
            flash_start = self._current_chip_config.flash_start
            vendor = self._current_chip_config.vendor or "Unknown"
            chip_family = self._current_chip_config.chip_family or (target[:5].upper() if len(target) >= 5 else target.upper())
            description = self._current_chip_config.description or f"用户自定义预设 - {target}"
            notes = self._current_chip_config.notes or ""
            # Use config's frequency/mode if UI hasn't changed them
            if self._current_chip_config.default_frequency:
                freq = self._current_chip_config.default_frequency
        else:
            # Fallback: determine from target name
            flash_start = get_default_flash_start(target)
            chip_family = target[:5].upper() if len(target) >= 5 else target.upper()
            description = f"用户自定义预设 - {target}"
            notes = ""
            
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
            elif target_lower.startswith("fm"):
                vendor = "FMSH"
        
        # Build initial data for dialog
        initial_data = {
            'name': f"{target.upper()} Custom",
            'target': target,
            'vendor': vendor,
            'chip_family': chip_family,
            'flash_start': hex(flash_start),
            'frequency': freq,
            'connect_mode': mode,
            'pack_file': self.pack_edit.text(),
            'description': description,
            'notes': notes,
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
        from Core.config import config as app_config
        import os
        
        # Get last import dir or default to Doc/ChipConfigs
        last_import_dir = app_config.get('last_preset_import_dir', '')
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
        app_config.set('last_preset_import_dir', os.path.dirname(path))
        
        result = self._chip_config_mgr.import_preset(Path(path))
        if result:
            self._update_preset_combo()
            
            # Auto-select the imported preset
            imported_config = self._chip_config_mgr.get_preset(result)
            if imported_config:
                # Find and select in combo using _preset_keys mapping
                found_idx = -1
                if hasattr(self, '_preset_keys'):
                    for idx, key in self._preset_keys.items():
                        if key == result:
                            found_idx = idx
                            break
                
                if found_idx < 0:
                    # Try to find by target name in text
                    for i in range(self.preset_combo.count()):
                        text = self.preset_combo.itemText(i)
                        if imported_config.target in text:
                            found_idx = i
                            break
                
                if found_idx >= 0:
                    self.preset_combo.setCurrentIndex(found_idx)
                
                # Set as current config
                self._current_chip_config = imported_config
                
                # Show info
                info_parts = [
                    f"目标: {imported_config.target}",
                    f"Flash: 0x{imported_config.flash_start:08X}",
                    f"频率: {imported_config.default_frequency // 1000}kHz",
                    f"模式: {imported_config.connect_mode}",
                ]
                if imported_config.description:
                    info_parts.append(imported_config.description)
                self.preset_info.setText(" | ".join(info_parts))
                
                # Auto-apply the imported preset
                self._apply_preset()
            
            self.log_message.emit(f"已导入并应用预设: {imported_config.name if imported_config else result}")
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
            'frequency': config.default_frequency,
            'connect_mode': config.connect_mode,
            'pack_file': config.pack_file or '',
            'description': config.description or '',
            'notes': config.notes or ''
        }
        
        # Show dialog
        dialog = SavePresetDialog(self, initial_data, export_only=True)
        dialog.setWindowTitle("导出芯片预设")
        if dialog.exec() != 1:  # QDialog.Accepted
            return
        
        export_path = dialog.get_export_path()
        if not export_path:
            return
        
        # Get edited data from dialog
        edited_data = dialog.get_preset_data()
        
        # Build export dict with proper format
        export_dict = {
            'name': edited_data.get('name', config.name),
            'vendor': edited_data.get('vendor', config.vendor),
            'chip_family': edited_data.get('chip_family', config.chip_family),
            'target': edited_data.get('target', config.target),
            'flash_start': int(edited_data.get('flash_start', '0x0'), 16) if isinstance(edited_data.get('flash_start'), str) else edited_data.get('flash_start', 0),
            'flash_size': config.flash_size,
            'ram_start': int(edited_data.get('ram_start', '0x20000000'), 16) if isinstance(edited_data.get('ram_start'), str) else edited_data.get('ram_start', 0x20000000),
            'ram_size': config.ram_size,
            'default_frequency': edited_data.get('frequency', config.default_frequency),
            'connect_mode': edited_data.get('connect_mode', config.connect_mode),
            'reset_type': config.reset_type,
            'pack_file': edited_data.get('pack_file', config.pack_file or ''),
            'options': config.options or {},
            'description': edited_data.get('description', config.description or ''),
            'notes': edited_data.get('notes', config.notes or ''),
        }
        
        import json
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_dict, f, indent=2, ensure_ascii=False)
            
            # Also save to app config so it appears in dropdown
            new_config = ChipConfig(
                name=export_dict['name'],
                vendor=export_dict['vendor'],
                chip_family=export_dict['chip_family'],
                target=export_dict['target'],
                flash_start=export_dict['flash_start'],
                flash_size=export_dict['flash_size'],
                ram_start=export_dict['ram_start'],
                ram_size=export_dict['ram_size'],
                default_frequency=export_dict['default_frequency'],
                connect_mode=export_dict['connect_mode'],
                reset_type=export_dict['reset_type'],
                pack_file=export_dict['pack_file'],
                options=export_dict['options'],
                description=export_dict['description'],
                notes=export_dict['notes'],
            )
            # Generate key for user preset
            preset_key = f"user_{new_config.target}_{new_config.chip_family}".lower().replace(' ', '_')
            self._chip_config_mgr.add_user_preset(preset_key, new_config)
            
            # Refresh presets and select the new one
            self._load_presets()
            self._current_chip_config = new_config
            
            # Try to select the new preset in combo
            for i in range(self.preset_combo.count()):
                if new_config.name in self.preset_combo.itemText(i):
                    self.preset_combo.setCurrentIndex(i)
                    break
            
            self.log_message.emit(f"已导出预设: {export_path}")
            InfoBar.success("成功", f"已导出并保存预设: {new_config.name}", parent=self.window(),
                           position=InfoBarPosition.TOP_RIGHT)
        except Exception as e:
            self.log_message.emit(f"导出失败: {e}")
            InfoBar.error("失败", f"导出失败: {e}", parent=self.window(),
                         position=InfoBarPosition.TOP_RIGHT)
    
    def get_current_chip_config(self) -> Optional[ChipConfig]:
        """Get currently selected/applied chip config"""
        return self._current_chip_config

    def _delete_preset(self):
        """Delete the currently selected preset"""
        from qfluentwidgets import MessageBox
        
        # Get selected preset key
        idx = self.preset_combo.currentIndex()
        if idx <= 0:
            InfoBar.warning("提示", "请先选择一个预设", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        # Initialize _preset_keys if not exists
        if not hasattr(self, '_preset_keys'):
            self._preset_keys = {}
        
        key = self._preset_keys.get(idx)
        if not key:
            InfoBar.warning("提示", "无法获取预设信息", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        # Check if it's a user preset (only user presets can be deleted)
        if not key.startswith("user_"):
            InfoBar.warning("提示", "内置预设不能删除，只能删除用户自定义预设", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        config = self._chip_config_mgr.get_preset(key)
        if not config:
            InfoBar.warning("提示", "找不到该预设", parent=self.window(),
                          position=InfoBarPosition.TOP_RIGHT)
            return
        
        # Confirm deletion
        box = MessageBox("确认删除", f"确定要删除预设 \"{config.name}\" 吗？", self.window())
        if box.exec():
            if self._chip_config_mgr.delete_user_preset(key):
                # Refresh preset list
                self._update_preset_combo()
                self._current_chip_config = None
                self.preset_info.setText("")
                
                self.log_message.emit(f"已删除预设: {config.name}")
                InfoBar.success("成功", f"已删除预设: {config.name}", parent=self.window(),
                              position=InfoBarPosition.TOP_RIGHT)
            else:
                InfoBar.error("失败", "删除预设失败", parent=self.window(),
                            position=InfoBarPosition.TOP_RIGHT)