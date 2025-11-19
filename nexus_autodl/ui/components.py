"""
Custom UI components for Nexus AutoDL.
"""

import weakref
from tkinter import Toplevel, Label
from typing import Optional
from ..constants import AppConstants
from .theme_manager import ThemeManager

class OptimizedHoverEffect:
    _instances = weakref.WeakSet()
    
    def __init__(self, widget, hover_key: str, theme_manager: ThemeManager, effect_type: str = "smooth"):
        self.widget = widget
        self.hover_key = hover_key
        self.theme_manager = theme_manager
        self.effect_type = effect_type
        self.is_hovering = False
        self._bound = False
        
        self._store_original_properties()
        self._bind_events()
        OptimizedHoverEffect._instances.add(self)
    
    def _store_original_properties(self):
        try:
            self.original_bg = self.widget.cget("bg")
            self.original_fg = self.widget.cget("fg") 
            self.original_cursor = self.widget.cget("cursor")
        except Exception:
            self.original_bg = self.theme_manager.get_color('button_bg_color')
            self.original_fg = self.theme_manager.get_color('button_fg_color')
            self.original_cursor = ""
    
    def _bind_events(self):
        if not self._bound:
            try:
                self.widget.bind("<Enter>", self._on_enter, add='+')
                self.widget.bind("<Leave>", self._on_leave, add='+')
                self._bound = True
            except Exception as e:
                print(f"Failed to bind hover events: {e}")
    
    def update_theme(self, theme_manager: ThemeManager):
        self.theme_manager = theme_manager
        if not self.is_hovering:
            self._store_original_properties()
            self._apply_normal_state()
    
    def _on_enter(self, event=None):
        if not self.is_hovering:
            self.is_hovering = True
            self._apply_hover_state()
    
    def _on_leave(self, event=None):
        if self.is_hovering:
            self.is_hovering = False
            self._apply_normal_state()
    
    def _apply_hover_state(self):
        try:
            hover_bg = self.theme_manager.get_hover_color(self.hover_key)
            hover_fg = "#FFFFFF"
            
            config_dict = {"cursor": "hand2"}
            
            if self.effect_type == "subtle":
                config_dict["bg"] = hover_bg
            else:
                config_dict.update({"bg": hover_bg, "fg": hover_fg})
            
            self.widget.config(**config_dict)
        except Exception:
            pass
    
    def _apply_normal_state(self):
        try:
            config_dict = {"cursor": self.original_cursor}
            
            if self.effect_type == "subtle":
                config_dict["bg"] = self.original_bg
            else:
                config_dict.update({"bg": self.original_bg, "fg": self.original_fg})
            
            self.widget.config(**config_dict)
        except Exception:
            pass
    
    @classmethod
    def update_all_themes(cls, theme_manager: ThemeManager):
        for instance in cls._instances:
            try:
                instance.update_theme(theme_manager)
            except Exception:
                continue

class EnhancedTooltip:
    _instances = weakref.WeakSet()
    
    def __init__(self, widget, text: str, theme_manager: ThemeManager, delay: int = AppConstants.TOOLTIP_DELAY):
        self.widget = widget
        self.text = text
        self.theme_manager = theme_manager
        self.delay = delay
        self.tooltip_window: Optional[Toplevel] = None
        self.schedule_id: Optional[str] = None
        self._bound = False
        
        self._bind_events()
        EnhancedTooltip._instances.add(self)
    
    def _bind_events(self):
        if not self._bound:
            try:
                self.widget.bind("<Enter>", self._on_enter, add='+')
                self.widget.bind("<Leave>", self._on_leave, add='+')
                self.widget.bind("<ButtonPress>", self._on_leave, add='+')
                self._bound = True
            except Exception as e:
                print(f"Failed to bind tooltip events: {e}")
    
    def update_theme(self, theme_manager: ThemeManager):
        self.theme_manager = theme_manager
    
    def _on_enter(self, event=None): 
        self._schedule_show()
    
    def _on_leave(self, event=None): 
        self._cancel_and_hide()
    
    def _schedule_show(self):
        self._cancel_scheduled()
        try:
            self.schedule_id = self.widget.after(self.delay, self._show_tooltip)
        except Exception:
            pass
    
    def _cancel_scheduled(self):
        if self.schedule_id:
            try:
                self.widget.after_cancel(self.schedule_id)
            except Exception:
                pass
            finally:
                self.schedule_id = None
    
    def _cancel_and_hide(self):
        self._cancel_scheduled()
        self._hide_tooltip()
    
    def _show_tooltip(self):
        if self.tooltip_window:
            return
        
        try:
            x, y = self.widget.winfo_pointerxy()
            self.tooltip_window = Toplevel(self.widget)
            self.tooltip_window.overrideredirect(True)
            self.tooltip_window.geometry(f"+{x+20}+{y+10}")
            
            try:
                if self.widget.winfo_toplevel().attributes("-topmost"):
                    self.tooltip_window.attributes("-topmost", True)
            except Exception:
                pass
            
            label = Label(
                self.tooltip_window,
                text=self.text,
                justify='left',
                background=self.theme_manager.get_color('tooltip_bg_color'),
                foreground=self.theme_manager.get_color('tooltip_fg_color'),
                relief='solid',
                borderwidth=1,
                wraplength=300,
                padx=8,
                pady=5,
                font=("Segoe UI", 9)
            )
            label.pack(ipadx=1)
        except Exception:
            self._hide_tooltip()
    
    def _hide_tooltip(self):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except Exception:
                pass
            finally:
                self.tooltip_window = None
    
    @classmethod
    def update_all_themes(cls, theme_manager: ThemeManager):
        for instance in cls._instances:
            try:
                instance.update_theme(theme_manager)
            except Exception:
                continue
    
    @classmethod
    def hide_all(cls):
        for instance in cls._instances:
            try:
                instance._cancel_and_hide()
            except Exception:
                continue
