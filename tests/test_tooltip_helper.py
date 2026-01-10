#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for UI/tooltip_helper.py
Tests the InstantToolTipFilter and install_tooltip function
"""

import pytest
from pathlib import Path


def get_project_root():
    return Path(__file__).parent.parent


class TestTooltipHelper:
    """Tests for tooltip_helper module"""
    
    @pytest.fixture
    def project_root(self):
        return get_project_root()
    
    def test_module_structure(self, project_root):
        """Test tooltip_helper has correct structure"""
        filepath = project_root / 'UI' / 'tooltip_helper.py'
        assert filepath.exists()
        
        content = filepath.read_text(encoding='utf-8')
        
        # Check for required imports
        assert 'from PyQt6.QtCore import' in content
        assert 'QObject' in content
        assert 'QEvent' in content
        
        # Check for required classes/functions
        assert 'class InstantToolTipFilter' in content
        assert 'def install_tooltip' in content
        assert 'def eventFilter' in content
    
    def test_instant_tooltip_filter_has_no_delay(self, project_root):
        """Ensure InstantToolTipFilter shows tooltip immediately without delay"""
        filepath = project_root / 'UI' / 'tooltip_helper.py'
        content = filepath.read_text(encoding='utf-8')
        
        # Should NOT have timer or delay mechanism
        assert 'QTimer' not in content, \
            "InstantToolTipFilter should not use QTimer (causes delay)"
        assert 'showDelay' not in content, \
            "InstantToolTipFilter should not have showDelay parameter"
    
    def test_event_filter_handles_required_events(self, project_root):
        """Ensure eventFilter handles all required event types"""
        filepath = project_root / 'UI' / 'tooltip_helper.py'
        content = filepath.read_text(encoding='utf-8')
        
        # Must handle these events
        assert 'QEvent.Type.ToolTip' in content, \
            "Must block native tooltip"
        assert 'QEvent.Type.Enter' in content, \
            "Must show tooltip on enter"
        assert 'QEvent.Type.Leave' in content, \
            "Must hide tooltip on leave"
    
    def test_uses_qfluentwidgets_tooltip(self, project_root):
        """Ensure uses qfluentwidgets ToolTip for theme compatibility"""
        filepath = project_root / 'UI' / 'tooltip_helper.py'
        content = filepath.read_text(encoding='utf-8')
        
        assert 'from qfluentwidgets import ToolTip' in content, \
            "Must use qfluentwidgets ToolTip for theme compatibility"


class TestTooltipIntegration:
    """Integration tests for tooltip usage across UI"""
    
    @pytest.fixture
    def project_root(self):
        return get_project_root()
    
    def test_settings_page_uses_install_tooltip(self, project_root):
        """Test settings_page.py uses install_tooltip"""
        filepath = project_root / 'UI' / 'settings_page.py'
        content = filepath.read_text(encoding='utf-8')
        
        # Should import and use install_tooltip
        assert 'from UI.tooltip_helper import install_tooltip' in content
        assert '_install_tooltips' in content
        assert 'install_tooltip(' in content
    
    def test_probe_page_uses_install_tooltip(self, project_root):
        """Test probe/page.py uses install_tooltip"""
        filepath = project_root / 'UI' / 'probe' / 'page.py'
        content = filepath.read_text(encoding='utf-8')
        
        # Should import and use install_tooltip
        assert 'from UI.tooltip_helper import install_tooltip' in content
        assert '_install_tooltips' in content
        assert 'install_tooltip(' in content
    
    def test_tooltip_widgets_are_covered(self, project_root):
        """Ensure all widgets with setToolTip have install_tooltip"""
        # Check settings_page
        settings_path = project_root / 'UI' / 'settings_page.py'
        settings_content = settings_path.read_text(encoding='utf-8')
        
        # Count setToolTip calls
        tooltip_count = settings_content.count('.setToolTip(')
        
        # Should have _install_tooltips method
        assert '_install_tooltips' in settings_content, \
            "settings_page.py should have _install_tooltips method"
