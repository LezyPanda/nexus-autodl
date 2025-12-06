import json
import os
import random
import shutil
import weakref
import threading
import gc
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from tkinter import (
    Tk, Toplevel, Canvas, Frame, Label, Button, Entry, 
    StringVar, BooleanVar, DoubleVar, IntVar, 
    filedialog, messagebox, simpledialog, colorchooser,
    Checkbutton, Radiobutton, Listbox, Scrollbar, Text,
    LabelFrame
)
from tkinter import ttk
from typing import Dict, List, Optional, Tuple, Union, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image as PILImageType
else:
    PILImageType = Any

try:
    from PIL import Image, ImageTk
    from PIL import UnidentifiedImageError
except ImportError:
    Image = None  # type: ignore[assignment]
    ImageTk = None  # type: ignore[assignment]
    UnidentifiedImageError = Exception  # type: ignore[assignment]


def open_image(path: str):
    if Image is None:
        raise ImportError("Pillow is required to open images")
    return Image.open(path)

import pyautogui

mss: Any
try:
    import mss as mss_module
    mss = mss_module
    MSS_AVAILABLE = True
except ImportError:
    mss = None  # type: ignore[assignment]
    MSS_AVAILABLE = False
from pynput import keyboard

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from ..constants import AppConstants
from ..utils.helpers import human_sort_key, safe_path_operation, validate_filename
from .theme_manager import ThemeManager
from .components import OptimizedHoverEffect, EnhancedTooltip
from ..core.template_cache import EnhancedTemplateCache
from .windows import EnhancedProfileManagerWindow

class NexusAutoDL:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(f"Nexus AutoDL {AppConstants.VERSION}")
        self.root.resizable(False, False)
        
        self._init_variables()
        self._init_state()
        self._refresh_monitors()
        self._load_config()
        self._ensure_valid_monitor_selection()
        
        self.theme_manager = ThemeManager(is_dark_mode=self.dark_mode.get())
        self.root.config(bg=self.theme_manager.get_color('bg_color'))
        
        self.template_cache = EnhancedTemplateCache(max_cache_size=AppConstants.CACHE_SIZE)
        self.templates: Dict[str, PILImageType] = {}
        
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
        self.monitor_number = IntVar()
        
        self.profiles_root_path = StringVar()
        self.active_profile = StringVar()
    
    def _init_state(self):
        self._is_running = False
        self._after_id: Optional[str] = None
        self._last_active_profile = ""
        self.sequence_index = 0

        self._monitors: List[Dict[str, int]] = []
        self._monitor_labels: List[str] = []
        self._monitor_label_map: Dict[str, int] = {}
        
        self.log_window: Optional[Toplevel] = None
        self.log_text_widget: Optional[Text] = None
        self.capture_window: Optional[Toplevel] = None
        self.capture_canvas: Optional[Canvas] = None
        self.rect: Optional[int] = None
        self.start_x: Optional[float] = None
        self.start_y: Optional[float] = None
        
        self.hover_effects: List[OptimizedHoverEffect] = []
        self.tooltips: List[EnhancedTooltip] = []
    
    def _init_keyboard_listener(self):
        try:
            self.keyboard_listener = keyboard.Listener(on_press=self._on_key_press)
            self.keyboard_listener.start()
        except Exception as e:
            print(f"Failed to initialize keyboard listener: {e}")
            self.keyboard_listener = None

    def _refresh_monitors(self):
        self._monitors.clear()
        self._monitor_labels.clear()
        self._monitor_label_map.clear()

        if not MSS_AVAILABLE:
            return

        try:
            with mss.mss() as sct:
                monitors = sct.monitors[1:]

            for idx, mon in enumerate(monitors, start=1):
                label = (
                    f"Monitor {idx} ({mon['width']}x{mon['height']} "
                    f"@ {mon['left']},{mon['top']})"
                )
                self._monitors.append(mon)
                self._monitor_labels.append(label)
                self._monitor_label_map[label] = idx
        except Exception as e:
            print(f"Failed to refresh monitor list: {e}")

    def _ensure_valid_monitor_selection(self):
        if not self._monitors:
            self.monitor_number.set(1)
            return

        current = self.monitor_number.get()
        if current < 1 or current > len(self._monitors):
            self.monitor_number.set(1)
    
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
        self._refresh_monitors()
        self._ensure_valid_monitor_selection()

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

        Label(display_frame, text="Target Monitor:", **styles['label']).grid(
            row=3, column=0, sticky='w', pady=(8, 3)
        )
        self.monitor_combobox = ttk.Combobox(
            display_frame,
            state="readonly",
            width=42,
            font=("Segoe UI", 9)
        )
        self.monitor_combobox.grid(row=3, column=1, columnspan=2, sticky='w', padx=(8, 0), pady=(8, 3))
        self.monitor_combobox.bind("<<ComboboxSelected>>", self._on_monitor_change)
        self._populate_monitor_selector()
        
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
            (getattr(self, 'monitor_combobox', None), "Choose which monitor to capture, detect, and click on."),
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

    def _populate_monitor_selector(self):
        if not hasattr(self, 'monitor_combobox'):
            return

        if self._monitor_labels:
            values = self._monitor_labels
        else:
            values = ["Monitor 1 (default display)"]

        self.monitor_combobox['values'] = values

        target_index = self.monitor_number.get()
        current_label = next(
            (label for label, idx in self._monitor_label_map.items() if idx == target_index),
            values[0] if values else ""
        )

        self.monitor_combobox.set(current_label)

    def _on_monitor_change(self, event=None):
        label = self.monitor_combobox.get()
        idx = self._monitor_label_map.get(label)
        if idx:
            self.monitor_number.set(idx)
    
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
        log_window = self.log_window
        log_was_open = log_window is not None and log_window.winfo_exists()
        if log_was_open and log_window is not None:
            try:
                log_window.destroy()
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
            self._refresh_monitors()
            self._ensure_valid_monitor_selection()
            self.root.withdraw()
            self.capture_window = Toplevel(self.root)
            self.capture_window.attributes("-alpha", 0.3)
            self.capture_window.attributes("-topmost", True)
            self.capture_window.overrideredirect(True)

            monitor = self._get_selected_monitor_bounds()
            if monitor:
                geometry = f"{monitor['width']}x{monitor['height']}+{monitor['left']}+{monitor['top']}"
                self.capture_window.geometry(geometry)
            else:
                self.capture_window.attributes("-fullscreen", True)
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

    def _get_selected_monitor_bounds(self) -> Optional[Dict[str, int]]:
        if not self._monitors:
            return None
        idx = self.monitor_number.get()
        if 1 <= idx <= len(self._monitors):
            return self._monitors[idx - 1]
        return None

    def _capture_region_with_mss(self, region: Tuple[int, int, int, int]) -> PILImageType:
        region_dict = {
            "left": int(region[0]),
            "top": int(region[1]),
            "width": int(region[2]),
            "height": int(region[3])
        }

        if MSS_AVAILABLE and mss is not None:
            try:
                if Image is None:
                    raise RuntimeError("Pillow is required for mss conversion")
                with mss.mss() as sct:
                    sct_img = sct.grab(region_dict)
                return Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            except Exception as e:
                self._log(f"mss capture failed, falling back to pyautogui: {e}", "WARN")

        return pyautogui.screenshot(region=region)

    def _grab_monitor_screenshot(self) -> Tuple[PILImageType, int, int]:
        monitor = self._get_selected_monitor_bounds()

        if MSS_AVAILABLE and monitor and mss is not None:
            try:
                if Image is None:
                    raise RuntimeError("Pillow is required for mss conversion")
                with mss.mss() as sct:
                    sct_img = sct.grab(monitor)
                image = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
                return image, monitor.get("left", 0), monitor.get("top", 0)
            except Exception as e:
                self._log(f"mss monitor capture failed, falling back: {e}", "WARN")

        screenshot = pyautogui.screenshot()
        return screenshot, 0, 0

    def _apply_screen_offset(self, box, offset_x: int, offset_y: int):
        if not box:
            return box
        if offset_x == 0 and offset_y == 0:
            return box
        try:
            return box.__class__(
                box.left + offset_x,
                box.top + offset_y,
                box.width,
                box.height
            )
        except Exception:
            try:
                # Fallback for tuple-like boxes
                new_box = namedtuple("Box", ["left", "top", "width", "height"])(
                    box[0] + offset_x,
                    box[1] + offset_y,
                    box[2],
                    box[3]
                )
                return new_box
            except Exception:
                return box
    
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
        if self.capture_canvas is None:
            return

        start_x = self.capture_canvas.canvasx(event.x)
        start_y = self.capture_canvas.canvasy(event.y)
        self.start_x = start_x
        self.start_y = start_y
        self.rect = self.capture_canvas.create_rectangle(
            start_x, start_y, start_x, start_y, 
            outline='red', width=2
        )
    
    def _on_capture_drag(self, event):
        if self.capture_canvas is None or self.rect is None or self.start_x is None or self.start_y is None:
            return

        cur_x = self.capture_canvas.canvasx(event.x)
        cur_y = self.capture_canvas.canvasy(event.y)
        self.capture_canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)
    
    def _on_capture_release(self, event):
        if self.capture_canvas is None or self.start_x is None or self.start_y is None:
            return

        try:
            end_x = self.capture_canvas.canvasx(event.x)
            end_y = self.capture_canvas.canvasy(event.y)
            
            if self.capture_window is not None and self.capture_window.winfo_exists():
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
            
            monitor = self._get_selected_monitor_bounds()
            offset_x = monitor.get("left", 0) if monitor else 0
            offset_y = monitor.get("top", 0) if monitor else 0

            region_tuple = (
                int(x1 + offset_x),
                int(y1 + offset_y),
                int(width),
                int(height)
            )
            img = self._capture_region_with_mss(region_tuple)
            
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
        if self.log_text_widget is None:
            return
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

        monitor_number = self.config.get("monitor_number", 1)
        if isinstance(monitor_number, int) and monitor_number > 0:
            self.monitor_number.set(monitor_number)
        else:
            self.monitor_number.set(1)
    
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
                "monitor_number": self.monitor_number.get(),
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
            
            screenshot, offset_x, offset_y = self._grab_monitor_screenshot()
            
            if self.search_mode.get() == "sequence": 
                self._perform_match_sequence(screenshot, offset_x, offset_y)
            else: 
                self._perform_match_priority(screenshot, offset_x, offset_y)
                
        except Exception as e:
            self._log(f"Screenshot error: {e}. Retrying...", "WARN")
    
    def _perform_match_priority(self, screenshot, offset_x: int, offset_y: int):
        try:
            search_kwargs: Dict[str, object] = {"grayscale": bool(self.grayscale.get())}
            if HAS_CV2: 
                search_kwargs["confidence"] = float(self.confidence.get())
            
            sorted_template_names = sorted(self.templates.keys(), key=str.lower)
            
            for name in sorted_template_names:
                image = self.templates.get(name)
                if not image: 
                    continue
                
                self._log(f"Searching for template: {name}")
                
                try:
                    box = pyautogui.locate(image, screenshot, **search_kwargs)
                    if box: 
                        adjusted_box = self._apply_screen_offset(box, offset_x, offset_y)
                        self._log(f"Found match: {name}")
                        self._handle_found_match(adjusted_box, name)
                        return
                        
                except pyautogui.PyAutoGUIException as e: 
                    self._log(f"Search error for '{name}': {e}", "WARN")
                except Exception as e:
                    self._log(f"Unexpected error searching '{name}': {e}", "ERROR")
            
            self._log("No templates matched in this cycle")
            
        except Exception as e:
            self._log(f"Error in priority match: {e}", "ERROR")
    
    def _perform_match_sequence(self, screenshot, offset_x: int, offset_y: int):
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
            
            search_kwargs: Dict[str, object] = {"grayscale": bool(self.grayscale.get())}
            if HAS_CV2: 
                search_kwargs["confidence"] = float(self.confidence.get())
            
            try:
                box = pyautogui.locate(image_to_find, screenshot, **search_kwargs)
                if box:
                    adjusted_box = self._apply_screen_offset(box, offset_x, offset_y)
                    self._log(f"Found sequence match: {target_name}")
                    self.sequence_index = (self.sequence_index + 1) % len(sequence)
                    self._handle_found_match(adjusted_box, target_name)
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
            if not MSS_AVAILABLE:
                self._log("Note: mss not installed. Install 'mss' for accurate multi-monitor capture.", "WARN")
            
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




