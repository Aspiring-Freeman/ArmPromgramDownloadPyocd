#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tooltip helper for theme-compatible tooltips.

Provides instant tooltip display (no delay) that follows qfluentwidgets theme.
This solves the black frame issue in light theme and the lag issue with
the default ToolTipFilter.
"""

from PyQt6.QtCore import QObject, QEvent, QPoint
from PyQt6.QtWidgets import QWidget

from qfluentwidgets import ToolTip, ToolTipPosition


class InstantToolTipFilter(QObject):
    """Event filter that shows tooltips instantly without delay.
    
    Unlike qfluentwidgets' ToolTipFilter which has a 300ms default delay,
    this filter shows tooltips immediately on hover, providing a responsive UX.
    """
    
    def __init__(self, parent: QWidget, position: ToolTipPosition = ToolTipPosition.BOTTOM):
        super().__init__(parent)
        self._tooltip: ToolTip = None
        self._position = position
        
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip:
            # Block native tooltip
            return True
            
        elif event.type() == QEvent.Type.Enter:
            self._show_tooltip()
            
        elif event.type() in (QEvent.Type.Leave, QEvent.Type.Hide, 
                               QEvent.Type.MouseButtonPress):
            self._hide_tooltip()
            
        return super().eventFilter(obj, event)
    
    def _show_tooltip(self):
        """Show the custom tooltip immediately"""
        parent = self.parent()
        if not isinstance(parent, QWidget):
            return
            
        text = parent.toolTip()
        if not text:
            return
            
        if self._tooltip is None:
            self._tooltip = ToolTip(text, parent)
        else:
            self._tooltip.setText(text)
        
        # Calculate position
        pos = self._get_tooltip_position(parent)
        self._tooltip.move(pos)
        
        # Set duration
        duration = parent.toolTipDuration() if parent.toolTipDuration() > 0 else -1
        self._tooltip.setDuration(duration)
        
        self._tooltip.show()
    
    def _hide_tooltip(self):
        """Hide the tooltip"""
        if self._tooltip is not None:
            self._tooltip.hide()
    
    def _get_tooltip_position(self, parent: QWidget) -> QPoint:
        """Calculate tooltip position based on position setting"""
        if self._tooltip is None:
            return QPoint(0, 0)
            
        # Get parent's global position
        pos = parent.mapToGlobal(QPoint(0, 0))
        
        # Adjust based on position preference
        if self._position == ToolTipPosition.TOP:
            x = pos.x() + (parent.width() - self._tooltip.width()) // 2
            y = pos.y() - self._tooltip.height() - 4
        elif self._position == ToolTipPosition.BOTTOM:
            x = pos.x() + (parent.width() - self._tooltip.width()) // 2
            y = pos.y() + parent.height() + 4
        elif self._position == ToolTipPosition.LEFT:
            x = pos.x() - self._tooltip.width() - 4
            y = pos.y() + (parent.height() - self._tooltip.height()) // 2
        elif self._position == ToolTipPosition.RIGHT:
            x = pos.x() + parent.width() + 4
            y = pos.y() + (parent.height() - self._tooltip.height()) // 2
        else:
            # Default to bottom
            x = pos.x() + (parent.width() - self._tooltip.width()) // 2
            y = pos.y() + parent.height() + 4
            
        return QPoint(x, y)


def install_tooltip(widget: QWidget, position: ToolTipPosition = ToolTipPosition.BOTTOM):
    """Install instant tooltip filter on a widget.
    
    Args:
        widget: The widget to install tooltip filter on
        position: Where to show the tooltip (default: BOTTOM)
        
    Example:
        from UI.tooltip_helper import install_tooltip
        
        edit = LineEdit()
        edit.setToolTip("This is a tooltip")
        install_tooltip(edit)
    """
    widget.installEventFilter(InstantToolTipFilter(widget, position))
