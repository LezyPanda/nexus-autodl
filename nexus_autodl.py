"""
Nexus AutoDL - Automation Script

v0.6.3
"""

import json
import os
import random
import re
import shutil
import weakref
from datetime import datetime
from pathlib import Path
from tkinter import (BooleanVar, Button, Checkbutton, DoubleVar, Entry, Frame,
                     Label, Listbox, Scrollbar, StringVar, Text, Tk, Toplevel,
                     filedialog, Canvas, LabelFrame, colorchooser, IntVar)
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Dict, Optional, List, Tuple, Union
import threading
import gc

try:
    from pynput import keyboard
    import pyautogui
    from PIL import UnidentifiedImageError, Image, ImageTk
    from PIL.Image import open as open_image
except ImportError as e:
    print(f"Error: A critical library is missing: {e.name}.")
    print("Please, run in your terminal: pip install pyautogui Pillow pynput")
    exit(1)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

INTEGER_PATTERN = re.compile(r"([0-9]+)")

class AppConstants:
    VERSION = "v0.6.3"
    CONFIG_FILE = "config.json"
    CLICK_TOLERANCE = 3
    MIN_CAPTURE_SIZE = 10
    TRANSPARENT_COLOR = "#010203"
    CACHE_SIZE = 50
    SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
    TOOLTIP_DELAY = 400
    FEEDBACK_WINDOW_DELAY = 100
    LOG_WINDOW_SIZE = "800x400"
    PROFILE_MANAGER_SIZE = "650x500"
    INVALID_FILENAME_CHARS = {'/', '\\', ':', '*', '?', '"', '<', '>', '|'}

def human_sort_key(path: Path) -> Tuple[Union[int, str], ...]:
    return tuple(
        int(c) if c.isdigit() else c.lower() 
        for c in INTEGER_PATTERN.split(path.name)
    )

def safe_path_operation(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (OSError, IOError, PermissionError) as e:
            print(f"Path operation failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in path operation: {e}")
            return None
    return wrapper

def validate_filename(filename: str) -> bool:
    return not any(char in filename for char in AppConstants.INVALID_FILENAME_CHARS)

class ThemeManager:
    THEMES = {
        'light': {
            'bg_color': '#F5F5F5',
            'fg_color': '#2C2C2C',
            'input_bg_color': '#FFFFFF',
            'input_fg_color': '#2C2C2C',
            'button_bg_color': '#E0E0E0',
            'button_fg_color': '#2C2C2C',
            'button_active_bg_color': '#D0D0D0',
            'button_active_fg_color': '#1C1C1C',
            'secondary_fg_color': '#666666',
            'border_color': '#C0C0C0',
            'selection_bg_color': '#0078D4',
            'selection_fg_color': '#FFFFFF',
            'tooltip_bg_color': '#FFFFCC',
            'tooltip_fg_color': '#000000',
            'tooltip_border_color': '#CCCCCC',
            'preview_bg_color': '#FAFAFA',
            'preview_border_color': '#DDDDDD',
            'error_fg_color': '#D32F2F',
            'success_fg_color': '#388E3C',
            'readonly_bg_color': '#F8F8F8'
        },
        'dark': {
            'bg_color': '#2E2E2E',
            'fg_color': '#EAEAEA',
            'input_bg_color': '#3C3C3C',
            'input_fg_color': '#EAEAEA',
            'button_bg_color': '#555555',
            'button_fg_color': '#EAEAEA',
            'button_active_bg_color': '#6A6A6A',
            'button_active_fg_color': '#FFFFFF',
            'secondary_fg_color': '#888888',
            'border_color': '#404040',
            'selection_bg_color': '#6A6A6A',
            'selection_fg_color': '#FFFFFF',
            'tooltip_bg_color': '#1E1E1E',
            'tooltip_fg_color': '#EAEAEA',
            'tooltip_border_color': '#404040',
            'preview_bg_color': '#2E2E2E',
            'preview_border_color': '#404040',
            'error_fg_color': '#FF6B6B',
            'success_fg_color': '#4CAF50',
            'readonly_bg_color': '#333333'
        }
    }
    
    HOVER_COLORS = {
        'light': {
            'manage': '#0066CC',
            'create': '#7B1FA2',
            'start': '#2E7D32',
            'new': '#2E7D32',
            'rename': '#F57C00',
            'delete': '#C62828',
            'set_active': '#1976D2',
            'preview': '#7B1FA2',
            'browse': '#0066CC',
            'up': '#2E7D32',
            'down': '#F57C00',
            'close': '#C62828'
        },
        'dark': {
            'manage': '#4A9EFF',
            'create': '#9C27B0',
            'start': '#4CAF50',
            'new': '#4CAF50',
            'rename': '#FF9800',
            'delete': '#F44336',
            'set_active': '#2196F3',
            'preview': '#9C27B0',
            'browse': '#4A9EFF',
            'up': '#4CAF50',
            'down': '#FF9800',
            'close': '#F44336'
        }
    }
    
    def __init__(self, is_dark_mode: bool = False):
        self.is_dark_mode = is_dark_mode
        self._update_theme()
    
    def _update_theme(self):
        theme_key = 'dark' if self.is_dark_mode else 'light'
        self.current_theme = self.THEMES[theme_key]
        self.hover_colors = self.HOVER_COLORS[theme_key]
    
    def switch_theme(self, is_dark_mode: bool) -> bool:
        if self.is_dark_mode != is_dark_mode:
            self.is_dark_mode = is_dark_mode
            self._update_theme()
            return True
        return False
    
    def get_color(self, color_key: str) -> str:
        return self.current_theme.get(color_key, '#000000')
    
    def get_hover_color(self, hover_key: str) -> str:
        if hover_key in self.hover_colors:
            return self.hover_colors[hover_key]
        return self.get_color('button_active_bg_color')

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

class EnhancedTemplateCache:
    def __init__(self, max_cache_size: int = AppConstants.CACHE_SIZE):
        self._cache: Dict[str, Image.Image] = {}
        self._timestamps: Dict[str, float] = {}
        self._access_order: List[str] = []
        self._max_size = max_cache_size
        self._cache_hits = 0
        self._cache_misses = 0
        self._lock = threading.RLock()
    
    @safe_path_operation
    def get_template(self, template_path: Path) -> Optional[Image.Image]:
        if not template_path or not template_path.exists():
            return None
        
        path_str = str(template_path)
        
        with self._lock:
            try:
                file_mtime = template_path.stat().st_mtime
                
                if (path_str in self._cache and 
                    path_str in self._timestamps and 
                    self._timestamps[path_str] >= file_mtime):
                    
                    self._update_access_order(path_str)
                    self._cache_hits += 1
                    return self._cache[path_str].copy()
                
                template = self._load_template_safely(template_path)
                if template:
                    self._store_template(path_str, template, file_mtime)
                    self._cache_misses += 1
                    return template.copy()
                
            except Exception as e:
                print(f"Error loading template {template_path}: {e}")
                return None
    
    def _load_template_safely(self, template_path: Path) -> Optional[Image.Image]:
        try:
            with open_image(template_path) as img:
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                return img.copy()
        except (UnidentifiedImageError, OSError, IOError) as e:
            print(f"Failed to load image {template_path}: {e}")
            return None
    
    def _store_template(self, path_str: str, template: Image.Image, mtime: float):
        if path_str in self._cache:
            self._remove_from_cache(path_str)
        
        while len(self._cache) >= self._max_size and self._access_order:
            oldest_path = self._access_order[0]
            self._remove_from_cache(oldest_path)
        
        self._cache[path_str] = template
        self._timestamps[path_str] = mtime
        self._access_order.append(path_str)
    
    def _update_access_order(self, path_str: str):
        if path_str in self._access_order:
            self._access_order.remove(path_str)
        self._access_order.append(path_str)
    
    def _remove_from_cache(self, path_str: str):
        if path_str in self._cache:
            try:
                self._cache[path_str].close()
            except Exception:
                pass
        
        self._cache.pop(path_str, None)
        self._timestamps.pop(path_str, None)
        if path_str in self._access_order:
            self._access_order.remove(path_str)
    
    def invalidate_template(self, template_path: Path):
        if not template_path:
            return
        
        path_str = str(template_path)
        with self._lock:
            self._remove_from_cache(path_str)
    
    def clear_cache(self):
        with self._lock:
            for img in self._cache.values():
                try:
                    img.close()
                except Exception:
                    pass
            
            self._cache.clear()
            self._timestamps.clear()
            self._access_order.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            gc.collect()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
            
            memory_usage = sum(
                img.width * img.height * len(img.getbands()) 
                for img in self._cache.values()
            ) if self._cache else 0
            
            return {
                'cache_size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._cache_hits,
                'misses': self._cache_misses,
                'hit_rate': hit_rate,
                'memory_usage_bytes': memory_usage,
                'cached_templates': list(self._cache.keys())
            }

class EnhancedTemplatePreviewWindow(Toplevel):
    def __init__(self, parent, template_path: Path, theme_manager: ThemeManager):
        super().__init__(parent)
        self.parent = parent
        self.template_path = template_path  
        self.theme_manager = theme_manager
        self.photo = None
        
        self._configure_window()
        
        try:
            self._setup_ui()
            self._center_window()
        except Exception as e:
            self.destroy()
            messagebox.showerror(
                "Preview Error", 
                f"Unable to load template preview for '{template_path.name}'\n\nError: {str(e)}", 
                parent=parent
            )
    
    def _configure_window(self):
        self.title(f"Template Preview - {self.template_path.name}")
        self.config(bg=self.theme_manager.get_color('preview_bg_color'))
        self.resizable(False, False)
        self.transient(self.parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _on_close(self):
        if self.photo:
            try:
                del self.photo
            except Exception:
                pass
        self.destroy()
    
    def _setup_ui(self):
        try:
            img, original_size = self._load_and_resize_image()
            self.photo = ImageTk.PhotoImage(img)
            
            main_frame = Frame(self, bg=self.theme_manager.get_color('preview_bg_color'), padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            
            self._create_info_section(main_frame, original_size, img.size)
            self._create_image_section(main_frame)
            self._create_button_section(main_frame)
            
        except Exception as e:
            self._create_error_ui(str(e))
    
    def _load_and_resize_image(self) -> Tuple[Image.Image, Tuple[int, int]]:
        with open_image(self.template_path) as img:
            original_size = (img.width, img.height)
            
            max_size = 400
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            return img.copy(), original_size
    
    def _create_info_section(self, parent, original_size, current_size):
        info_frame = Frame(parent, bg=self.theme_manager.get_color('preview_bg_color'))
        info_frame.pack(fill="x", pady=(0, 15))
        
        Label(info_frame, text=f"File: {self.template_path.name}", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('fg_color'), 
              font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        Label(info_frame, text=f"Original Size: {original_size[0]}×{original_size[1]} pixels", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('secondary_fg_color'), 
              font=("Segoe UI", 9)).pack(anchor="w")
        
        if current_size != original_size:
            Label(info_frame, text=f"Preview Size: {current_size[0]}×{current_size[1]} pixels (scaled)", 
                  bg=self.theme_manager.get_color('preview_bg_color'), 
                  fg=self.theme_manager.get_color('secondary_fg_color'), 
                  font=("Segoe UI", 9)).pack(anchor="w")
    
    def _create_image_section(self, parent):
        image_frame = Frame(parent, bg=self.theme_manager.get_color('input_bg_color'), 
                           relief="solid", bd=1)
        image_frame.pack(pady=15)
        
        image_label = Label(image_frame, image=self.photo, 
                           bg=self.theme_manager.get_color('input_bg_color'))
        image_label.pack(padx=8, pady=8)
    
    def _create_button_section(self, parent):
        close_btn = Button(parent, text="Close", command=self._on_close,
                          bg=self.theme_manager.get_color('button_bg_color'), 
                          fg=self.theme_manager.get_color('button_fg_color'), 
                          bd=0, padx=30, pady=8, 
                          font=("Segoe UI", 9), cursor="hand2", relief="flat")
        close_btn.pack(pady=(20, 0))
        
        OptimizedHoverEffect(close_btn, 'close', self.theme_manager)
    
    def _create_error_ui(self, error_message: str):
        error_frame = Frame(self, bg=self.theme_manager.get_color('preview_bg_color'), 
                           padx=40, pady=40)
        error_frame.pack(fill="both", expand=True)
        
        Label(error_frame, text="⚠", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('error_fg_color'), 
              font=("Segoe UI", 24)).pack(pady=(0, 10))
        
        Label(error_frame, text="Unable to load image preview", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('error_fg_color'), 
              font=("Segoe UI", 11, "bold")).pack(pady=(0, 5))
        
        Label(error_frame, text=f"Error: {error_message}", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('fg_color'), 
              font=("Segoe UI", 9)).pack(pady=(0, 20))
        
        close_btn = Button(error_frame, text="Close", command=self._on_close,
                          bg=self.theme_manager.get_color('button_bg_color'), 
                          fg=self.theme_manager.get_color('button_fg_color'), 
                          bd=0, padx=30, pady=8, 
                          font=("Segoe UI", 9), cursor="hand2", relief="flat")
        close_btn.pack()
        
        OptimizedHoverEffect(close_btn, 'close', self.theme_manager)
    
    def _center_window(self):
        self.update_idletasks()
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        my_width = self.winfo_width()
        my_height = self.winfo_height()
        
        pos_x = parent_x + (parent_width - my_width) // 2
        pos_y = parent_y + (parent_height - my_height) // 2
        
        pos_x = max(0, pos_x)
        pos_y = max(0, pos_y)
        
        self.geometry(f"+{pos_x}+{pos_y}")

class EnhancedProfileManagerWindow(Toplevel):
    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.parent_app = parent_app
        self.theme_manager = parent_app.theme_manager
        
        self._configure_window()
        self._setup_ui()
        self._populate_profile_list()
        self._center_window()
    
    def _configure_window(self):
        self.transient(self.parent_app.root)
        self.title("Profile & Template Manager")
        self.config(bg=self.theme_manager.get_color('bg_color'))
        self.resizable(True, True)
        self.grab_set()
        self.minsize(600, 450)
    
    def _center_window(self):
        self.update_idletasks()
        parent = self.parent_app.root
        
        width, height = map(int, AppConstants.PROFILE_MANAGER_SIZE.split('x'))
        
        parent_x, parent_y = parent.winfo_x(), parent.winfo_y()
        parent_width, parent_height = parent.winfo_width(), parent.winfo_height()
        
        pos_x = parent_x + (parent_width - width) // 2
        pos_y = parent_y + (parent_height - height) // 2
        
        pos_x = max(0, pos_x)
        pos_y = max(0, pos_y)
        
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    
    def _setup_ui(self):
        main_frame = Frame(self, bg=self.theme_manager.get_color('bg_color'))
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        self._create_header(main_frame)
        self._create_directory_section(main_frame)
        self._create_content_section(main_frame)
    
    def _create_header(self, parent):
        header_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        header_frame.pack(fill="x", pady=(0, 15))
        
        title_label = Label(header_frame, text="Profile & Template Manager", 
                           bg=self.theme_manager.get_color('bg_color'), 
                           fg=self.theme_manager.get_color('fg_color'), 
                           font=("Segoe UI", 13, "bold"))
        title_label.pack(side="left")
    
    def _create_directory_section(self, parent):
        dir_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        dir_frame.pack(fill="x", pady=(0, 15))
        
        Label(dir_frame, text="Profiles Directory:", 
              bg=self.theme_manager.get_color('bg_color'), 
              fg=self.theme_manager.get_color('fg_color'), 
              font=("Segoe UI", 10)).pack(side="left")
        
        path_entry = Entry(dir_frame, textvariable=self.parent_app.profiles_root_path, 
                          state="readonly", 
                          readonlybackground=self.theme_manager.get_color('readonly_bg_color'), 
                          fg=self.theme_manager.get_color('input_fg_color'), 
                          bd=1, font=("Segoe UI", 9))
        path_entry.pack(side="left", fill="x", expand=True, padx=(10, 10))
        
        browse_btn = Button(dir_frame, text="Browse...", command=self._select_profiles_root, 
                           bg=self.theme_manager.get_color('button_bg_color'), 
                           fg=self.theme_manager.get_color('button_fg_color'), 
                           bd=0, padx=15, pady=6, font=("Segoe UI", 9), 
                           cursor="hand2", relief="flat")
        browse_btn.pack(side="right")
        
        OptimizedHoverEffect(browse_btn, 'browse', self.theme_manager)
    
    def _create_content_section(self, parent):
        content_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        content_frame.pack(fill="both", expand=True)
        
        self._create_profiles_panel(content_frame)
        self._create_templates_panel(content_frame)
    
    def _create_profiles_panel(self, parent):
        left_panel = LabelFrame(parent, text="Profiles", 
                               bg=self.theme_manager.get_color('bg_color'), 
                               fg=self.theme_manager.get_color('fg_color'), 
                               padx=10, pady=10, 
                               font=("Segoe UI", 10, "bold"))
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        profile_list_frame = Frame(left_panel, bg=self.theme_manager.get_color('bg_color'))
        profile_list_frame.pack(fill="both", expand=True)
        
        self.profile_listbox = Listbox(profile_list_frame, 
                                      bg=self.theme_manager.get_color('input_bg_color'), 
                                      fg=self.theme_manager.get_color('input_fg_color'), 
                                      bd=0, highlightthickness=0, 
                                      selectbackground=self.theme_manager.get_color('selection_bg_color'), 
                                      selectforeground=self.theme_manager.get_color('selection_fg_color'),
                                      exportselection=False, font=("Segoe UI", 9))
        self.profile_listbox.pack(side="left", fill="both", expand=True)
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)
        self.profile_listbox.bind("<Double-Button-1>", self._set_active_profile)
        
        profile_scrollbar = Scrollbar(profile_list_frame, command=self.profile_listbox.yview,
                                     bg=self.theme_manager.get_color('bg_color'),
                                     troughcolor=self.theme_manager.get_color('input_bg_color'),
                                     activebackground=self.theme_manager.get_color('selection_bg_color'))
        profile_scrollbar.pack(side="right", fill="y")
        self.profile_listbox.config(yscrollcommand=profile_scrollbar.set)

        self._create_profile_buttons(left_panel)
    
    def _create_profile_buttons(self, parent):
        profile_buttons_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        profile_buttons_frame.pack(fill="x", pady=(10, 0))
        
        button_style = {
            "bg": self.theme_manager.get_color('button_bg_color'), 
            "fg": self.theme_manager.get_color('button_fg_color'), 
            "bd": 0, "padx": 12, "pady": 5, 
            "font": ("Segoe UI", 9), "cursor": "hand2", "relief": "flat"
        }
        
        new_btn = Button(profile_buttons_frame, text="New", command=self._create_profile, **button_style)
        new_btn.pack(side="left")
        OptimizedHoverEffect(new_btn, 'new', self.theme_manager)
        
        rename_btn = Button(profile_buttons_frame, text="Rename", command=self._rename_profile, **button_style)
        rename_btn.pack(side="left", padx=(6,0))
        OptimizedHoverEffect(rename_btn, 'rename', self.theme_manager)
        
        delete_btn = Button(profile_buttons_frame, text="Delete", command=self._delete_profile, **button_style)
        delete_btn.pack(side="left", padx=(6,0))
        OptimizedHoverEffect(delete_btn, 'delete', self.theme_manager)
        
        set_active_btn = Button(profile_buttons_frame, text="Set Active", 
                               command=self._set_active_profile, **button_style)
        set_active_btn.pack(side="right")
        OptimizedHoverEffect(set_active_btn, 'set_active', self.theme_manager)
    
    def _create_templates_panel(self, parent):
        right_panel = LabelFrame(parent, text="Templates", 
                                bg=self.theme_manager.get_color('bg_color'), 
                                fg=self.theme_manager.get_color('fg_color'), 
                                padx=10, pady=10, 
                                font=("Segoe UI", 10, "bold"))
        right_panel.pack(side="right", fill="both", expand=True, padx=(8, 0))
        
        template_list_frame = Frame(right_panel, bg=self.theme_manager.get_color('bg_color'))
        template_list_frame.pack(fill="both", expand=True)
        
        self.template_listbox = Listbox(template_list_frame, 
                                       bg=self.theme_manager.get_color('input_bg_color'), 
                                       fg=self.theme_manager.get_color('input_fg_color'), 
                                       bd=0, highlightthickness=0, 
                                       selectbackground=self.theme_manager.get_color('selection_bg_color'), 
                                       selectforeground=self.theme_manager.get_color('selection_fg_color'),
                                       exportselection=False, font=("Segoe UI", 9))
        self.template_listbox.pack(side="left", fill="both", expand=True)
        self.template_listbox.bind("<Double-Button-1>", self._preview_template)
        
        template_scrollbar = Scrollbar(template_list_frame, command=self.template_listbox.yview,
                                      bg=self.theme_manager.get_color('bg_color'),
                                      troughcolor=self.theme_manager.get_color('input_bg_color'),
                                      activebackground=self.theme_manager.get_color('selection_bg_color'))
        template_scrollbar.pack(side="right", fill="y")
        self.template_listbox.config(yscrollcommand=template_scrollbar.set)
        
        self._create_template_buttons(right_panel)
    
    def _create_template_buttons(self, parent):
        template_buttons_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        template_buttons_frame.pack(fill="x", pady=(10, 0))
        
        button_style = {
            "bg": self.theme_manager.get_color('button_bg_color'), 
            "fg": self.theme_manager.get_color('button_fg_color'), 
            "bd": 0, "padx": 12, "pady": 5, 
            "font": ("Segoe UI", 9), "cursor": "hand2", "relief": "flat"
        }
        
        preview_btn = Button(template_buttons_frame, text="Preview", 
                           command=self._preview_template, **button_style)
        preview_btn.pack(side="left")
        OptimizedHoverEffect(preview_btn, 'preview', self.theme_manager)
        
        delete_template_btn = Button(template_buttons_frame, text="Delete", 
                                   command=self._delete_template, **button_style)
        delete_template_btn.pack(side="left", padx=(6,0))
        OptimizedHoverEffect(delete_template_btn, 'delete', self.theme_manager)
    
    def _populate_profile_list(self):
        self.profile_listbox.delete(0, 'end')
        
        try:
            profiles = sorted(self.parent_app.get_profiles())
            if not profiles:
                self.profile_listbox.insert('end', "(No profiles found)")
                return
            
            active_profile = self.parent_app.active_profile.get()
            for i, profile in enumerate(profiles):
                display_text = f"● {profile}" if profile == active_profile else f"  {profile}"
                self.profile_listbox.insert('end', display_text)
                
                if profile == active_profile:
                    self.profile_listbox.selection_set(i)
                    self.profile_listbox.see(i)
                    self._populate_template_list(profile)
                    
        except Exception as e:
            error_msg = f"Error loading profiles: {str(e)}"
            self.profile_listbox.insert('end', error_msg)
            print(error_msg)
    
    def _populate_template_list(self, profile_name: str):
        self.template_listbox.delete(0, 'end')
        
        if not profile_name or profile_name.startswith("(") or profile_name.startswith("Error"):
            return
        
        try:
            profile_path = Path(self.parent_app.profiles_root_path.get()) / profile_name
            if not profile_path.is_dir():
                self.template_listbox.insert('end', "(Profile directory not found)")
                return
            
            template_files = [
                f for f in profile_path.iterdir()
                if f.is_file() and f.suffix.lower() in AppConstants.SUPPORTED_IMAGE_EXTENSIONS
            ]
            
            if not template_files:
                self.template_listbox.insert('end', "(No templates found)")
                return
            
            template_files.sort(key=human_sort_key)
            
            for template_file in template_files:
                self.template_listbox.insert('end', template_file.name)
                
        except Exception as e:
            error_msg = f"Error loading templates: {str(e)}"
            self.template_listbox.insert('end', error_msg)
            print(error_msg)
    
    def _on_profile_select(self, event=None):
        selection = self.profile_listbox.curselection()
        if not selection:
            self.template_listbox.delete(0, 'end')
            return
        
        selected_text = self.profile_listbox.get(selection[0])
        if selected_text.startswith("(") or selected_text.startswith("Error"):
            self.template_listbox.delete(0, 'end')
            return
        
        profile_name = selected_text.replace("● ", "").replace("  ", "")
        self._populate_template_list(profile_name)
    
    def _get_selected_profile(self) -> Optional[str]:
        selection = self.profile_listbox.curselection()
        if not selection:
            return None
        
        selected_text = self.profile_listbox.get(selection[0])
        if selected_text.startswith("(") or selected_text.startswith("Error"):
            return None
        
        return selected_text.replace("● ", "").replace("  ", "")
    
    @safe_path_operation
    def _select_profiles_root(self):
        try:
            path = filedialog.askdirectory(
                title="Select Profiles Root Directory", 
                parent=self,
                initialdir=self.parent_app.profiles_root_path.get()
            )
            if path:
                self.parent_app.profiles_root_path.set(path)
                self.parent_app._update_profile_list()
                self._populate_profile_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not change profiles directory: {e}", parent=self)
    
    def _create_profile(self):
        try:
            self.parent_app._create_new_profile(parent_window=self)
            self._populate_profile_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not create profile: {e}", parent=self)
    
    def _rename_profile(self):
        profile_name = self._get_selected_profile()
        if not profile_name:
            messagebox.showwarning("No Selection", "Please select a profile to rename.", parent=self)
            return
        
        try:
            new_name = simpledialog.askstring(
                "Rename Profile", 
                f"Enter a new name for '{profile_name}':",
                parent=self,
                initialvalue=profile_name
            )
            
            if not new_name or not new_name.strip() or new_name == profile_name:
                return
            
            if not validate_filename(new_name):
                messagebox.showerror(
                    "Invalid Name", 
                    "Profile name contains invalid characters.",
                    parent=self
                )
                return
            
            root_path = Path(self.parent_app.profiles_root_path.get())
            old_path, new_path = root_path / profile_name, root_path / new_name
            
            if new_path.exists():
                messagebox.showerror("Error", f"A profile named '{new_name}' already exists.", parent=self)
                return
            
            old_path.rename(new_path)
            self.parent_app._rename_profile_config(profile_name, new_name)
            
            if self.parent_app.active_profile.get() == profile_name:
                self.parent_app.active_profile.set(new_name)
            
            self.parent_app._update_profile_list()
            self._populate_profile_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not rename profile: {e}", parent=self)
    
    def _delete_profile(self):
        profile_name = self._get_selected_profile()
        if not profile_name:
            messagebox.showwarning("No Selection", "Please select a profile to delete.", parent=self)
            return
        
        if not messagebox.askyesno(
            "Confirm Deletion", 
            f"Are you sure you want to permanently delete the profile '{profile_name}' and all its templates?\n\n"
            f"This action cannot be undone.",
            parent=self
        ):
            return
        
        try:
            profile_path = Path(self.parent_app.profiles_root_path.get()) / profile_name
            if profile_path.exists():
                shutil.rmtree(profile_path)
            
            self.parent_app._delete_profile_config(profile_name)
            
            if self.parent_app.active_profile.get() == profile_name:
                self.parent_app.active_profile.set("")
            
            self.parent_app._update_profile_list()
            self._populate_profile_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete profile: {e}", parent=self)
    
    def _set_active_profile(self, event=None):
        profile_name = self._get_selected_profile()
        if not profile_name:
            messagebox.showwarning("No Selection", "Please select a profile to set as active.", parent=self)
            return
        
        try:
            self.parent_app.active_profile.set(profile_name)
            self.parent_app._on_profile_change()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not set active profile: {e}", parent=self)
    
    def _preview_template(self, event=None):
        template_selection = self.template_listbox.curselection()
        if not template_selection:
            messagebox.showwarning("No Selection", "Please select a template to preview.", parent=self)
            return
        
        template_name = self.template_listbox.get(template_selection[0])
        if template_name.startswith("(") or template_name.startswith("Error"):
            return
        
        profile_name = self._get_selected_profile()
        if not profile_name:
            return
        
        try:
            template_path = Path(self.parent_app.profiles_root_path.get()) / profile_name / template_name
            
            if not template_path.exists():
                messagebox.showerror("Error", f"Template file '{template_name}' not found.", parent=self)
                return
            
            EnhancedTemplatePreviewWindow(self, template_path, self.theme_manager)
        except Exception as e:
            messagebox.showerror("Error", f"Could not preview template: {e}", parent=self)
    
    def _delete_template(self):
        template_selection = self.template_listbox.curselection()
        if not template_selection:
            messagebox.showwarning("No Selection", "Please select a template to delete.", parent=self)
            return
        
        template_name = self.template_listbox.get(template_selection[0])
        if template_name.startswith("(") or template_name.startswith("Error"):
            return
        
        profile_name = self._get_selected_profile()
        if not profile_name:
            return
        
        if not messagebox.askyesno(
            "Confirm Deletion", 
            f"Are you sure you want to delete the template '{template_name}'?\n\nThis action cannot be undone.",
            parent=self
        ):
            return
        
        try:
            template_path = Path(self.parent_app.profiles_root_path.get()) / profile_name / template_name
            if template_path.exists():
                template_path.unlink()
                
                self.parent_app.template_cache.invalidate_template(template_path)
                self._populate_template_list(profile_name)
                self.parent_app._populate_sequence_listbox()
                
                messagebox.showinfo("Success", f"Template '{template_name}' deleted successfully.", parent=self)
            else:
                messagebox.showerror("Error", f"Template file '{template_name}' not found.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete template: {e}", parent=self)

class NexusAutoDL:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(f"Nexus AutoDL {AppConstants.VERSION}")
        self.root.resizable(False, False)
        
        self._init_variables()
        self._load_config()
        
        self.theme_manager = ThemeManager(is_dark_mode=self.dark_mode.get())
        self.root.config(bg=self.theme_manager.get_color('bg_color'))
        
        self._init_state()
        
        self.template_cache = EnhancedTemplateCache(max_cache_size=AppConstants.CACHE_SIZE)
        self.templates: Dict[str, Image.Image] = {}
        
        self._setup_ttk_style()
        self._setup_ui()
        self._update_profile_list()
        self._update_always_on_top()
        
        self._init_keyboard_listener()
        
        self.root.protocol("WM_DELETE_WINDOW", self._terminate_app)
    
    def _init_variables(self):
        self.confidence = DoubleVar()
        self.grayscale = BooleanVar()
        self.min_sleep_seconds = DoubleVar()
        self.max_sleep_seconds = DoubleVar()
        self.search_mode = StringVar()
        
        self.always_on_top = BooleanVar()
        self.dark_mode = BooleanVar()
        self.show_visual_feedback = BooleanVar()
        self.feedback_color = StringVar()
        self.feedback_duration = IntVar()
        
        self.profiles_root_path = StringVar()
        self.active_profile = StringVar()
    
    def _init_state(self):
        self._is_running = False
        self._after_id: Optional[str] = None
        self._last_active_profile = ""
        self.sequence_index = 0
        
        self.log_window: Optional[Toplevel] = None
        self.log_text_widget: Optional[Text] = None
        self.capture_window: Optional[Toplevel] = None
        
        self.hover_effects: List[OptimizedHoverEffect] = []
        self.tooltips: List[EnhancedTooltip] = []
    
    def _init_keyboard_listener(self):
        try:
            self.keyboard_listener = keyboard.Listener(on_press=self._on_key_press)
            self.keyboard_listener.start()
        except Exception as e:
            print(f"Failed to initialize keyboard listener: {e}")
            self.keyboard_listener = None
    
    def _setup_ttk_style(self):
        try:
            style = ttk.Style()
            style.theme_use('clam')
            
            style.configure("TCombobox", 
                           fieldbackground=self.theme_manager.get_color('input_bg_color'), 
                           background=self.theme_manager.get_color('button_bg_color'), 
                           foreground=self.theme_manager.get_color('input_fg_color'), 
                           arrowcolor=self.theme_manager.get_color('fg_color'), 
                           selectbackground=self.theme_manager.get_color('selection_bg_color'), 
                           selectforeground=self.theme_manager.get_color('selection_fg_color'), 
                           bordercolor=self.theme_manager.get_color('border_color'),
                           lightcolor=self.theme_manager.get_color('bg_color'), 
                           darkcolor=self.theme_manager.get_color('bg_color'))
            
            style.map('TCombobox', 
                     fieldbackground=[('readonly', self.theme_manager.get_color('readonly_bg_color'))], 
                     selectbackground=[('readonly', self.theme_manager.get_color('selection_bg_color'))], 
                     selectforeground=[('readonly', self.theme_manager.get_color('selection_fg_color'))])
            
            style.configure("TRadiobutton", 
                           background=self.theme_manager.get_color('bg_color'), 
                           foreground=self.theme_manager.get_color('fg_color'), 
                           indicatorcolor=self.theme_manager.get_color('input_bg_color'))
            
            style.map("TRadiobutton", 
                     background=[('active', self.theme_manager.get_color('bg_color'))], 
                     indicatorcolor=[('active', self.theme_manager.get_color('selection_bg_color'))], 
                     foreground=[('active', self.theme_manager.get_color('fg_color'))])
        except Exception as e:
            print(f"Failed to setup TTK styles: {e}")
    
    def _setup_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.hover_effects.clear()
        self.tooltips.clear()
        
        main_frame = Frame(self.root, padx=12, pady=12, bg=self.theme_manager.get_color('bg_color'))
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.grid_columnconfigure(0, weight=1)
        
        styles = self._create_style_dictionaries()
        
        self._create_profile_section(main_frame, styles)
        self._create_tuning_section(main_frame, styles)
        self._create_display_section(main_frame, styles)
        self._create_sequence_section(main_frame, styles)
        self._create_action_section(main_frame, styles)
        self._create_status_section(main_frame, styles)
        
        main_frame.grid_columnconfigure(0, weight=1)
        
        self._add_tooltips()
        
        self._toggle_feedback_options()
        self._toggle_sequence_editor()
    
    def _create_style_dictionaries(self) -> Dict[str, Dict[str, Any]]:
        return {
            'label': {
                "bg": self.theme_manager.get_color('bg_color'), 
                "fg": self.theme_manager.get_color('fg_color'), 
                "font": ("Segoe UI", 9)
            },
            'entry': {
                "bg": self.theme_manager.get_color('input_bg_color'), 
                "fg": self.theme_manager.get_color('input_fg_color'), 
                "insertbackground": self.theme_manager.get_color('input_fg_color'), 
                "bd": 1, "highlightthickness": 0, "font": ("Segoe UI", 9)
            },
            'button': {
                "bg": self.theme_manager.get_color('button_bg_color'), 
                "fg": self.theme_manager.get_color('button_fg_color'), 
                "bd": 0, "padx": 12, "pady": 5, "font": ("Segoe UI", 9), 
                "cursor": "hand2", "relief": "flat"
            },
            'checkbox': {
                "bg": self.theme_manager.get_color('bg_color'),
                "fg": self.theme_manager.get_color('fg_color'),
                "font": ("Segoe UI", 9),
                "selectcolor": self.theme_manager.get_color('input_bg_color'), 
                "activebackground": self.theme_manager.get_color('bg_color')
            },
            'labelframe': {
                "bg": self.theme_manager.get_color('bg_color'), 
                "fg": self.theme_manager.get_color('fg_color'), 
                "padx": 12, "pady": 10, "font": ("Segoe UI", 10, "bold")
            }
        }
    
    def _create_profile_section(self, parent, styles):
        self.profile_frame = LabelFrame(parent, text="Profile Settings", **styles['labelframe'])
        self.profile_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        Label(self.profile_frame, text="Active Profile:", **styles['label']).grid(row=0, column=0, sticky="w", pady=3)
        
        self.profile_combobox = ttk.Combobox(self.profile_frame, textvariable=self.active_profile, 
                                            state="readonly", width=28, font=("Segoe UI", 9))
        self.profile_combobox.grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=3)
        self.profile_combobox.bind("<<ComboboxSelected>>", self._on_profile_change)
        
        self.manage_profiles_button = Button(self.profile_frame, text="Manage...", 
                                           command=self._open_profile_manager, **styles['button'])
        self.manage_profiles_button.grid(row=0, column=2, pady=3)
        self.profile_frame.grid_columnconfigure(1, weight=1)
        
        hover_effect = OptimizedHoverEffect(self.manage_profiles_button, 'manage', self.theme_manager)
        self.hover_effects.append(hover_effect)
    
    def _create_tuning_section(self, parent, styles):
        tuning_frame = LabelFrame(parent, text="Automation Tuning", **styles['labelframe'])
        tuning_frame.grid(row=1, column=0, sticky="ew", pady=10)
        
        Label(tuning_frame, text="Confidence:", **styles['label']).grid(row=0, column=0, sticky="w", pady=3)
        self.confidence_entry = Entry(tuning_frame, textvariable=self.confidence, **styles['entry'], width=10)
        self.confidence_entry.grid(row=0, column=1, padx=(8, 0), pady=3)
        
        Label(tuning_frame, text="Search Mode:", **styles['label']).grid(row=0, column=2, sticky="w", padx=(20,0), pady=3)
        radio_frame = Frame(tuning_frame, bg=self.theme_manager.get_color('bg_color'))
        radio_frame.grid(row=0, column=3, columnspan=3, sticky="w", padx=(8, 0), pady=3)
        
        self.priority_radio = ttk.Radiobutton(radio_frame, text="Priority", variable=self.search_mode, 
                                             value="priority", command=self._toggle_sequence_editor, style="TRadiobutton")
        self.priority_radio.pack(side="left", padx=(0, 20))
        
        self.sequence_radio = ttk.Radiobutton(radio_frame, text="Sequence", variable=self.search_mode, 
                                             value="sequence", command=self._toggle_sequence_editor, style="TRadiobutton")
        self.sequence_radio.pack(side="left")
        
        Label(tuning_frame, text="Min Sleep (s):", **styles['label']).grid(row=1, column=0, sticky="w", pady=(10,3))
        self.min_sleep_entry = Entry(tuning_frame, textvariable=self.min_sleep_seconds, **styles['entry'], width=10)
        self.min_sleep_entry.grid(row=1, column=1, padx=(8, 0), pady=(10,3))
        
        Label(tuning_frame, text="Max Sleep (s):", **styles['label']).grid(row=1, column=2, sticky="w", padx=(20, 0), pady=(10,3))
        self.max_sleep_entry = Entry(tuning_frame, textvariable=self.max_sleep_seconds, **styles['entry'], width=10)
        self.max_sleep_entry.grid(row=1, column=3, padx=(8, 0), pady=(10,3))
        
        self.grayscale_check = Checkbutton(tuning_frame, text="Grayscale Matching", 
                                          variable=self.grayscale, **styles['checkbox'])
        self.grayscale_check.grid(row=2, column=0, columnspan=2, sticky='w', pady=(10,3))
    
    def _create_display_section(self, parent, styles):
        display_frame = LabelFrame(parent, text="Display & Appearance", **styles['labelframe'])
        display_frame.grid(row=2, column=0, sticky="ew", pady=10)
        
        self.always_on_top_check = Checkbutton(display_frame, text="Always on Top", 
                                              variable=self.always_on_top, command=self._update_always_on_top, 
                                              **styles['checkbox'])
        self.always_on_top_check.grid(row=0, column=0, sticky='w', pady=3)
        
        self.dark_mode_check = Checkbutton(display_frame, text="Dark Mode", 
                                          variable=self.dark_mode, command=self._toggle_theme, 
                                          **styles['checkbox'])
        self.dark_mode_check.grid(row=0, column=1, sticky='w', padx=(30, 0), pady=3)
        
        self.visual_feedback_check = Checkbutton(display_frame, text="Visual Feedback", 
                                                variable=self.show_visual_feedback, 
                                                command=self._toggle_feedback_options, 
                                                **styles['checkbox'])
        self.visual_feedback_check.grid(row=1, column=0, columnspan=2, sticky='w', pady=(8,3))
        
        self.feedback_options_frame = Frame(display_frame, bg=self.theme_manager.get_color('bg_color'))
        
        self._create_feedback_options(styles)
    
    def _create_feedback_options(self, styles):
        Label(self.feedback_options_frame, text="Color:", **styles['label']).grid(row=0, column=0, sticky="w", pady=3)
        
        self.color_swatch = Label(self.feedback_options_frame, text="   ", 
                                 bg=self.feedback_color.get(), relief="solid", bd=1, cursor="hand2")
        self.color_swatch.grid(row=0, column=1, padx=(8, 8), pady=3)
        self.color_swatch.bind("<Button-1>", self._choose_color)
        
        self.color_entry = Entry(self.feedback_options_frame, textvariable=self.feedback_color, 
                                **styles['entry'], width=8, state="readonly", 
                                readonlybackground=self.theme_manager.get_color('readonly_bg_color'))
        self.color_entry.grid(row=0, column=2, pady=3)
        
        Label(self.feedback_options_frame, text="Duration (ms):", **styles['label']).grid(row=0, column=3, sticky="w", padx=(15,0), pady=3)
        self.duration_entry = Entry(self.feedback_options_frame, textvariable=self.feedback_duration, 
                                   **styles['entry'], width=8)
        self.duration_entry.grid(row=0, column=4, padx=(8, 0), pady=3)
    
    def _create_sequence_section(self, parent, styles):
        self.sequence_frame = LabelFrame(parent, text="Sequence Editor", **styles['labelframe'])
        
        self.sequence_listbox = Listbox(self.sequence_frame, 
                                       bg=self.theme_manager.get_color('input_bg_color'), 
                                       fg=self.theme_manager.get_color('input_fg_color'), 
                                       bd=0, highlightthickness=0, 
                                       selectbackground=self.theme_manager.get_color('selection_bg_color'), 
                                       selectforeground=self.theme_manager.get_color('selection_fg_color'),
                                       height=4, exportselection=False, font=("Segoe UI", 9))
        self.sequence_listbox.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        seq_button_frame = Frame(self.sequence_frame, bg=self.theme_manager.get_color('bg_color'))
        seq_button_frame.pack(side="right")
        
        seq_button_style = {**styles['button'], "padx": 8, "pady": 3}
        
        self.up_btn = Button(seq_button_frame, text="▲", command=self._move_template_up, **seq_button_style)
        self.up_btn.pack(pady=(0, 3), fill="x")
        up_hover = OptimizedHoverEffect(self.up_btn, 'up', self.theme_manager)
        self.hover_effects.append(up_hover)
        
        self.down_btn = Button(seq_button_frame, text="▼", command=self._move_template_down, **seq_button_style)
        self.down_btn.pack(fill="x")
        down_hover = OptimizedHoverEffect(self.down_btn, 'down', self.theme_manager)
        self.hover_effects.append(down_hover)
    
    def _create_action_section(self, parent, styles):
        action_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        action_frame.grid(row=4, column=0, sticky="ew", pady=(15, 0))
        
        self.create_button = Button(action_frame, text="Create Template", 
                                   command=self._start_capture_mode, **styles['button'])
        self.create_button.pack(side="left", expand=True, padx=(0, 8))
        create_hover = OptimizedHoverEffect(self.create_button, 'create', self.theme_manager)
        self.hover_effects.append(create_hover)
        
        self.start_button = Button(action_frame, text="Start (F3)", 
                                  command=self._start_handler, **styles['button'])
        self.start_button.pack(side="left", expand=True)
        start_hover = OptimizedHoverEffect(self.start_button, 'start', self.theme_manager)
        self.hover_effects.append(start_hover)
    
    def _create_status_section(self, parent, styles):
        status_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        status_frame.grid(row=5, column=0, sticky="ew", pady=(10,0))
        
        Label(status_frame, text="F3: Start/Resume | F4: Pause", 
              bg=self.theme_manager.get_color('bg_color'), 
              fg=self.theme_manager.get_color('secondary_fg_color'), 
              font=("Segoe UI", 8)).pack(side="left")
        
        Label(status_frame, text=AppConstants.VERSION, 
              bg=self.theme_manager.get_color('bg_color'), 
              fg=self.theme_manager.get_color('secondary_fg_color'), 
              font=("Segoe UI", 8)).pack(side="right")
    
    def _add_tooltips(self):
        tooltip_configs = [
            (self.profile_combobox, "Select the active profile for automation."),
            (self.manage_profiles_button, "Open the Profile Manager to create, rename, or delete profiles and templates."),
            (self.confidence_entry, "The accuracy required for a match (0.0 to 1.0).\nLower values are less strict. Requires OpenCV."),
            (self.min_sleep_entry, "The minimum time in seconds to wait between search cycles."),
            (self.max_sleep_entry, "The maximum time in seconds to wait between search cycles."),
            (self.priority_radio, "Checks for templates one by one, in alphabetical order.\nIt clicks the first match it finds and then rests."),
            (self.sequence_radio, "Searches for templates one by one in the exact order\ndefined in the Sequence Editor."),
            (self.grayscale_check, "Searches for templates in black and white.\nThis is often faster but can be less accurate for some images."),
            (self.sequence_listbox, "Define the exact order templates should be searched in Sequence Mode."),
            (self.always_on_top_check, "Keeps the application and log windows above all other windows."),
            (self.dark_mode_check, "Switch between Light Mode (default) and Dark Mode themes."),
            (self.visual_feedback_check, "Briefly shows a colored border around a matched template before clicking."),
            (self.color_swatch, "Click to choose the color of the feedback border."),
            (self.color_entry, "The currently selected color in hex format."),
            (self.duration_entry, "How long the feedback border stays on screen, in milliseconds."),
            (self.create_button, "Capture a new template by drawing a rectangle on your screen. Press ESC to cancel."),
            (self.start_button, "Start or Resume the automation process (F3)."),
            (self.up_btn, "Move the selected template up in the sequence order."),
            (self.down_btn, "Move the selected template down in the sequence order.")
        ]
        
        for widget, text in tooltip_configs:
            if widget:
                tooltip = EnhancedTooltip(widget, text, self.theme_manager)
                self.tooltips.append(tooltip)
    
    def _toggle_theme(self):
        try:
            is_dark = self.dark_mode.get()
            
            if not self.theme_manager.switch_theme(is_dark):
                return
            
            log_was_open = self._close_log_window_if_open()
            
            EnhancedTooltip.hide_all()
            
            self.root.config(bg=self.theme_manager.get_color('bg_color'))
            
            self._setup_ttk_style()
            
            OptimizedHoverEffect.update_all_themes(self.theme_manager)
            EnhancedTooltip.update_all_themes(self.theme_manager)
            
            self._setup_ui()
            
            self._update_profile_list()
            
            if log_was_open and self._is_running:
                self.root.after(AppConstants.FEEDBACK_WINDOW_DELAY, self._show_log_window)
            
        except Exception as e:
            messagebox.showerror("Theme Error", f"Could not switch theme: {e}")
    
    def _close_log_window_if_open(self) -> bool:
        log_was_open = self.log_window is not None and self.log_window.winfo_exists()
        if log_was_open:
            try:
                self.log_window.destroy()
            except Exception:
                pass
            finally:
                self.log_window = None
                self.log_text_widget = None
        return log_was_open
    
    def _toggle_feedback_options(self):
        if self.show_visual_feedback.get(): 
            self.feedback_options_frame.grid(row=2, column=0, columnspan=4, sticky='w', padx=(25, 0), pady=(8, 0))
            try:
                current_color = self.feedback_color.get()
                if hasattr(self, 'color_swatch') and current_color:
                    self.color_swatch.config(bg=current_color)
            except Exception:
                pass
        else: 
            self.feedback_options_frame.grid_forget()
    
    def _toggle_sequence_editor(self):
        self._populate_sequence_listbox()
        if self.search_mode.get() == "sequence":
            self.sequence_frame.grid(row=3, column=0, sticky="ew", pady=10)
        else:
            self.sequence_frame.grid_forget()
    
    def _choose_color(self, event=None):
        try:
            _, color_hex = colorchooser.askcolor(
                parent=self.root, 
                initialcolor=self.feedback_color.get(),
                title="Choose Feedback Color"
            )
            if color_hex: 
                self.feedback_color.set(color_hex)
                self.color_swatch.config(bg=color_hex)
        except Exception as e:
            messagebox.showerror("Color Chooser Error", f"Could not open color chooser: {e}")
    
    def _show_feedback_box(self, box):
        try:
            feedback_window = Toplevel(self.root)
            feedback_window.overrideredirect(True)
            feedback_window.geometry(f'{box.width}x{box.height}+{box.left}+{box.top}')
            feedback_window.config(bg=AppConstants.TRANSPARENT_COLOR)
            feedback_window.wm_attributes("-transparentcolor", AppConstants.TRANSPARENT_COLOR)
            feedback_window.attributes("-topmost", True)
            
            border_frame = Frame(feedback_window, 
                               highlightbackground=self.feedback_color.get(), 
                               highlightthickness=3, 
                               bg=AppConstants.TRANSPARENT_COLOR)
            border_frame.pack(fill="both", expand=True)
            
            self.root.update_idletasks()
            return feedback_window
        except Exception as e:
            print(f"Failed to create feedback box: {e}")
            return None
    
    @safe_path_operation
    def _start_capture_mode(self):
        if not self.active_profile.get(): 
            messagebox.showwarning("No Profile Selected", 
                                 "Please select or create a profile before adding a template.")
            return
        
        try:
            self.root.withdraw()
            self.capture_window = Toplevel(self.root)
            self.capture_window.attributes("-fullscreen", True)
            self.capture_window.attributes("-alpha", 0.3)
            self.capture_window.attributes("-topmost", True)
            self.capture_window.focus_set()
            
            self.capture_canvas = Canvas(self.capture_window, cursor="cross", bg="grey")
            self.capture_canvas.pack(fill="both", expand=True)
            self.capture_canvas.focus_set()
            
            self.rect, self.start_x, self.start_y = None, None, None
            
            self.capture_canvas.bind("<Button-1>", self._on_capture_press)
            self.capture_canvas.bind("<B1-Motion>", self._on_capture_drag)
            self.capture_canvas.bind("<ButtonRelease-1>", self._on_capture_release)
            self.capture_window.bind("<KeyPress-Escape>", self._cancel_capture)
            self.capture_canvas.bind("<KeyPress-Escape>", self._cancel_capture)
            
        except Exception as e:
            self._ensure_main_window_visible()
            messagebox.showerror("Capture Error", f"Could not start capture mode: {e}")
    
    def _ensure_main_window_visible(self):
        try:
            self.root.deiconify()
            self.root.lift()
        except Exception:
            pass
    
    def _cancel_capture(self, event=None):
        try:
            if hasattr(self, 'capture_window') and self.capture_window and self.capture_window.winfo_exists():
                self.capture_window.destroy()
                self.capture_window = None
        except Exception:
            pass
        finally:
            self._ensure_main_window_visible()
    
    def _on_capture_press(self, event):
        self.start_x = self.capture_canvas.canvasx(event.x)
        self.start_y = self.capture_canvas.canvasy(event.y)
        self.rect = self.capture_canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, 
            outline='red', width=2
        )
    
    def _on_capture_drag(self, event):
        cur_x = self.capture_canvas.canvasx(event.x)
        cur_y = self.capture_canvas.canvasy(event.y)
        self.capture_canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)
    
    def _on_capture_release(self, event):
        try:
            end_x = self.capture_canvas.canvasx(event.x)
            end_y = self.capture_canvas.canvasy(event.y)
            
            self.capture_window.destroy()
            self.capture_window = None
            
            x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
            x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
            width, height = x2 - x1, y2 - y1
            
            if width <= AppConstants.MIN_CAPTURE_SIZE or height <= AppConstants.MIN_CAPTURE_SIZE:
                messagebox.showwarning(
                    "Capture Too Small", 
                    f"Please capture an area larger than {AppConstants.MIN_CAPTURE_SIZE}×{AppConstants.MIN_CAPTURE_SIZE} pixels.\n"
                    f"Current size: {int(width)}×{int(height)} pixels"
                )
                return
            
            region_tuple = (int(x1), int(y1), int(width), int(height))
            img = pyautogui.screenshot(region=region_tuple)
            
            self._save_captured_template(img)
            
        except Exception as e: 
            messagebox.showerror("Capture Error", f"Failed to save template: {e}")
        finally:
            self._ensure_main_window_visible()
    
    @safe_path_operation
    def _save_captured_template(self, img):
        try:
            profile_dir = Path(self.profiles_root_path.get()) / self.active_profile.get()
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = profile_dir / f"template_{timestamp}.png"
            
            counter = 1
            while save_path.exists():
                save_path = profile_dir / f"template_{timestamp}_{counter:02d}.png"
                counter += 1
            
            img.save(save_path, "PNG", optimize=True)
            
            self.template_cache.clear_cache()
            self._populate_sequence_listbox()
            
            messagebox.showinfo(
                "Template Saved", 
                f"Template saved successfully to profile '{self.active_profile.get()}':\n\n{save_path.name}\n\n"
                f"Size: {img.width}×{img.height} pixels"
            )
            
        except Exception as e:
            raise Exception(f"Failed to save template: {e}")
    
    def _log(self, message: str, level: str = "INFO"):
        if not self.log_text_widget:
            return
        
        try:
            self.root.after_idle(self._write_log_message, message, level)
        except Exception:
            pass
    
    def _write_log_message(self, message: str, level: str):
        try:
            self.log_text_widget.config(state="normal")
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_text_widget.insert("end", f"[{timestamp}][{level}] {message}\n")
            self.log_text_widget.see("end")
            self.log_text_widget.config(state="disabled")
        except Exception:
            pass
    
    def _load_config(self):
        try:
            if Path(AppConstants.CONFIG_FILE).exists():
                with open(AppConstants.CONFIG_FILE, "r", encoding='utf-8') as f: 
                    self.config = json.load(f)
            else:
                self.config = {}
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Failed to load config: {e}")
            self.config = {}
        
        self._load_validated_settings()
        self._load_profile_settings()
        self._last_active_profile = self.active_profile.get()
    
    def _load_validated_settings(self):
        is_dark = self.config.get("dark_mode", False)
        if isinstance(is_dark, bool):
            self.dark_mode.set(is_dark)
        else:
            self.dark_mode.set(False)
        
        profiles_path = self.config.get("profiles_root_path", "profiles")
        if isinstance(profiles_path, str) and profiles_path.strip():
            self.profiles_root_path.set(profiles_path)
        else:
            self.profiles_root_path.set("profiles")
        
        active_profile = self.config.get("active_profile", "")
        if isinstance(active_profile, str):
            self.active_profile.set(active_profile)
        else:
            self.active_profile.set("")
        
        self.always_on_top.set(bool(self.config.get("always_on_top", False)))
        self.show_visual_feedback.set(bool(self.config.get("show_visual_feedback", False)))
        
        feedback_color = self.config.get("feedback_color", "#00FF00")
        if isinstance(feedback_color, str) and feedback_color.startswith("#") and len(feedback_color) == 7:
            self.feedback_color.set(feedback_color)
        else:
            self.feedback_color.set("#00FF00")
        
        duration = self.config.get("feedback_duration", 400)
        if isinstance(duration, (int, float)) and 100 <= duration <= 5000:
            self.feedback_duration.set(int(duration))
        else:
            self.feedback_duration.set(400)
    
    def _save_config(self):
        try:
            self._save_current_profile_settings()
            
            config_data = {
                "dark_mode": self.dark_mode.get(),
                "profiles_root_path": self.profiles_root_path.get(),
                "active_profile": self.active_profile.get(),
                "always_on_top": self.always_on_top.get(),
                "show_visual_feedback": self.show_visual_feedback.get(),
                "feedback_color": self.feedback_color.get(),
                "feedback_duration": self.feedback_duration.get(),
                "profile_settings": self.config.get("profile_settings", {})
            }
            
            config_path = Path(AppConstants.CONFIG_FILE)
            temp_path = config_path.with_suffix('.tmp')
            
            with open(temp_path, "w", encoding='utf-8') as f: 
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            temp_path.replace(config_path)
            
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def _validate_inputs(self) -> bool:
        try:
            if not self.active_profile.get(): 
                messagebox.showerror("Invalid Setup", "No active profile selected. Please select or create a profile.")
                return False
            
            confidence = self.confidence.get()
            if not (0.0 <= confidence <= 1.0):
                messagebox.showerror("Invalid Input", 
                                   f"Confidence must be between 0.0 and 1.0.\nCurrent value: {confidence}")
                return False
            
            min_sleep = self.min_sleep_seconds.get()
            max_sleep = self.max_sleep_seconds.get()
            
            if min_sleep < 0 or max_sleep < 0:
                messagebox.showerror("Invalid Input", "Sleep values must be positive.")
                return False
            
            if min_sleep > max_sleep:
                messagebox.showerror("Invalid Input", 
                                   f"Minimum sleep ({min_sleep}s) must be less than or equal to maximum sleep ({max_sleep}s).")
                return False
            
            if max_sleep > 3600:
                messagebox.showerror("Invalid Input", "Maximum sleep cannot exceed 3600 seconds (1 hour).")
                return False
            
            duration = self.feedback_duration.get()
            if duration < 100 or duration > 5000:
                messagebox.showerror("Invalid Input", 
                                   "Feedback duration must be between 100 and 5000 milliseconds.")
                return False
            
            return True
            
        except (ValueError, TypeError) as e:
            messagebox.showerror("Invalid Input", 
                               f"Please ensure all numeric fields contain valid numbers.\nError: {e}")
            return False
    
    def _on_key_press(self, key):
        try:
            if key == keyboard.Key.f3: 
                self.root.after_idle(self._start_handler)
            elif key == keyboard.Key.f4: 
                self.root.after_idle(self._pause_handler)
            elif key == keyboard.Key.esc and hasattr(self, 'capture_window') and self.capture_window:
                self.root.after_idle(self._cancel_capture)
        except Exception as e:
            print(f"Keyboard event error: {e}")
    
    @safe_path_operation
    def get_profiles(self) -> List[str]:
        try:
            root_path = Path(self.profiles_root_path.get())
            if not root_path.is_dir(): 
                return []
            
            profiles = [
                d.name for d in root_path.iterdir() 
                if d.is_dir() and not d.name.startswith('.')
            ]
            return sorted(profiles)
        except Exception as e:
            print(f"Error getting profiles: {e}")
            return []
    
    def _update_profile_list(self):
        try:
            profiles = self.get_profiles()
            self.profile_combobox['values'] = profiles
            
            saved_profile = self.active_profile.get()
            if saved_profile and saved_profile in profiles: 
                self.profile_combobox.set(saved_profile)
            elif profiles: 
                self.profile_combobox.set(profiles[0])
                self.active_profile.set(profiles[0])
            else: 
                self.profile_combobox.set("")
                self.active_profile.set("")
            
            self._on_profile_change()
        except Exception as e:
            print(f"Error updating profile list: {e}")
    
    def _on_profile_change(self, event=None):
        try:
            if self._last_active_profile and self._last_active_profile != self.active_profile.get():
                self._save_current_profile_settings()
            
            self.template_cache.clear_cache()
            self._load_profile_settings()
            self._populate_sequence_listbox()
            self._last_active_profile = self.active_profile.get()
        except Exception as e:
            print(f"Error changing profile: {e}")
    
    def _populate_sequence_listbox(self):
        try:
            self.sequence_listbox.delete(0, 'end')
            
            profile_name = self.active_profile.get()
            if not profile_name: 
                return
            
            profile_path = Path(self.profiles_root_path.get()) / profile_name
            if not profile_path.is_dir(): 
                return
            
            actual_files = {
                p.name for p in profile_path.iterdir() 
                if p.is_file() and p.suffix.lower() in AppConstants.SUPPORTED_IMAGE_EXTENSIONS
            }
            
            if not actual_files:
                return
            
            profile_settings = self.config.get("profile_settings", {}).get(profile_name, {})
            saved_sequence = profile_settings.get("sequence", [])
            
            final_sequence = [f for f in saved_sequence if f in actual_files]
            new_files = sorted(actual_files - set(final_sequence), key=str.lower)
            final_sequence.extend(new_files)
            
            for item in final_sequence: 
                self.sequence_listbox.insert('end', item)
                
        except Exception as e:
            print(f"Error populating sequence listbox: {e}")
    
    def _move_template_up(self):
        try:
            selected_indices = self.sequence_listbox.curselection()
            if not selected_indices: 
                return
            
            idx = selected_indices[0]
            if idx > 0:
                item = self.sequence_listbox.get(idx)
                self.sequence_listbox.delete(idx)
                self.sequence_listbox.insert(idx - 1, item)
                self.sequence_listbox.selection_set(idx - 1)
                self.sequence_listbox.activate(idx - 1)
        except Exception as e:
            print(f"Error moving template up: {e}")
    
    def _move_template_down(self):
        try:
            selected_indices = self.sequence_listbox.curselection()
            if not selected_indices: 
                return
            
            idx = selected_indices[0]
            if idx < self.sequence_listbox.size() - 1:
                item = self.sequence_listbox.get(idx)
                self.sequence_listbox.delete(idx)
                self.sequence_listbox.insert(idx + 1, item)
                self.sequence_listbox.selection_set(idx + 1)
                self.sequence_listbox.activate(idx + 1)
        except Exception as e:
            print(f"Error moving template down: {e}")
    
    def _create_new_profile(self, parent_window=None):
        parent = parent_window if parent_window else self.root
        
        try:
            new_profile_name = simpledialog.askstring(
                "New Profile", 
                "Enter a name for the new profile:",
                parent=parent
            )
            
            if not new_profile_name or not new_profile_name.strip(): 
                return
            
            new_profile_name = new_profile_name.strip()
            
            if not validate_filename(new_profile_name):
                messagebox.showerror(
                    "Invalid Name", 
                    "Profile name contains invalid characters.",
                    parent=parent
                )
                return
            
            root_path = Path(self.profiles_root_path.get())
            root_path.mkdir(exist_ok=True)
            new_profile_path = root_path / new_profile_name
            
            if new_profile_path.exists(): 
                messagebox.showwarning(
                    "Profile Exists", 
                    f"A profile named '{new_profile_name}' already exists.",
                    parent=parent
                )
                return
            
            new_profile_path.mkdir(parents=True, exist_ok=True)
            
            self.active_profile.set(new_profile_name)
            self._update_profile_list()
            self._populate_sequence_listbox()
            
            messagebox.showinfo(
                "Success", 
                f"Profile '{new_profile_name}' created successfully.",
                parent=parent
            )
            
        except Exception as e: 
            messagebox.showerror(
                "Error", 
                f"Could not create profile directory: {e}",
                parent=parent
            )
    
    def _open_profile_manager(self):
        try:
            EnhancedProfileManagerWindow(self)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open profile manager: {e}")
    
    def _update_always_on_top(self):
        try:
            is_on_top = self.always_on_top.get()
            self.root.attributes("-topmost", is_on_top)
            
            if self.log_window and self.log_window.winfo_exists(): 
                self.log_window.attributes("-topmost", is_on_top)
        except Exception as e:
            print(f"Error updating always on top: {e}")
    
    def _start_handler(self):
        if self._is_running: 
            return
        
        if not self._validate_inputs(): 
            return
        
        try:
            self._is_running = True
            self.start_button.config(
                state="disabled", 
                text="Running...",
                bg=self.theme_manager.get_color('button_active_bg_color')
            )
            self.sequence_index = 0
            
            if self.log_window is None: 
                self._show_log_window()
            
            self._load_templates()
            
            if self.log_window: 
                self.root.withdraw()
            
            self._match_loop()
            
        except Exception as e:
            self._handle_start_error(e)
    
    def _handle_start_error(self, error):
        self._is_running = False
        self.start_button.config(
            state="normal", 
            text="Start (F3)",
            bg=self.theme_manager.get_color('button_bg_color')
        )
        messagebox.showerror("Automation Error", f"Could not start automation: {error}")
    
    def _pause_handler(self):
        if not self._is_running: 
            return
        
        try:
            self._is_running = False
            
            if self._after_id: 
                self.root.after_cancel(self._after_id)
                self._after_id = None
            
            self.start_button.config(
                state="normal", 
                text="Resume (F3)",
                bg=self.theme_manager.get_color('button_bg_color')
            )
            
            self.root.deiconify()
            self.root.lift()
            
            self._log("Process paused. Press F3 to resume.", "WARN")
            
        except Exception as e:
            print(f"Error pausing automation: {e}")
    
    def _load_templates(self):
        try:
            self.templates.clear()
            
            profile_path = Path(self.profiles_root_path.get()) / self.active_profile.get()
            if not profile_path.is_dir(): 
                self._log(f"Profile directory not found: {profile_path}", "ERROR")
                return
            
            all_template_files = [
                p for p in profile_path.iterdir() 
                if p.is_file() and p.suffix.lower() in AppConstants.SUPPORTED_IMAGE_EXTENSIONS
            ]
            
            if not all_template_files:
                self._log(f"No template files found in profile '{self.active_profile.get()}'", "WARN")
                return
            
            all_template_files.sort(key=human_sort_key)
            
            loaded_count = 0
            failed_count = 0
            
            for path in all_template_files:
                template = self.template_cache.get_template(path)
                if template:
                    self.templates[path.name] = template
                    loaded_count += 1
                else:
                    failed_count += 1
                    self._log(f"Failed to load template: {path.name}", "WARN")
            
            self._log(f"Loaded {loaded_count} templates for profile '{self.active_profile.get()}'")
            if failed_count > 0:
                self._log(f"Failed to load {failed_count} templates", "WARN")
            
            if loaded_count > 0:
                stats = self.template_cache.get_cache_stats()
                self._log(f"Cache: {stats['cache_size']}/{stats['max_size']} "
                         f"(Hit rate: {stats['hit_rate']:.1f}%, "
                         f"Memory: {stats['memory_usage_bytes'] // 1024} KB)")
            
        except Exception as e:
            self._log(f"Error loading templates: {e}", "ERROR")
    
    def _match_loop(self):
        if not self._is_running: 
            return
        
        try:
            self._perform_match()
            
            sleep_interval = random.uniform(
                self.min_sleep_seconds.get(), 
                self.max_sleep_seconds.get()
            )
            
            self._log(f"Waiting for {sleep_interval:.2f} seconds.")
            
            self._after_id = self.root.after(
                int(sleep_interval * 1000), 
                self._match_loop
            )
            
        except Exception as e:
            self._log(f"Error in match loop: {e}", "ERROR")
            self._pause_handler()
    
    def _perform_click_action(self, box, path_name: str):
        try:
            center_x, center_y = pyautogui.center(box)
            
            click_x = center_x + random.randint(-AppConstants.CLICK_TOLERANCE, AppConstants.CLICK_TOLERANCE)
            click_y = center_y + random.randint(-AppConstants.CLICK_TOLERANCE, AppConstants.CLICK_TOLERANCE)
            
            original_pos = pyautogui.position()
            
            pyautogui.click(click_x, click_y)
            
            pyautogui.moveTo(original_pos)
            
            self._log(f"Clicked '{path_name}' at ({click_x}, {click_y})")
            
        except Exception as e:
            self._log(f"Error clicking '{path_name}': {e}", "ERROR")
    
    def _perform_match(self):
        try:
            if not self.templates:
                self._log(f"No templates loaded for profile '{self.active_profile.get()}'. Pausing.", "WARN")
                self._pause_handler()
                return
            
            screenshot = pyautogui.screenshot()
            
            if self.search_mode.get() == "sequence": 
                self._perform_match_sequence(screenshot)
            else: 
                self._perform_match_priority(screenshot)
                
        except Exception as e:
            self._log(f"Screenshot error: {e}. Retrying...", "WARN")
    
    def _perform_match_priority(self, screenshot):
        try:
            search_kwargs = {"grayscale": self.grayscale.get()}
            if HAS_CV2: 
                search_kwargs["confidence"] = self.confidence.get()
            
            sorted_template_names = sorted(self.templates.keys(), key=str.lower)
            
            for name in sorted_template_names:
                image = self.templates.get(name)
                if not image: 
                    continue
                
                self._log(f"Searching for template: {name}")
                
                try:
                    box = pyautogui.locate(image, screenshot, **search_kwargs)
                    if box: 
                        self._log(f"Found match: {name}")
                        self._handle_found_match(box, name)
                        return
                        
                except pyautogui.PyAutoGUIException as e: 
                    self._log(f"Search error for '{name}': {e}", "WARN")
                except Exception as e:
                    self._log(f"Unexpected error searching '{name}': {e}", "ERROR")
            
            self._log("No templates matched in this cycle")
            
        except Exception as e:
            self._log(f"Error in priority match: {e}", "ERROR")
    
    def _perform_match_sequence(self, screenshot):
        try:
            sequence = list(self.sequence_listbox.get(0, 'end'))
            if not sequence: 
                self._log("Sequence is empty. Pausing.", "WARN")
                self._pause_handler()
                return
            
            self.sequence_index %= len(sequence)
            target_name = sequence[self.sequence_index]
            
            image_to_find = self.templates.get(target_name)
            if not image_to_find: 
                self._log(f"Template '{target_name}' for sequence step not found in memory. Pausing.", "ERROR")
                self._pause_handler()
                return
            
            self._log(f"Searching for sequence step {self.sequence_index + 1}/{len(sequence)}: '{target_name}'")
            
            search_kwargs = {"grayscale": self.grayscale.get()}
            if HAS_CV2: 
                search_kwargs["confidence"] = self.confidence.get()
            
            try:
                box = pyautogui.locate(image_to_find, screenshot, **search_kwargs)
                if box:
                    self._log(f"Found sequence match: {target_name}")
                    self.sequence_index = (self.sequence_index + 1) % len(sequence)
                    self._handle_found_match(box, target_name)
                else:
                    self._log(f"Sequence step '{target_name}' not found, waiting...")
                    
            except pyautogui.PyAutoGUIException as e: 
                self._log(f"Search error for sequence '{target_name}': {e}", "WARN")
            except Exception as e:
                self._log(f"Unexpected error in sequence search: {e}", "ERROR")
                
        except Exception as e:
            self._log(f"Error in sequence match: {e}", "ERROR")
    
    def _handle_found_match(self, box, path_name: str):
        try:
            if self.show_visual_feedback.get():
                feedback_box = self._show_feedback_box(box)
                if feedback_box:
                    self.root.after(
                        self.feedback_duration.get(), 
                        lambda: self._execute_delayed_click(feedback_box, box, path_name)
                    )
                else:
                    self._perform_click_action(box, path_name)
            else:
                self._perform_click_action(box, path_name)
                
        except Exception as e:
            self._log(f"Error handling match for '{path_name}': {e}", "ERROR")
    
    def _execute_delayed_click(self, feedback_box, box, path_name: str):
        try:
            if feedback_box:
                feedback_box.destroy()
            
            self._perform_click_action(box, path_name)
            
        except Exception as e:
            self._log(f"Error in delayed click for '{path_name}': {e}", "ERROR")
    
    def _show_log_window(self):
        try:
            self.root.withdraw()
            
            self.log_window = Toplevel(self.root)
            self.log_window.title("Automation Log Console")
            self.log_window.protocol("WM_DELETE_WINDOW", self._terminate_app)
            self.log_window.config(bg=self.theme_manager.get_color('bg_color'))
            
            width, height = map(int, AppConstants.LOG_WINDOW_SIZE.split('x'))
            self.log_window.geometry(f"{width}x{height}")
            
            self._update_always_on_top()
            
            main_log_frame = Frame(self.log_window, bg=self.theme_manager.get_color('bg_color'))
            main_log_frame.pack(padx=10, pady=10, fill="both", expand=True)
            
            help_label = Label(
                main_log_frame, 
                text="F3: Resume | F4: Pause & Show Settings", 
                bg=self.theme_manager.get_color('bg_color'), 
                fg=self.theme_manager.get_color('secondary_fg_color'), 
                font=("Segoe UI", 9)
            )
            help_label.pack(pady=(0, 5))
            
            text_frame = Frame(main_log_frame, bg=self.theme_manager.get_color('bg_color'))
            text_frame.pack(fill="both", expand=True)
            
            self.log_text_widget = Text(
                text_frame, 
                height=15, width=80, wrap="word", 
                bg=self.theme_manager.get_color('input_bg_color'), 
                fg=self.theme_manager.get_color('input_fg_color'), 
                bd=0, highlightthickness=0, font=("Consolas", 9),
                state="disabled"
            )
            self.log_text_widget.pack(side="left", fill="both", expand=True)
            
            scrollbar = Scrollbar(
                text_frame, 
                command=self.log_text_widget.yview, 
                bg=self.theme_manager.get_color('bg_color'), 
                troughcolor=self.theme_manager.get_color('input_bg_color'), 
                bd=0, 
                activebackground=self.theme_manager.get_color('selection_bg_color')
            )
            scrollbar.pack(side="right", fill="y")
            self.log_text_widget.config(yscrollcommand=scrollbar.set)
            
            self._log(f"Automation started - Profile: '{self.active_profile.get()}' | Mode: '{self.search_mode.get()}'")
            self._log(f"Templates loaded: {len(self.templates)}")
            
            if not HAS_CV2:
                self._log("Note: OpenCV not installed. Confidence setting will be ignored. "
                         "Install with: pip install opencv-python", "WARN")
            
        except Exception as e:
            messagebox.showerror("Log Window Error", f"Could not create log window: {e}")
    
    def _terminate_app(self):
        try:
            self._save_config()
            
            self._is_running = False
            if self._after_id: 
                self.root.after_cancel(self._after_id)
                self._after_id = None
            
            if hasattr(self, 'keyboard_listener') and self.keyboard_listener:
                try:
                    self.keyboard_listener.stop()
                except Exception:
                    pass
            
            self.templates.clear()
            self.template_cache.clear_cache()
            
            EnhancedTooltip.hide_all()
            
            gc.collect()
            
            self.root.destroy()
            
        except Exception as e:
            print(f"Error during app termination: {e}")
            try:
                self.root.destroy()
            except:
                pass
    
    def _load_profile_settings(self):
        try:
            profile_name = self.active_profile.get()
            if not profile_name:
                profile_settings = {}
            else:
                all_profile_settings = self.config.get("profile_settings", {})
                profile_settings = all_profile_settings.get(profile_name, {})
            
            confidence = profile_settings.get("confidence", 0.8)
            if isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0:
                self.confidence.set(float(confidence))
            else:
                self.confidence.set(0.8)
            
            self.grayscale.set(bool(profile_settings.get("grayscale", True)))
            
            min_sleep = profile_settings.get("min_sleep", 1.0)
            if isinstance(min_sleep, (int, float)) and 0.0 <= min_sleep <= 3600:
                self.min_sleep_seconds.set(float(min_sleep))
            else:
                self.min_sleep_seconds.set(1.0)
            
            max_sleep = profile_settings.get("max_sleep", 5.0)
            if isinstance(max_sleep, (int, float)) and 0.0 <= max_sleep <= 3600:
                self.max_sleep_seconds.set(float(max_sleep))
            else:
                self.max_sleep_seconds.set(5.0)
            
            search_mode = profile_settings.get("search_mode", "priority")
            if search_mode in ["priority", "sequence"]:
                self.search_mode.set(search_mode)
            else:
                self.search_mode.set("priority")
            
        except Exception as e:
            print(f"Error loading profile settings: {e}")
            self.confidence.set(0.8)
            self.grayscale.set(True)
            self.min_sleep_seconds.set(1.0)
            self.max_sleep_seconds.set(5.0)
            self.search_mode.set("priority")
    
    def _save_current_profile_settings(self):
        try:
            profile_name = self._last_active_profile
            if not profile_name: 
                return
            
            if "profile_settings" not in self.config:
                self.config["profile_settings"] = {}
            
            sequence = list(self.sequence_listbox.get(0, 'end')) if hasattr(self, 'sequence_listbox') else []
            
            self.config["profile_settings"][profile_name] = {
                "confidence": self.confidence.get(),
                "grayscale": self.grayscale.get(),
                "min_sleep": self.min_sleep_seconds.get(),
                "max_sleep": self.max_sleep_seconds.get(),
                "search_mode": self.search_mode.get(),
                "sequence": sequence
            }
            
        except Exception as e:
            print(f"Error saving profile settings: {e}")
    
    def _rename_profile_config(self, old_name: str, new_name: str):
        try:
            if "profile_settings" in self.config and old_name in self.config["profile_settings"]:
                self.config["profile_settings"][new_name] = self.config["profile_settings"].pop(old_name)
        except Exception as e:
            print(f"Error renaming profile config: {e}")
    
    def _delete_profile_config(self, profile_name: str):
        try:
            if "profile_settings" in self.config:
                self.config["profile_settings"].pop(profile_name, None)
        except Exception as e:
            print(f"Error deleting profile config: {e}")

def main():
    try:
        root = Tk()
        app = NexusAutoDL(root)
        root.mainloop()
        
    except KeyboardInterrupt:
        print("Application interrupted by user")
        if 'app' in locals():
            app._terminate_app()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if 'root' in locals():
                root.destroy()
        except:
            pass

if __name__ == "__main__":
    main()
