# -*- coding: utf-8 -*-
"""
This version uses a stable, single-threaded architecture with root.after() to
prevent both GUI freezing and thread-related crashes.

Features:
- F3 to Start/Resume, F4 to Pause.
- Dark Mode GUI.
- Mouse returns to its original position after clicking.
- Some other features (hotkeys, config saving, etc.).
"""

import json
import random
import re
from datetime import datetime
from pathlib import Path
from tkinter import (BooleanVar, Button, Checkbutton, DoubleVar, Entry, Frame,
                     Label, Scrollbar, StringVar, Text, Tk, Toplevel,
                     filedialog)
from tkinter import messagebox
from typing import Any, Dict, Optional

# --- Dependency Check ---
try:
    from pynput import keyboard
    import pyautogui
    from PIL import UnidentifiedImageError
    from PIL.Image import open as open_image
    from PIL.ImageFile import ImageFile
except ImportError as e:
    print(f"Error: A critical library is missing: {e.name}.")
    print("Please, run in your terminal: pip install pyautogui Pillow pynput")
    exit()

try:
    import cv2
    del cv2
    has_cv2 = True
except ImportError:
    has_cv2 = False

# --- Constants ---
CONFIG_FILE = "config.json"
CLICK_TOLERANCE = 3

# --- Utility Functions ---
_INTEGER_PATTERN = re.compile("([0-9]+)")

def _human_sort(key: Path) -> tuple:
    return tuple(int(c) if c.isdigit() else c for c in _INTEGER_PATTERN.split(key.name))


class NexusAutoDL:
    # --- Dark Mode Colors ---
    BG_COLOR = "#2E2E2E"
    FG_COLOR = "#EAEAEA"
    INPUT_BG_COLOR = "#3C3C3C"
    BUTTON_BG_COLOR = "#555555"
    BUTTON_ACTIVE_BG_COLOR = "#6A6A6A"

    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Nexus AutoDL (F3 Start/Resume, F4 Pause)")
        self.root.resizable(False, False)
        self.root.config(bg=self.BG_COLOR)

        self._is_running = False
        self._after_id: Optional[str] = None

        self.confidence = DoubleVar(value=0.7)
        self.grayscale = BooleanVar(value=True)
        self.min_sleep_seconds = DoubleVar(value=1.0)
        self.max_sleep_seconds = DoubleVar(value=5.0)
        self.templates_path = StringVar(value="templates")
        
        self._load_config()
        self._setup_ui()
        
        self.log_text_widget: Optional[Text] = None
        self.templates: Dict[str, ImageFile] = {}

        self.keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self.keyboard_listener.start()
        self.root.protocol("WM_DELETE_WINDOW", self._terminate_app)

    def _setup_ui(self):
        input_frame = Frame(self.root, padx=10, pady=10, bg=self.BG_COLOR)
        input_frame.pack()

        label_style = {"bg": self.BG_COLOR, "fg": self.FG_COLOR}
        entry_style = {"bg": self.INPUT_BG_COLOR, "fg": self.FG_COLOR, "insertbackground": self.FG_COLOR, "bd": 1, "highlightthickness": 0}
        button_style = {"bg": self.BUTTON_BG_COLOR, "fg": self.FG_COLOR, "activebackground": self.BUTTON_ACTIVE_BG_COLOR, "activeforeground": self.FG_COLOR, "bd": 0}
        check_style = {**label_style, "selectcolor": self.INPUT_BG_COLOR, "activebackground": self.BG_COLOR}

        Label(input_frame, text="Confidence:", **label_style).grid(row=0, column=0, sticky="w", pady=2)
        Entry(input_frame, textvariable=self.confidence, **entry_style).grid(row=0, column=1)
        Label(input_frame, text="Min sleep seconds:", **label_style).grid(row=1, column=0, sticky="w", pady=2)
        Entry(input_frame, textvariable=self.min_sleep_seconds, **entry_style).grid(row=1, column=1)
        Label(input_frame, text="Max sleep seconds:", **label_style).grid(row=2, column=0, sticky="w", pady=2)
        Entry(input_frame, textvariable=self.max_sleep_seconds, **entry_style).grid(row=2, column=1)
        Label(input_frame, text="Templates directory:", **label_style).grid(row=3, column=0, sticky="w", pady=2)
        Entry(input_frame, state="readonly", textvariable=self.templates_path, readonlybackground=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=1).grid(row=3, column=1)
        Button(input_frame, text="...", command=self._select_folder, **button_style).grid(row=3, column=2, padx=(5, 0))
        Checkbutton(input_frame, text="Grayscale", variable=self.grayscale, **check_style).grid(row=4, column=0, sticky="w", pady=5)
        
        self.start_button = Button(input_frame, text="Start (F3)", command=self._start_handler, **button_style)
        self.start_button.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="ew", ipady=5)
    
    def _log(self, message: str, level: str = "INFO"):
        if not self.log_text_widget: return
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text_widget.insert("end", f"[{timestamp}][{level}] {message}\n")
        self.log_text_widget.see("end")

    def _load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                self.templates_path.set(json.load(f).get("templates_path", "templates"))
        except (FileNotFoundError, json.JSONDecodeError): pass

    def _save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"templates_path": self.templates_path.get()}, f, indent=4)

    def _validate_inputs(self) -> bool:
        try:
            conf, min_s, max_s = self.confidence.get(), self.min_sleep_seconds.get(), self.max_sleep_seconds.get()
            if not (0.0 <= conf <= 1.0): messagebox.showerror("Invalid Input", "Confidence must be between 0.0 and 1.0."); return False
            if min_s < 0 or max_s < 0: messagebox.showerror("Invalid Input", "Sleep times cannot be negative."); return False
            if min_s > max_s: messagebox.showerror("Invalid Input", "Min sleep must not be greater than Max sleep."); return False
            if not Path(self.templates_path.get()).exists(): messagebox.showerror("Invalid Path", "The specified templates directory does not exist."); return False
            return True
        except Exception:
            messagebox.showerror("Invalid Input", "Please ensure all fields contain valid numbers."); return False

    def _on_press(self, key):
        if key == keyboard.Key.f3: self._start_handler()
        elif key == keyboard.Key.f4: self._pause_handler()

    def _select_folder(self):
        path = filedialog.askdirectory(title="Select Templates Folder")
        if path:
            self.templates_path.set(path)
            self._save_config()

    def _start_handler(self):
        """Handles both starting the process for the first time and resuming it."""
        if self._is_running: return

        self._is_running = True
        self.start_button.config(state="disabled", text="Running...")

        # Differentiate between first start and resume
        if self.log_text_widget is None:
            # This is the first start
            if not self._validate_inputs():
                self._is_running = False # Revert state if validation fails
                self.start_button.config(state="normal", text="Start (F3)")
                return
            self._show_log_window()
            self._load_templates()
            self._log("Process started. Starting search loop...")
        else:
            # This is a resume
            self._log("Process resumed.")

        # Kick off the match loop
        self._match_loop()

    def _pause_handler(self):
        """Pauses the matching process."""
        if not self._is_running: return

        self._is_running = False
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        
        self.start_button.config(state="normal", text="Resume (F3)")
        self._log("Process paused. Press F3 to resume.", "WARN")

    def _load_templates(self):
        """Loads all template images from the specified directory."""
        self.templates.clear()
        for path in sorted(Path(self.templates_path.get()).iterdir(), key=_human_sort):
            try:
                img = open_image(path)
                self.templates[str(path)] = img.copy()
                img.close()
                self._log(f"Loaded template: {path.name}")
            except (IsADirectoryError, UnidentifiedImageError): pass

    def _match_loop(self):
        if not self._is_running: return

        self._perform_match()
        sleep_interval = random.uniform(self.min_sleep_seconds.get(), self.max_sleep_seconds.get())
        self._log(f"Waiting for {sleep_interval:.2f} seconds.")
        self._after_id = self.root.after(int(sleep_interval * 1000), self._match_loop)

    def _perform_match(self):
        search_kwargs: Dict[str, Any] = {"grayscale": self.grayscale.get()}
        if has_cv2: search_kwargs["confidence"] = self.confidence.get()

        if not self.templates:
            self._log("No valid templates loaded. Stopping.", "FATAL")
            self._terminate_app()
            return

        screenshot = pyautogui.screenshot()
        for path_str, image in self.templates.items():
            path_name = Path(path_str).name
            self._log(f"Attempting to find {path_name}.")
            try:
                box = pyautogui.locate(image, screenshot, **search_kwargs)
                if box:
                    center_x, center_y = pyautogui.center(box)
                    click_x = center_x + random.randint(-CLICK_TOLERANCE, CLICK_TOLERANCE)
                    click_y = center_y + random.randint(-CLICK_TOLERANCE, CLICK_TOLERANCE)
                    
                    original_pos = pyautogui.position()
                    pyautogui.click(click_x, click_y)
                    pyautogui.moveTo(original_pos)
                    
                    self._log(f"Clicked {path_name} at ({click_x}, {click_y}) and returned mouse.", "INFO")
                    return
            except pyautogui.PyAutoGUIException as e:
                self._log(f"Search error for {path_name}: {e}", "WARN")

    def _show_log_window(self):
        self.root.withdraw()
        log_window = Toplevel(self.root)
        log_window.title("Log Console")
        log_window.protocol("WM_DELETE_WINDOW", self._terminate_app)
        log_window.config(bg=self.BG_COLOR)

        frame = Frame(log_window, bg=self.BG_COLOR)
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.log_text_widget = Text(frame, height=20, width=100, wrap="word", bg=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=0, highlightthickness=0)
        self.log_text_widget.pack(side="left", fill="both", expand=True)
        scrollbar = Scrollbar(frame, command=self.log_text_widget.yview, bg=self.BG_COLOR, troughcolor=self.INPUT_BG_COLOR, bd=0, activebackground=self.BUTTON_ACTIVE_BG_COLOR)
        scrollbar.pack(side="right", fill="y")
        self.log_text_widget.config(yscrollcommand=scrollbar.set)

    def _terminate_app(self):
        self._is_running = False
        if self._after_id: self.root.after_cancel(self._after_id)
        if self.keyboard_listener.is_alive(): self.keyboard_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    main_root = Tk()
    app = NexusAutoDL(main_root)
    try:
        main_root.mainloop()
    except KeyboardInterrupt:
        app._terminate_app()
